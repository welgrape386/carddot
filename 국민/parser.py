"""
parser.py - KB국민카드 HTML 파싱

포함 함수:
  - parse_card_info      : 카드 기본정보 (연회비/네트워크/이미지 등)
  - discover_main_tabs   : 메인 탭 감지 및 분류 (benefit/fee/notice)
  - parse_benefit_tab    : 혜택 탭 → 혜택 행 리스트
  - parse_notice_tabs_for_benefit : 확인사항 탭 → 유의사항 행
  - parse_fee_tabs       : 연회비 탭 → (요약 dict, 상세 행)
  - parse_notices        : 이용전확인사항 → 공지 행
  - _postprocess_benefit_rows : 혜택 행 후처리
"""

import re
from bs4 import BeautifulSoup

from config import CARD_PAGE_CODE
from classifier import (
    get_category, get_category_id, classify_benefit_type,
    extract_number, extract_min_amount, extract_max_count, extract_max_limit,
    filter_brands, classify_merchants_with_llm,
    ON_OFF_MAP, LOCATION_MAP,
)

# ── 파서 내부 상수 ─────────────────────────────────────────────
_GYEONG_SUFFIXES = ("업종", "매장", "가맹점", "서비스", "요금", "대출", "서비스 이용")

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def fee_to_number(s: str) -> str:
    if not s or s.strip() in ("-", ""):
        return ""
    s = s.strip()
    # 괄호 안 금액(기본 X천원 + 제휴 Y천원 등) 제거 — 합산 방지
    s_clean = re.sub(r"\([^)]*\)", "", s).strip()
    total = 0
    for val, unit in re.findall(r"(\d+)(만|천|백)", s_clean):
        if unit == "만":
            total += int(val) * 10000
        elif unit == "천":
            total += int(val) * 1000
        elif unit == "백":
            total += int(val) * 100
    if total:
        return str(total)
    m = re.search(r"[\d,]+", s_clean)
    return m.group(0).replace(",", "") if m else ""

def extract_number(text: str) -> str:
    text = (text or "").strip()
    if not text or text in ("없음", "-", ""):
        return ""
    total = 0
    for val, unit in re.findall(r"(\d+)(만|천|백)", text):
        if unit == "만":
            total += int(val) * 10000
        elif unit == "천":
            total += int(val) * 1000
        elif unit == "백":
            total += int(val) * 100
    if total:
        return str(total)
    m = re.search(r"[\d,]+", text)
    return m.group(0).replace(",", "") if m else ""


def extract_min_amount(content: str) -> str:
    """
    건당 최소 결제금액 조건 추출.
    '1만원 이상 결제 시', '5천원 이상 시', '건당 1만원 이상' 패턴 → 숫자 반환.
    전월실적 조건('전월 이용실적 N만원 이상')은 제외.
    """
    if not content:
        return ""
    # 전월실적 조건 먼저 제거 (오추출 방지)
    content_clean = re.sub(r"전월\s*이용실적[^\s]*\s*[\d,만천백]+원\s*이상", "", content)
    m = re.search(
        r"(?:건당\s*)?([\d,만천백]+)원\s*이상\s*(?:결제\s*)?시",
        content_clean
    )
    if m:
        return extract_number(m.group(1) + "원")
    return ""


def extract_max_count(content: str) -> str:
    """
    월 최대 횟수 추출.
    '월 2회', '2회 / 2천원', '월한도: 월 1회' 패턴 → 숫자 반환.
    연 단위(연 N회)는 제외.
    """
    if not content:
        return ""
    # '월 N회' 패턴
    m = re.search(r"월\s*(\d+)\s*회", content)
    if m:
        return m.group(1)
    # 'N회 / N천원' 패턴 (노리2 스타일)
    m = re.search(r"(\d+)회\s*/\s*[\d,만천백]+원", content)
    if m:
        return m.group(1)
    # '월한도: 월 N회' 패턴
    m = re.search(r"월한도\s*[:|]\s*월?\s*(\d+)\s*회", content)
    if m:
        return m.group(1)
    return ""

def extract_benefit_value(소분류: str, 내용: str) -> tuple:
    skip = ["연회비", "반환", "이용실적", "제외", "안내", "실적유예", "유예기간"]
    if any(k in 소분류 for k in skip):
        return "", ""

    # ── 전월실적 조건 설명문 → 수치 없음 처리 ──────────────────────
    # "전월 이용실적이 35만원 이상 40만원 미만인 고객" 처럼
    # 문장 전체가 실적 조건 설명이면 수치로 추출하지 않음
    _PERF_COND_RE = re.compile(
        r"(전월\s*이용실적이?|전월실적이?)\s*([\d,만천]+원\s*)?(이상|미만시?|구간|부족|조건|없이)",
        re.IGNORECASE,
    )
    if _PERF_COND_RE.search(내용):
        # 전월실적 조건 부분을 제거한 나머지에 실제 할인 수치가 있는지 확인
        내용_잔여 = _PERF_COND_RE.sub("", 내용)
        # 잔여에 % 할인율이 있으면 그걸 사용
        m = re.search(r"([\d.]+)%", 내용_잔여)
        if m:
            return m.group(1), "%"
        # 잔여에 명확한 'N원 할인' 또는 '한도 : N원' 패턴이 있으면 사용
        m = re.search(r"([\d,만천]+)원\s*할인", 내용_잔여)
        if m:
            return extract_number(m.group(1) + "원"), "원"
        m = re.search(r"한도\s*[:|]\s*([\d,만천]+)원", 내용_잔여)
        if m:
            return extract_number(m.group(1) + "원"), "원"
        # 파이프 구분 테이블 행 마지막 금액 (e.g. "월간 통합할인한도 | 전월실적 20만원 이상 | 20,000원")
        m = re.search(r"\|\s*([\d,만천]+)원\s*$", 내용_잔여)
        if m:
            return extract_number(m.group(1) + "원"), "원"
        # 잔여에 실질 할인 수치가 없으면 빈값 반환
        # 단순히 '80만원 미만 구간' 같은 조건 잔여만 있으면 빈값
        return "", ""

    m = re.search(r"([\d.]+)%", 내용)
    if m:
        return m.group(1), "%"

    # ── 'N원 이상 시 M원 할인' 패턴 → 조건금액 건너뛰고 할인액 추출 ──
    # "1만원 이상 시 1,000원 할인" 에서 value=1000 (조건인 1만원 아님)
    m_threshold = re.search(
        r"[\d,만천]+원\s*이상\s*(?:시|결제\s*시|이용\s*시)\s*([\d,만천]+)원",
        내용,
    )
    if m_threshold:
        return extract_number(m_threshold.group(1) + "원"), "원"

    m = re.search(r"([\d,만천]+)원", 내용)
    if m:
        return extract_number(m.group(0)), "원"
    return "", ""

# 카테고리명 → 숫자 ID 매핑
CATEGORY_ID_MAP: dict[str, int] = {
    "온라인쇼핑":             1,
    "패션/뷰티":              2,
    "슈퍼마켓/생활잡화":      3,
    "백화점/아울렛/면세점":   4,
    "대중교통/택시":          5,
    "자동차/주유":            6,
    "반려동물":               7,
    "구독/스트리밍":          8,
    "레저/스포츠":            9,
    "페이/간편결제":          10,
    "문화/엔터":              11,
    "생활비":                 12,
    "편의점":                 13,
    "커피/카페/베이커리":     14,
    "배달":                   15,
    "외식":                   16,
    "여행/숙박":              17,
    "항공":                   18,
    "해외":                   19,
    "교육/육아":              20,
    "의료":                   21,
}


def get_category(소제목: str, 내용: str) -> str:
    text = 소제목 + " " + 내용
    for cat, keywords in CATEGORY_MAP:
        if any(k in text for k in keywords):
            return cat
    # 전 가맹점 할인 (국내 가맹점, 해외 가맹점 전체) → 해외/국내로 분류
    if re.search(r"국내\s*(전체\s*)?가맹점|전\s*가맹점|전가맹점", text):
        return "전가맹점"
    # 일상팩/가족팩 할인율·한도 안내 행 → 생활비 (팩 전체 포함 의미)
    if re.search(r"일상팩|가족팩", text):
        return "생활비"
    return ""

def classify_benefit_type(소분류: str, 내용: str, 혜택단위: str) -> str:
    text = 소분류 + " " + 내용
    if "캐시백" in text:
        return "캐시백"
    if any(k in text for k in ["포인트 사용", "M포인트"]):
        return "포인트사용"
    if any(k in text for k in ["적립", "포인트", "마일리지"]):
        return "포인트적립"

    # ── 할인한도 테이블 행은 서비스 판별 전에 먼저 '할인'으로 분류 ──
    # "월간 통합할인한도 | 전월실적 N만원 이상 | N원" 형태
    # 전월실적 조건이 포함돼 있어도 실제 할인 한도값을 나타내는 행
    if re.search(r"할인한도|통합한도|월\s*한도", text) and 혜택단위 in ("원", "%"):
        return "할인"

    # ── 전월실적 조건/서비스 설명문은 서비스로 분류 ──────────────
    # "할인 혜택을 받을 수 있도록 전월실적을 채워드리는 서비스" 처럼
    # 문장 자체가 서비스 안내인 경우, 중간에 "할인"이 포함되어도 서비스로 분류
    _SERVICE_DESC_RE = re.compile(
        r"(채워드리|신청\s*(가능|불가)|분기\s*\d+회|서비스\s*신청|서비스\s*적용"
        r"|이용실적이?\s*[\d,만천]+원\s*(이상|미만)"
        r"|실적\s*\d+만원\s*(이상|미만|구간))"
    )
    if _SERVICE_DESC_RE.search(내용):
        return "서비스"

    if 혜택단위 == "%" or "할인" in text:
        return "할인"
    return "서비스"


_MERCHANT_CATEGORIES = ["쇼핑", "OTT", "배달", "통신", "카페", "편의점", "앱스토어", "기타"]

def classify_merchants_with_llm(merchants_text: str) -> dict:
    """
    혜택 텍스트에서 LLM으로 브랜드명 추출 + 카테고리 분류 동시 수행.
    - target_merchants: 실제 브랜드/업체명만 (스타벅스, 넷플릭스 등 고유명사)
    - 업종명/조건문/서비스설명은 제외
    - ANTHROPIC_API_KEY 없으면 빈 결과 반환
    반환: {"row_idx": {"brands": [...], "category": "카테고리명"}, ...}
    """
    empty = {}

    if not merchants_text or not merchants_text.strip():
        return empty
    if not ANTHROPIC_API_KEY:
        print("  [LLM 스킵] ANTHROPIC_API_KEY 환경변수 없음")
        return empty

    prompt = f"""다음은 신용카드 혜택 텍스트 목록입니다. 각 줄에서 실제 브랜드/업체명만 추출하고 카테고리를 분류해줘.

규칙:
- 브랜드명: 고유한 상호명만 (스타벅스, 넷플릭스, GS25, SKT 등)
- 제외 대상: 업종명(교육, 주유, 병원), 조건문(이용 시, 결제 전), 서비스설명(채워드림, 공항라운지, 여행자보험), 일반명사
- 브랜드가 없으면 brands를 빈 배열로

카테고리 목록 (아래 21개 중 하나만 사용, 해당 없으면 빈 문자열):
온라인쇼핑, 패션/뷰티, 슈퍼마켓/생활잡화, 백화점/아울렛/면세점, 대중교통/택시,
자동차/주유, 반려동물, 구독/스트리밍, 레저/스포츠, 페이/간편결제, 문화/엔터,
생활비, 편의점, 커피/카페/베이커리, 배달, 외식, 여행/숙박, 항공, 해외, 교육/육아, 의료

출력 형식 (JSON만, 다른 텍스트 없이):
{{"0": {{"brands": ["브랜드1", "브랜드2"], "category": "카테고리명"}}, "1": {{"brands": [], "category": ""}}, ...}}

텍스트 목록 (줄번호: 내용):
{merchants_text}"""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "content-type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": ANTHROPIC_API_KEY,
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        raw = "".join(
            b.get("text", "") for b in data.get("content", [])
            if b.get("type") == "text"
        )
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        return json.loads(raw)

    except Exception as e:
        print(f"  [LLM 실패] {e}")
        return empty



def parse_max_benefit(text: str) -> str:
    text = (text or "").strip()
    if not text or text in ("없음", "-"):
        return ""
    # 회수+금액 혼합 패턴에서 금액 부분만 추출
    # 예) "월 10회(월 2천원 이내)" → "2천원 이내", "2회 / 2천원" → "2천원"
    m_paren = re.search(r'\(월?\s*([^)]+)\)', text)
    m_slash = re.search(r'/\s*(.+)', text)
    if m_paren:
        text = m_paren.group(1).strip()
    elif m_slash and re.search(r'\d+\s*회', text.split('/')[0]):
        text = m_slash.group(1).strip()
    # 회수만 남으면(금액 없음) 빈값
    if re.search(r'\d+\s*회|연\s*\d+|건당|%', text) and \
       not re.search(r'\d+[만천]원|\d{1,3},\d{3}원|\d+원', text):
        return ""
    total = 0
    for val, unit in re.findall(r"(\d+)(만|천)", text):
        total += int(val) * 10000 if unit == "만" else int(val) * 1000
    if total:
        return str(total)
    m = re.search(r"[\d,]+", text)
    return m.group(0).replace(",", "") if m else ""

def korean_to_won(s: str) -> str:
    s = s.strip()
    total = 0
    for val, unit in re.findall(r"(\d+)(만|천)", s):
        total += int(val) * 10000 if unit == "만" else int(val) * 1000
    if total:
        return f"{total:,}원"
    m = re.search(r"[\d,]+원", s)
    return m.group(0) if m else s



def _is_gyeong(name: str) -> bool:
    """'스포츠용품점 업종' 처럼 업종분류 텍스트이면 True"""
    return any(name.endswith(s) for s in _GYEONG_SUFFIXES)

def _split_by_comma(text: str) -> list[str]:
    """쉼표·슬래시·중점으로 구분된 가맹점 목록 분리 후 정제"""
    parts = re.split(r"[,，/·、]\s*", text)
    result = []
    for p in parts:
        p = p.strip()
        # 괄호 속 부연 제거: "트레이더스 홀세일 클럽(이마트)" -> "트레이더스 홀세일 클럽"
        p = re.sub(r"\([^)]*\)", "", p).strip()
        if not p or len(p) < 2:
            continue
        # 조건문 접미사 → 가맹점명 아님
        if re.search(r"결제 시$|이용 시$|이용건$|이상 결제$", p):
            continue
        # 자동납부 관련 접미사 제거
        # "Liiv M 이동통신 자동납부요금" → "Liiv M"
        # "쿠팡 로켓와우 멤버십 자동납부요금" → "쿠팡 로켓와우 멤버십"
        p = re.sub(
            r"\s+(이동통신\s*)?자동납부\s*요금$|"
            r"\s+멤버십\s+자동납부\s*요금$|"
            r"\s+자동납부요금$",
            "", p
        ).strip()
        if not p or len(p) < 2:
            continue
        result.append(p)
    return result


def parse_h4_merchants(h4_text: str) -> tuple[list[str], list[str]]:
    """
    패턴 A: h4.titDep2 제목 텍스트에서 가맹점 추출.

    "[배달]배달의민족/쿠팡이츠 10% 청구할인"
      -> include=["배달의민족","쿠팡이츠"], exclude=[]

    "[편의점]GS25/CU 오프라인 매장 5% 청구할인"
      -> include=["GS25","CU"], exclude=[]

    "[통신/보험/APP]이동통신/보험료/앱스토어 10% 청구할인"
      -> include=[] (업종명이므로, tblH에서 별도 추출)
    """
    include, exclude = [], []

    # [] 브래킷 안 내용 추출
    bracket_m = re.search(r"\[([^\]]+)\]", h4_text)
    if not bracket_m:
        return include, exclude

    bracket_inner = bracket_m.group(1).strip()

    # 브래킷 안에 슬래시가 있거나 업종 접미사를 포함하면 업종 조합 브래킷으로 판단
    # → 브래킷 뒤 텍스트도 업종명일 가능성이 높으므로 tblH에 위임하고 빠져나옴
    if "/" in bracket_inner or _is_gyeong(bracket_inner):
        return include, exclude

    # 브래킷 뒤 가맹점명 부분 추출
    after_bracket = h4_text[bracket_m.end():].strip()
    # 할인율/청구할인/괄호 이하 잘라내기
    after_bracket = re.split(r"\s*\d+%|\s*청구할인|\s*\(", after_bracket)[0].strip()

    # "오프라인 매장", "업종" 같은 접미어 제거
    after_bracket = re.sub(
        r"\s*(오프라인|온라인)?\s*(매장|업종|서비스)\s*$", "", after_bracket
    ).strip()

    # 슬래시/쉼표로 구분된 가맹점 후보
    candidates = re.split(r"[/,]\s*", after_bracket)

    # 불용어: 숫자+개, 단독 방향어, 업종 분류어
    NOISE_PATTERNS = [
        re.compile(r"^\d+개"),          # "7개 온라인쇼핑몰"
        re.compile(r"^(오프라인|온라인|업종|매장|이용처)$"),
    ]

    for c in candidates:
        c = c.strip()
        if not c or len(c) < 2:
            continue
        if any(p.match(c) for p in NOISE_PATTERNS):
            continue
        if _is_gyeong(c):
            continue
        include.append(c)

    return include, exclude


def parse_tblH_merchants(table) -> tuple[list[str], list[str]]:
    """
    패턴 B: table.tblH 의 "할인 대상" 컬럼에서 가맹점 추출.

    구분:이동통신 | 할인대상:SKT, KT, LG U+, Liiv M 이동통신 자동납부 요금
      -> include=["SKT","KT","LG U+","Liiv M"], exclude=[]

    구분:스포츠 | 할인대상:스포츠용품점, 레저용품점 ... 업종
      -> include=[] (모두 업종 분류), exclude=[]

    전월실적 한도 테이블 / Mastercard 서비스 테이블 -> include=[] (스킵)
    """
    include, exclude = [], []

    rows = table.find_all("tr")
    if not rows:
        return include, exclude

    # 헤더 행
    header_cells = rows[0].find_all(["th", "td"])
    header_texts = [c.get_text(strip=True) for c in header_cells]

    # 비가맹점 테이블 조기 스킵
    header_joined = " ".join(header_texts)
    SKIP_TABLE_KW = (
        "전월 이용실적", "월 할인한도", "이용실적에 따른",  # 전월실적 한도 테이블
        "기본서비스", "선택서비스", "서비스명",             # Mastercard/JCB 서비스 테이블
        "1회", "1일", "월간", "출금한도",                  # 이용한도 테이블
        "이자율", "수수료율",                               # 이자/수수료 테이블
    )
    if any(k in header_joined for k in SKIP_TABLE_KW):
        return include, exclude

    # "할인 대상" 컬럼 인덱스
    target_col = -1
    for i, h in enumerate(header_texts):
        if any(k in h for k in ("할인 대상", "이용처", "가맹점")):
            target_col = i
            break
    # "대상" 단독 키워드는 2컬럼 이하 테이블(구분|내용 형태)에서만 fallback 허용
    if target_col < 0:
        for i, h in enumerate(header_texts):
            if "대상" in h:
                target_col = i
                break
    # 명시적 컬럼을 찾지 못하면 추출 포기 (엉뚱한 컬럼 오추출 방지)
    if target_col < 0:
        return include, exclude

    # 노이즈 토큰 패턴 (한도 금액, 숫자만, 단순 설명어)
    NOISE_TOKEN = re.compile(
        r"^(\d+천원|\d+만원|\d+%|이상|미만|이하|이내|이후|구간\d+)$"
    )

    for tr in rows[1:]:
        cells = tr.find_all(["th", "td"])
        if target_col < 0 or target_col >= len(cells):
            continue
        cell_text = cells[target_col].get_text(separator=", ", strip=True)

        # 업종 접미사로 끝나는 셀 전체 → 스킵
        if _is_gyeong(cell_text.strip()):
            continue

        parts = _split_by_comma(cell_text)
        for p in parts:
            # 뒤에 붙는 설명 제거
            p = re.sub(
                r"\s*(업종|자동납부요금|자동납부 요금|이동통신 자동납부요금|이동통신 자동납부 요금"
                r"|멤버십 자동납부요금|멤버십 자동납부 요금"
                r"|요금|서비스|오프라인 결제 건.*|앱주문 제외.*"
                r"|이동통신 자동납부.*|및 생명보험.*|및 이용원.*)$",
                "", p
            ).strip()
            if not p or len(p) < 2:
                continue
            if _is_gyeong(p):
                continue
            if NOISE_TOKEN.match(p):
                continue
            include.append(p)

    return include, exclude


def parse_listType1_merchants(ul) -> tuple[list[str], list[str]]:
    """
    패턴 C: ul.listType1 li "할인 대상 : ..." 형태.

    "할인 대상 : 이마트, 트레이더스 홀세일 클럽, 롯데마트"
      -> include=["이마트","트레이더스 홀세일 클럽","롯데마트"], exclude=[]

    "할인 대상 : 네이버플러스스토어, 쿠팡, 마켓컬리, 오아시스마켓"
      -> include=["네이버플러스스토어","쿠팡","마켓컬리","오아시스마켓"], exclude=[]
    """
    include, exclude = [], []
    for li in ul.find_all("li"):
        txt = li.get_text(strip=True)
        # "할인 대상 :" 또는 "대상:" 패턴
        m = re.match(r"^(?:할인\s*)?대상\s*[:：]\s*(.+)", txt)
        if m:
            merchants = _split_by_comma(m.group(1))
            for mer in merchants:
                mer = re.sub(r"\s*(업종|매장)$", "", mer).strip()
                if mer and len(mer) >= 2:
                    include.append(mer)
    return include, exclude


def parse_caution_excludes(ul) -> list[str]:
    """
    패턴 D: ul.caution-list에서 제외 가맹점 추출.

    "백화점, 대형마트 등 일부 입점 매장 제외"
      -> ["백화점","대형마트"]
    "온라인몰, 주차장, 상품권, 임대매장, 기업형 슈퍼마켓(SSM)은 제외"
      -> ["온라인몰","주차장","상품권","임대매장","기업형 슈퍼마켓"]
    "멤버십 이용권은 할인 대상 제외"
      -> ["멤버십 이용권"]
    "이동통신 : 인터넷, IPTV 등 결합상품 제외"
      -> ["인터넷","IPTV 등 결합상품"]
    """
    # li 전체가 서비스 안내/전월실적 등 비제외 문장이면 스킵
    SKIP_CONTENT_KW = ("전월 이용실적", "할인 서비스는", "최초 발급", "유의사항", "단기카드대출")

    excludes = []
    for li in ul.find_all("li"):
        txt = li.get_text(strip=True)

        if any(k in txt for k in SKIP_CONTENT_KW):
            continue

        # "X 제외" / "X은/는 제외" / "X 대상 제외" / "X은 제외됩니다" 패턴
        m = re.search(
            r"(.+?)(?:\s*등\s*일부[^,제외]*?)?(?:은|는)?\s*(?:할인\s*)?대상?\s*제외",
            txt
        )
        if not m:
            m = re.search(r"(.+?)\s+제외(?:됩니다|됨|처리)?$", txt)
        if not m:
            continue

        raw = m.group(1).strip()

        # "이동통신 : 인터넷, IPTV" → 콜론 뒤만 사용
        colon_m = re.match(r"^[^:：]+[:：]\s*(.+)", raw)
        if colon_m:
            raw = colon_m.group(1).strip()

        parts = _split_by_comma(raw)
        for p in parts:
            p = re.sub(r"\s*(및|등)\s*일부.*$", "", p).strip()
            p = re.sub(r"[은는]$", "", p).strip()
            if p and len(p) >= 2:
                excludes.append(p)
    return excludes


def parse_titDep2_section(container) -> list[dict]:
    """
    h4.titDep2 기준으로 섹션을 분리하고
    include / exclude 가맹점을 안정적으로 추출
    """

    import re

    def normalize_merchants(lst):
        result = []
        for item in lst:
            parts = re.split(r"[,/·]", item)
            result.extend([p.strip() for p in parts if p.strip()])
        return list(dict.fromkeys(result))

    results = []
    h4s = container.find_all("h4", class_="titDep2")

    SKIP_KEYWORDS = ("전월", "실적", "안내", "유의", "확인", "조건", "기준")

    for h4 in h4s:
        h4_text = h4.get_text(separator=" ", strip=True)

        if any(k in h4_text for k in SKIP_KEYWORDS):
            continue

        include_all, exclude_all = [], []

        # [패턴 A]
        inc_a, _ = parse_h4_merchants(h4_text)
        include_all.extend(inc_a)

        # 🔥 핵심: 섹션 전체 HTML 누적
        html_parts = [str(h4)]

        sib = h4.find_next_sibling()
        while sib:
            # 다음 섹션 시작이면 종료
            if getattr(sib, "name", None) == "h4" and "titDep2" in sib.get("class", []):
                break

            # NavigableString 방어
            if not hasattr(sib, "name"):
                sib = sib.find_next_sibling()
                continue

            html_parts.append(str(sib))

            cls = " ".join(sib.get("class", []))

            # [패턴 B]
            if sib.name == "table" and "tblH" in cls:
                inc_b, exc_b = parse_tblH_merchants(sib)
                include_all.extend(inc_b)
                exclude_all.extend(exc_b)

            # [패턴 C]
            elif sib.name == "ul" and "listType1" in cls:
                inc_c, exc_c = parse_listType1_merchants(sib)
                include_all.extend(inc_c)
                exclude_all.extend(exc_c)

            # [패턴 D]
            elif sib.name == "ul" and "caution-list" in cls:
                exc_d = parse_caution_excludes(sib)
                exclude_all.extend(exc_d)

            sib = sib.find_next_sibling()

        raw_html = "".join(html_parts)

        results.append({
            "section_title": h4_text,
            "include_merchants": filter_brands(normalize_merchants(include_all)),
            "exclude_merchants": filter_brands(normalize_merchants(exclude_all)),
            "raw_html": raw_html
        })

    return results


def extract_number(text: str) -> str:
    text = (text or "").strip()
    if not text or text in ("없음", "-", ""):
        return ""
    total = 0
    for val, unit in re.findall(r"(\d+)(만|천|백)", text):
        if unit == "만":
            total += int(val) * 10000
        elif unit == "천":
            total += int(val) * 1000
        elif unit == "백":
            total += int(val) * 100
    if total:
        return str(total)
    m = re.search(r"[\d,]+", text)
    return m.group(0).replace(",", "") if m else ""


def extract_min_amount(content: str) -> str:
    """
    건당 최소 결제금액 조건 추출.
    '1만원 이상 결제 시', '5천원 이상 시', '건당 1만원 이상' 패턴 → 숫자 반환.
    전월실적 조건('전월 이용실적 N만원 이상')은 제외.
    """
    if not content:
        return ""
    # 전월실적 조건 먼저 제거 (오추출 방지)
    content_clean = re.sub(r"전월\s*이용실적[^\s]*\s*[\d,만천백]+원\s*이상", "", content)
    m = re.search(
        r"(?:건당\s*)?([\d,만천백]+)원\s*이상\s*(?:결제\s*)?시",
        content_clean
    )
    if m:
        return extract_number(m.group(1) + "원")
    return ""


def extract_max_count(content: str) -> str:
    """
    월 최대 횟수 추출.
    '월 2회', '2회 / 2천원', '월한도: 월 1회' 패턴 → 숫자 반환.
    연 단위(연 N회)는 제외.
    """
    if not content:
        return ""
    # '월 N회' 패턴
    m = re.search(r"월\s*(\d+)\s*회", content)
    if m:
        return m.group(1)
    # 'N회 / N천원' 패턴 (노리2 스타일)
    m = re.search(r"(\d+)회\s*/\s*[\d,만천백]+원", content)
    if m:
        return m.group(1)
    # '월한도: 월 N회' 패턴
    m = re.search(r"월한도\s*[:|]\s*월?\s*(\d+)\s*회", content)
    if m:
        return m.group(1)
    return ""

def extract_benefit_value(소분류: str, 내용: str) -> tuple:
    skip = ["연회비", "반환", "이용실적", "제외", "안내", "실적유예", "유예기간"]
    if any(k in 소분류 for k in skip):
        return "", ""

    # ── 전월실적 조건 설명문 → 수치 없음 처리 ──────────────────────
    # "전월 이용실적이 35만원 이상 40만원 미만인 고객" 처럼
    # 문장 전체가 실적 조건 설명이면 수치로 추출하지 않음
    _PERF_COND_RE = re.compile(
        r"(전월\s*이용실적이?|전월실적이?)\s*([\d,만천]+원\s*)?(이상|미만시?|구간|부족|조건|없이)",
        re.IGNORECASE,
    )
    if _PERF_COND_RE.search(내용):
        # 전월실적 조건 부분을 제거한 나머지에 실제 할인 수치가 있는지 확인
        내용_잔여 = _PERF_COND_RE.sub("", 내용)
        # 잔여에 % 할인율이 있으면 그걸 사용
        m = re.search(r"([\d.]+)%", 내용_잔여)
        if m:
            return m.group(1), "%"
        # 잔여에 명확한 'N원 할인' 또는 '한도 : N원' 패턴이 있으면 사용
        m = re.search(r"([\d,만천]+)원\s*할인", 내용_잔여)
        if m:
            return extract_number(m.group(1) + "원"), "원"
        m = re.search(r"한도\s*[:|]\s*([\d,만천]+)원", 내용_잔여)
        if m:
            return extract_number(m.group(1) + "원"), "원"
        # 파이프 구분 테이블 행 마지막 금액 (e.g. "월간 통합할인한도 | 전월실적 20만원 이상 | 20,000원")
        m = re.search(r"\|\s*([\d,만천]+)원\s*$", 내용_잔여)
        if m:
            return extract_number(m.group(1) + "원"), "원"
        # 잔여에 실질 할인 수치가 없으면 빈값 반환
        # 단순히 '80만원 미만 구간' 같은 조건 잔여만 있으면 빈값
        return "", ""

    m = re.search(r"([\d.]+)%", 내용)
    if m:
        return m.group(1), "%"

    # ── 'N원 이상 시 M원 할인' 패턴 → 조건금액 건너뛰고 할인액 추출 ──
    # "1만원 이상 시 1,000원 할인" 에서 value=1000 (조건인 1만원 아님)
    m_threshold = re.search(
        r"[\d,만천]+원\s*이상\s*(?:시|결제\s*시|이용\s*시)\s*([\d,만천]+)원",
        내용,
    )
    if m_threshold:
        return extract_number(m_threshold.group(1) + "원"), "원"

    m = re.search(r"([\d,만천]+)원", 내용)
    if m:
        return extract_number(m.group(0)), "원"
    return "", ""

# 카테고리명 → 숫자 ID 매핑
CATEGORY_ID_MAP: dict[str, int] = {
    "온라인쇼핑":             1,
    "패션/뷰티":              2,
    "슈퍼마켓/생활잡화":      3,
    "백화점/아울렛/면세점":   4,
    "대중교통/택시":          5,
    "자동차/주유":            6,
    "반려동물":               7,
    "구독/스트리밍":          8,
    "레저/스포츠":            9,
    "페이/간편결제":          10,
    "문화/엔터":              11,
    "생활비":                 12,
    "편의점":                 13,
    "커피/카페/베이커리":     14,
    "배달":                   15,
    "외식":                   16,
    "여행/숙박":              17,
    "항공":                   18,
    "해외":                   19,
    "교육/육아":              20,
    "의료":                   21,
}


def get_category(소제목: str, 내용: str) -> str:
    text = 소제목 + " " + 내용
    for cat, keywords in CATEGORY_MAP:
        if any(k in text for k in keywords):
            return cat
    # 전 가맹점 할인 (국내 가맹점, 해외 가맹점 전체) → 해외/국내로 분류
    if re.search(r"국내\s*(전체\s*)?가맹점|전\s*가맹점|전가맹점", text):
        return "전가맹점"
    # 일상팩/가족팩 할인율·한도 안내 행 → 생활비 (팩 전체 포함 의미)
    if re.search(r"일상팩|가족팩", text):
        return "생활비"
    return ""

def classify_benefit_type(소분류: str, 내용: str, 혜택단위: str) -> str:
    text = 소분류 + " " + 내용
    if "캐시백" in text:
        return "캐시백"
    if any(k in text for k in ["포인트 사용", "M포인트"]):
        return "포인트사용"
    if any(k in text for k in ["적립", "포인트", "마일리지"]):
        return "포인트적립"

    # ── 할인한도 테이블 행은 서비스 판별 전에 먼저 '할인'으로 분류 ──
    # "월간 통합할인한도 | 전월실적 N만원 이상 | N원" 형태
    # 전월실적 조건이 포함돼 있어도 실제 할인 한도값을 나타내는 행
    if re.search(r"할인한도|통합한도|월\s*한도", text) and 혜택단위 in ("원", "%"):
        return "할인"

    # ── 전월실적 조건/서비스 설명문은 서비스로 분류 ──────────────
    # "할인 혜택을 받을 수 있도록 전월실적을 채워드리는 서비스" 처럼
    # 문장 자체가 서비스 안내인 경우, 중간에 "할인"이 포함되어도 서비스로 분류
    _SERVICE_DESC_RE = re.compile(
        r"(채워드리|신청\s*(가능|불가)|분기\s*\d+회|서비스\s*신청|서비스\s*적용"
        r"|이용실적이?\s*[\d,만천]+원\s*(이상|미만)"
        r"|실적\s*\d+만원\s*(이상|미만|구간))"
    )
    if _SERVICE_DESC_RE.search(내용):
        return "서비스"

    if 혜택단위 == "%" or "할인" in text:
        return "할인"
    return "서비스"


_MERCHANT_CATEGORIES = ["쇼핑", "OTT", "배달", "통신", "카페", "편의점", "앱스토어", "기타"]

def classify_merchants_with_llm(merchants_text: str) -> dict:
    """
    혜택 텍스트에서 LLM으로 브랜드명 추출 + 카테고리 분류 동시 수행.
    - target_merchants: 실제 브랜드/업체명만 (스타벅스, 넷플릭스 등 고유명사)
    - 업종명/조건문/서비스설명은 제외
    - ANTHROPIC_API_KEY 없으면 빈 결과 반환
    반환: {"row_idx": {"brands": [...], "category": "카테고리명"}, ...}
    """
    empty = {}

    if not merchants_text or not merchants_text.strip():
        return empty
    if not ANTHROPIC_API_KEY:
        print("  [LLM 스킵] ANTHROPIC_API_KEY 환경변수 없음")
        return empty

    prompt = f"""다음은 신용카드 혜택 텍스트 목록입니다. 각 줄에서 실제 브랜드/업체명만 추출하고 카테고리를 분류해줘.

규칙:
- 브랜드명: 고유한 상호명만 (스타벅스, 넷플릭스, GS25, SKT 등)
- 제외 대상: 업종명(교육, 주유, 병원), 조건문(이용 시, 결제 전), 서비스설명(채워드림, 공항라운지, 여행자보험), 일반명사
- 브랜드가 없으면 brands를 빈 배열로

카테고리 목록 (아래 21개 중 하나만 사용, 해당 없으면 빈 문자열):
온라인쇼핑, 패션/뷰티, 슈퍼마켓/생활잡화, 백화점/아울렛/면세점, 대중교통/택시,
자동차/주유, 반려동물, 구독/스트리밍, 레저/스포츠, 페이/간편결제, 문화/엔터,
생활비, 편의점, 커피/카페/베이커리, 배달, 외식, 여행/숙박, 항공, 해외, 교육/육아, 의료

출력 형식 (JSON만, 다른 텍스트 없이):
{{"0": {{"brands": ["브랜드1", "브랜드2"], "category": "카테고리명"}}, "1": {{"brands": [], "category": ""}}, ...}}

텍스트 목록 (줄번호: 내용):
{merchants_text}"""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "content-type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": ANTHROPIC_API_KEY,
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        raw = "".join(
            b.get("text", "") for b in data.get("content", [])
            if b.get("type") == "text"
        )
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        return json.loads(raw)

    except Exception as e:
        print(f"  [LLM 실패] {e}")
        return empty



def append_csv(filepath: str, fieldnames: list, rows: list):
    file_exists = os.path.isfile(filepath)
    with open(filepath, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

def parse_card_info(soup, cooperation_code: str = "") -> dict:
    info = {
        "card_type": "신용",
        "카드설명": "",
        "main_benefit": "",
        "결제네트워크브랜드": "",
        "국내전용_일반": "",
        "해외겸용_일반": "",
        "국내전용_프리미엄": "",
        "해외겸용_프리미엄": "",
        "연회비_비고": "",
        "후불교통": False,
        "image_url": "",
    }

    # 카드 종류
    ul = soup.find("ul", class_="cardKind")
    if ul:
        types = [clean(li.get_text()) for li in ul.find_all("li") if li.get_text(strip=True)]
        if types:
            info["card_type"] = "/".join(types)

    # 카드 설명
    tit_div = soup.find("div", class_="cardTit")
    if tit_div:
        p = tit_div.find("p", class_="txt")
        if p:
            info["카드설명"] = clean(p.get_text())

    # 카드대표혜택: .cardBenefit li → span 첫번째만 추출
    benefit_ul = soup.find(class_="cardBenefit")
    if benefit_ul:
        benefit_txts = []
        for li in benefit_ul.find_all("li"):
            span = li.find("span")
            txt = clean(span.get_text()) if span else ""
            if not txt:
                for p in li.find_all("p", class_="overTxt"):
                    p.decompose()
                txt = clean(li.get_text())
            if txt:
                benefit_txts.append(txt)
        info["main_benefit"] = " / ".join(benefit_txts)

    # 카드 이미지: cooperation_code로 URL 직접 조립, 없으면 slideList에서 fallback
    if cooperation_code:
        info["image_url"] = (
            f"https://img1.kbcard.com/ST/img/cxc/kbcard/upload/img/product/"
            f"{cooperation_code}_img.png"
        )
    if not info["image_url"]:
        slide_ul = soup.find("ul", class_=lambda c: c and "slideList" in c and "card" in c)
        if slide_ul:
            for li in slide_ul.find_all("li", recursive=False):
                if "bx-clone" in li.get("class", []):
                    continue
                img_tag = li.find("img")
                if img_tag and img_tag.get("src"):
                    src = img_tag["src"]
                    info["image_url"] = src if src.startswith("http") else f"https:{src}"
                    break

    # 결제네트워크 + 연회비
    fee_div = soup.find("div", class_="cardAnnualFee")
    if fee_div:
        brands = []
        for li in fee_div.find_all("li"):
            img = li.find("img")
            span = li.find("span", class_="card-fee")
            if not img or not span:
                continue
            alt = img.get("alt", "")
            fee_text = clean(span.get_text())

            if "국내전용" in alt or "Local" in alt:
                if "Local" not in brands:
                    brands.append("Local")
            if "VISA" in alt and "VISA" not in brands:
                brands.append("VISA")
            if "Master" in alt and "Master" not in brands:
                brands.append("Master")
            if "UnionPay" in alt and "UnionPay" not in brands:
                brands.append("UnionPay")

            main_m   = re.match(r"([\d,]+원)", fee_text)
            mobile_m = re.search(r"모바일단독[:\s]*([\d,]+원)", fee_text)
            main_fee = main_m.group(1) if main_m else ""

            if "국내전용" in alt or "Local" in alt:
                info["국내전용_일반"] = main_fee
                if mobile_m:
                    info["연회비_비고"] = f"모바일단독(국내): {mobile_m.group(1)}"
            if "VISA" in alt:
                info["해외겸용_일반"] = main_fee
                if mobile_m:
                    existing = info.get("연회비_비고", "")
                    visa_note = f"모바일단독(VISA): {mobile_m.group(1)}"
                    if existing and visa_note not in existing:
                        info["연회비_비고"] = f"{existing} / {visa_note}"
                    elif not existing:
                        info["연회비_비고"] = visa_note

        info["결제네트워크브랜드"] = ", ".join(brands)

    # 연회비 테이블 보완
    for t in soup.find_all("table"):
        cap = t.find("caption")
        if not cap or "연회비" not in cap.get_text():
            continue
        tbody = t.find("tbody")
        if not tbody:
            continue
        for row in tbody.find_all("tr"):
            tds = row.find_all("td")
            if not tds:
                continue
            발급유형 = tds[0].get_text(strip=True)
            합계 = tds[-1].get_text(strip=True)
            if 발급유형 == "일반":
                won = korean_to_won(합계)
                if not info["국내전용_일반"]:
                    info["국내전용_일반"] = won
                if not info["해외겸용_일반"]:
                    info["해외겸용_일반"] = won
            elif "모바일" in 발급유형 and not info["연회비_비고"]:
                info["연회비_비고"] = f"모바일단독: {korean_to_won(합계)}"
        break

    # 후불교통 여부
    info["후불교통"] = "후불교통" in soup.get_text()

    return info

def discover_main_tabs(soup) -> list[dict]:
    """
    메인 탭 메뉴를 동적으로 감지해 tab_type(benefit/fee/notice)으로 분류.
    href="#tabConXX", onclick="seleTab(...)", id 직접 탐색 3가지 방식 지원.
    """
    # 스킵할 탭 (연회비/확인사항은 전용 파서가 처리)
    FEE_KEYWORDS    = {"연회비", "annual", "fee"}
    NOTICE_KEYWORDS = {"확인사항", "유의사항", "안내사항"}

    tab_map: dict[str, str] = {}

    for a in soup.find_all("a", href=re.compile(r"^#tabCon\d{2}$")):
        m = re.search(r"#(tabCon\d{2})$", a.get("href", ""))
        if m:
            tid = m.group(1)
            txt = clean(a.get_text())
            if txt and tid not in tab_map:
                tab_map[tid] = txt

    for el in soup.find_all(["a", "button", "li"]):
        onclick = el.get("onclick", "")
        m = re.search(r"""['\"](tabCon\d{2})['\"]""", onclick)
        if m:
            tid = m.group(1)
            txt = clean(el.get_text())
            if txt and len(txt) < 25 and tid not in tab_map:
                tab_map[tid] = txt

    for div in soup.find_all("div", id=re.compile(r"^tabCon\d{2}$")):
        tid = div.get("id")
        if tid not in tab_map:
            h = div.find(["h2", "h3", "h4"])
            tab_map[tid] = clean(h.get_text()) if h else tid

    FEE_KEYWORDS    = {"연회비", "annual", "fee"}
    NOTICE_KEYWORDS = {"확인사항", "유의사항", "안내사항"}
    SKIP_KEYWORDS   = {"카드이용", "해외이용", "이용안내", "이용 안내"}
    result = []
    for tid, tname in sorted(tab_map.items()):
        tname_low = tname.lower()
        if any(k in tname_low for k in FEE_KEYWORDS):
            ttype = "fee"
        elif any(k in tname for k in NOTICE_KEYWORDS):
            ttype = "notice"
        elif tname in SKIP_KEYWORDS or any(
            re.search(rf"(^|\s){re.escape(k)}(\s|$)", tname) for k in {"이용안내", "이용 안내"}
        ):
            ttype = "notice"
        else:
            ttype = "benefit"
        result.append({"tab_id": tid, "tab_name": tname, "tab_type": ttype})
    return result


def get_subtab_names(soup, main_tab_id: str) -> dict[str, str]:
    """특정 메인 탭에 속한 서브탭 id → 이름 매핑 반환. href/onclick 방식 모두 수집."""
    prefix = main_tab_id          # "tabCon01"
    # Y가 1자리 이상이면 매칭 (tabCon010, tabCon0100 등 모두 포함)
    pattern = re.compile(rf"^{re.escape(prefix)}\d+$")
    subtab_names: dict[str, str] = {}

    # href 방식
    for a in soup.find_all("a", href=re.compile(rf"#{re.escape(prefix)}\d")):
        m = re.search(rf"#({re.escape(prefix)}\d+)", a.get("href", ""))
        if m:
            txt = clean(a.get_text())
            if txt:
                subtab_names[m.group(1)] = txt

    # onclick 방식
    for el in soup.find_all(["a", "button", "li"]):
        onclick = el.get("onclick", "")
        m = re.search(rf"""['\"]({re.escape(prefix)}\d+)['\"]""", onclick)
        if m:
            sid = m.group(1)
            if sid not in subtab_names:
                txt = clean(el.get_text())
                if txt and len(txt) < 30:
                    subtab_names[sid] = txt

    return subtab_names


def parse_benefit_tab(soup, tab_id: str, tab_name: str) -> list:
    """임의의 혜택 탭(tab_id)을 파싱. benefit_group=tab_name, benefit_title=서브탭명 또는 섹션 소제목."""
    rows = []
    div = soup.find("div", id=tab_id)
    if not div:
        return rows

    메인탭명 = tab_name
    subtab_names = get_subtab_names(soup, tab_id)

    def make_row(소제목, 혜택명, 내용, 혜택수치="", 혜택단위="",
                 전월실적="", 최대한도="", 적용가맹점="", 제외가맹점="", 서브탭명="",
                 is_업종=False):
        # 혜택요약: 혜택명을 그대로 요약으로 사용
        요약 = 혜택명[:120] if 혜택명 else ""

        return {
            "탭":        메인탭명,
            "benefit_group":  메인탭명,
            "benefit_title": 서브탭명 if 서브탭명 else 소제목,
            "혜택명":    혜택명[:120],
            "benefit_summary":  요약,
            "content":      내용,
            "benefit_value":  혜택수치,
            "benefit_unit":  혜택단위,
            "전월실적":  전월실적,
            "최대한도":  최대한도,
            "적용가맹점": 적용가맹점,
            "excluded_merchants": 제외가맹점,
            "is_업종":   is_업종,
        }

    # ── 가맹점 파싱 유틸 ─────────────────────────────────────────
    EXCLUDE_KW = ("제외", "except", "미적용", "불포함", "해당없음", "excluded_merchants", "제외 가맹점")
    INCLUDE_KW = ("적용", "대상", "해당", "포함", "가맹점명", "업종", "이용처")

    def split_merchants(items: list[str]) -> tuple[list[str], list[str]]:
        """
        li/텍스트 목록을 적용가맹점 / 제외가맹점으로 분리.

        규칙:
        - "제외:" / "※제외" / "- 제외" 등으로 시작하는 항목 → 제외가맹점
        - "제외: A, B, C" 처럼 인라인 쉼표 목록 → 각각 분리해 제외가맹점에 추가
        - "A 제외" 처럼 끝에 '제외' 붙는 경우도 처리
        - 적용/대상 등 블록 복귀 키워드 있으면 include 블록으로 복귀
        """
        include_list, exclude_list = [], []
        in_exclude_block = False
        for item in items:
            stripped = item.strip()
            if not stripped:
                continue

            # 블록 전환: 제외 키워드로 시작하면 우선 제외 블록으로
            if any(re.match(rf"^[※\-\*]?\s*{k}", stripped) for k in EXCLUDE_KW):
                in_exclude_block = True
            # 블록 복귀: 제외 키워드가 없을 때만 적용 키워드 체크
            elif any(re.match(rf"^[※\-\*]?\s*{k}", stripped) for k in INCLUDE_KW):
                in_exclude_block = False

            # 인라인 "제외: A / B / C" 또는 "제외: A, B" 패턴
            excl_inline_m = re.match(r"^[※\-\*\s]*제외\s*[:：]\s*(.+)", stripped)
            if excl_inline_m:
                excl_val = excl_inline_m.group(1).strip()
                # 쉼표·슬래시 분리
                for part in re.split(r"[,/、·]", excl_val):
                    part = part.strip()
                    if part:
                        exclude_list.append(part)
                continue

            # 끝에 "제외" 붙는 단순 패턴 "XXX 제외"
            end_excl_m = re.match(r"^(.+?)\s+제외$", stripped)
            if end_excl_m:
                exclude_list.append(end_excl_m.group(1).strip())
                continue

            if in_exclude_block:
                exclude_list.append(stripped)
            else:
                include_list.append(stripped)
        return include_list, exclude_list

    def parse_merchant_cell(cell_el) -> tuple[str, str]:
        """
        단일 셀(td/th)에서 적용가맹점 / 제외가맹점 추출.
        셀 안에 ul/li 구조 있으면 각 li를 분리, 없으면 전체 텍스트.
        - <br> 기준 분리
        - span/strong 텍스트 포함
        - '·', '、', ',' 로 연결된 인라인 목록도 분리
        - 비고/주석성 텍스트(※, *, 주) 로 시작) 제거
        """
        # br → newline 변환 후 재파싱
        raw = str(cell_el)
        raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
        from bs4 import BeautifulSoup as BS
        cell_copy = BS(raw, "html.parser")

        lis = cell_copy.find_all("li")
        if lis:
            items = [clean(li.get_text()) for li in lis if clean(li.get_text())]
        else:
            # 줄바꿈 기준 1차 분리
            lines = [t.strip() for t in cell_copy.get_text("\n").split("\n") if t.strip()]
            # 각 줄을 '·', '、', ',' 기준으로 추가 분리 (단, 숫자 포함 문자열은 분리하지 않아 할인율 등 보호)
            items = []
            for line in lines:
                if re.search(r"[·、]", line):
                    sub = [s.strip() for s in re.split(r"[·、]", line) if s.strip()]
                    items.extend(sub)
                else:
                    items.append(line)

        # 비고성 라인 필터링 (※ * 주) 로 시작, 단독 숫자, 단독 기호 등)
        def is_noise(s: str) -> bool:
            return bool(re.match(r"^[※＊\*\(\（]|^주\)", s)) or len(s) <= 1

        items = [i for i in items if not is_noise(i)]

        incl, excl = split_merchants(items)
        return ", ".join(incl), ", ".join(excl)

    def col_idx(headers: list[str], *keywords) -> int:
        """col_headers에서 키워드 매칭 컬럼 인덱스 반환, 없으면 -1"""
        for i, h in enumerate(headers):
            if any(k in h for k in keywords):
                return i
        return -1

    def parse_table(table, 소제목, 서브탭명="", ctx_rate_map: dict = {}):
        """테이블 파싱 → 혜택 행 생성. tier table / 일반 혜택 테이블 / 가맹점 컬럼 명시 테이블 모두 지원."""
        result = []
        shared_실적 = ""
        shared_한도 = ""

        thead = table.find("thead")
        tbody = table.find("tbody")
        if tbody:
            all_trs = tbody.find_all("tr")
        else:
            all_trs = table.find_all("tr")
            if not all_trs:
                return result

        col_map: dict[int, str] = {}
        if thead:
            col_pos = 0
            for th in thead.find_all("th"):
                txt = clean(th.get_text())
                span = int(th.get("colspan", 1))
                for i in range(span):
                    col_map[col_pos + i] = txt
                col_pos += span
        elif all_trs:
            # thead 없으면 첫 행을 헤더로
            header_cells = all_trs[0].find_all(["th", "td"])
            for i, c in enumerate(header_cells):
                col_map[i] = clean(c.get_text())
            all_trs = all_trs[1:]

        col_headers = list(col_map.values())
        header_joined = " ".join(col_headers)

        # ── 비가맹점 테이블 조기 스킵 ──────────────────────────
        SKIP_TABLE_KW = (
            "1회", "1일", "월간", "출금한도",        # 이용한도 테이블
            "이자율", "수수료율",                      # 이자/수수료율 테이블
            "기본서비스", "선택서비스", "서비스명",    # 국제브랜드 서비스 테이블
            "비자(VISA)", "마스터(Master)", "마에스트로", "은련(UPI)",  # 국제브랜드별 안내
            "비고",                                    # 비고 컬럼만 있는 단순 테이블
        )
        # caption에 스킵 키워드가 있어도 조기 종료
        cap = table.find("caption")
        cap_txt = clean(cap.get_text()) if cap else ""
        CAP_SKIP_KW = ("이용한도", "수수료", "후불교통", "국제 브랜드", "이자율")
        CAP_SKIP_EXACT = (
            "해외혜택 안내", "국내혜택 안내",   # 구분|할인내용|확인사항 구조
        )
        # CAP_SKIP_KW_SOFT 제거 — 이용 안내 등 caption으로 테이블 통째 스킵하지 않음
        if any(k in header_joined for k in SKIP_TABLE_KW):
            return result
        if any(k in cap_txt for k in CAP_SKIP_KW):
            return result
        if cap_txt in CAP_SKIP_EXACT:
            return result

        # ── 컬럼 역할 감지 ─────────────────────────────────────
        def find_col(*keywords):
            for idx, h in col_map.items():
                if any(k in h for k in keywords):
                    return idx
            return -1

        idx_svc   = find_col("서비스", "구분", "항목", "혜택", "상품서비스")
        idx_rate  = find_col("할인", "적립", "혜택률", "혜택율", "혜택내용", "금액")
        idx_perf  = find_col("전월실적", "이용실적", "실적")
        idx_limit = find_col("월최대", "한도", "월한도", "최대")
        idx_incl  = find_col("적용가맹점", "target_merchants", "이용처", "가맹점명", "대상 업종", "할인대상", "할인 대상")
        idx_excl  = find_col("excluded_merchants", "제외업종", "제외대상")

        if idx_rate >= 0 and idx_rate == idx_incl:
            idx_rate = -1

        has_svc_content_col = False
        idx_svc_content = -1
        if thead:
            col_pos = 0
            for th in thead.find_all("th"):
                txt = clean(th.get_text())
                span = int(th.get("colspan", 1))
                if span == 2 and any(k in txt for k in ("서비스", "구분")):
                    idx_svc = col_pos
                    idx_svc_content = col_pos + 1
                    has_svc_content_col = True
                col_pos += span

        if idx_svc < 0:
            idx_svc = 0
        if idx_rate < 0 and idx_incl < 0:
            idx_rate = find_col("할인금액")
            if idx_rate < 0 and len(col_map) >= 2:
                idx_rate = 1

        is_tier_table = (
            len(col_map) >= 3 and
            any(re.search(r"\d+만원\s*(이상|미만|이하)", h) for h in col_headers[1:])
        )
        if is_tier_table:
            tier_labels = col_headers[1:]
            for tr in all_trs:
                cells = tr.find_all(["th", "td"])
                if not cells:
                    continue
                row_label = clean(cells[0].get_text())
                if not row_label or row_label in col_headers:
                    continue
                for i, cell in enumerate(cells[1:]):
                    val = clean(cell.get_text())
                    if not val:
                        continue
                    tier = tier_labels[i] if i < len(tier_labels) else f"구간{i+1}"
                    실적_m = re.search(r"(\d+)", tier.replace(",", ""))
                    실적_num = str(int(실적_m.group(1)) * 10000) if 실적_m and "만" in tier else \
                               extract_number(tier) if 실적_m else ""
                    혜택수치_v, 혜택단위_v = extract_benefit_value(row_label, val)
                    result.append(make_row(
                        소제목=소제목,
                        혜택명=f"{row_label} ({tier}): {val}",
                        내용=f"{row_label} | 전월실적 {tier} | {val}",
                        혜택수치=혜택수치_v, 혜택단위=혜택단위_v,
                        전월실적=실적_num, 최대한도=parse_max_benefit(val),
                        서브탭명=서브탭명,
                    ))
            return result

        # ── 일반 혜택 테이블: rowspan 구분 컬럼 추적 ──────────
        # rowspan 값이 있는 첫 번째 컬럼(구분: 해외혜택/국내혜택 등)을 추적
        rowspan_tracker: dict[int, tuple[str, int]] = {}  # col_idx → (text, remaining)

        for tr in all_trs:
            all_cells = tr.find_all(["th", "td"])
            if not all_cells:
                continue

            # rowspan 컬럼 삽입: 실제 셀 위치를 논리 컬럼 위치로 변환
            logical_cells: dict[int, str] = {}
            # 먼저 이전 행에서 이어지는 rowspan 값 채움
            for col_i, (txt, remaining) in list(rowspan_tracker.items()):
                if remaining > 0:
                    logical_cells[col_i] = txt
                    rowspan_tracker[col_i] = (txt, remaining - 1)
                    if remaining - 1 == 0:
                        del rowspan_tracker[col_i]

            # 현재 행 셀을 논리 컬럼에 배치
            cell_iter = iter(enumerate(all_cells))
            log_col = 0
            for _, cell in cell_iter:
                while log_col in logical_cells:
                    log_col += 1
                txt = clean(cell.get_text())
                colspan = int(cell.get("colspan", 1))
                rowspan = int(cell.get("rowspan", 1))
                for c in range(colspan):
                    logical_cells[log_col + c] = txt
                if rowspan > 1:
                    rowspan_tracker[log_col] = (txt, rowspan - 1)
                log_col += colspan

            def lcell(idx):
                return logical_cells.get(idx, "")

            서비스명 = lcell(idx_svc)
            서비스내용 = lcell(idx_svc_content) if has_svc_content_col else ""
            할인율 = lcell(idx_rate) if idx_rate >= 0 else ""

            if not 할인율 and ctx_rate_map:
                할인율 = (
                    ctx_rate_map.get(서비스명, "") or
                    ctx_rate_map.get(서비스명.split()[0] if 서비스명 else "", "")
                )

            if idx_perf >= 0:
                v = lcell(idx_perf)
                if v and v not in ("없음", "-"):
                    shared_실적 = extract_number(v) or v

            row_한도 = ""
            if idx_limit >= 0:
                v = lcell(idx_limit)
                if v and v not in ("없음", "-"):
                    row_한도 = v

            # 헤더행·빈행 스킵
            if not 서비스명 or 서비스명 in col_headers:
                continue
            SKIP_SVC = ("서비스", "구분", "상품서비스 요약", "해외혜택", "국내혜택")
            if 서비스명 in SKIP_SVC:
                continue

            skip_merchant = False

            _bracket_m = re.search(r"\[([^\]]+)\]", 서비스명)
            bracket_merchants: list[str] = []
            if _bracket_m:
                bracket_merchants = [x.strip() for x in _bracket_m.group(1).split(",") if x.strip()]
                서비스명 = 서비스명[:_bracket_m.start()].strip()

            row_is_업종 = False
            if idx_incl >= 0:
                incl_raw = lcell(idx_incl)
                incl_header = col_map.get(idx_incl, "")
                if "업종" in incl_header or "결제방법" in incl_header:
                    incl_txt = incl_raw.rstrip("*").strip()
                    row_is_업종 = True
                else:
                    incl_parts = _split_by_comma(incl_raw)
                    incl_txt = ", ".join(p for p in incl_parts if p.strip()) or incl_raw
                excl_txt = lcell(idx_excl) if idx_excl >= 0 else ""
            elif has_svc_content_col:
                is_desc = bool(re.search(r"업종|결제 시|이용 시|이상|이내|\d+원 이상|수수료|면제|이용 수수료", 서비스내용))
                if not is_desc:
                    incl_parts = _split_by_comma(서비스내용)
                    incl_txt = ", ".join(p for p in incl_parts if p.strip())
                else:
                    incl_txt = ""
                if not incl_txt:
                    incl_txt = 서비스명
                excl_txt = ""
            else:
                svc_el = all_cells[0] if all_cells else None
                if svc_el:
                    lis_in_svc = svc_el.find_all("li")
                    if lis_in_svc:
                        items = [clean(li.get_text()) for li in lis_in_svc if clean(li.get_text())]
                        incl_list, excl_list = split_merchants(items)
                        incl_txt = ", ".join(incl_list)
                        excl_txt = ", ".join(excl_list)
                    else:
                        incl_txt = 서비스명
                        excl_txt = ""
                else:
                    incl_txt = 서비스명
                    excl_txt = ""

            혜택수치, 혜택단위 = extract_benefit_value(서비스명, 할인율)
            율_m = re.search(r"([\d.]+%|[\d,]+원|면제)", 할인율)
            혜택율 = 율_m.group(1) if 율_m else 할인율
            혜택명 = f"{서비스명} {혜택율}" if 혜택율 and 혜택율 != 서비스명 else 서비스명

            if skip_merchant:
                incl_txt, excl_txt = "", ""
            elif bracket_merchants:
                if not incl_txt or incl_txt == 서비스명:
                    incl_txt = ", ".join(bracket_merchants)

            _PAY_METHOD_RE = re.compile(r"(KB\s*Pay|페이|Pay|결제\s*수단|간편결제).*(결제|이용)\s*(시|할인)", re.I)
            if row_is_업종 and _PAY_METHOD_RE.search(incl_txt):
                incl_txt = ""
                row_is_업종 = False

            result.append(make_row(
                소제목=소제목,
                혜택명=혜택명,
                내용=f"{서비스명}"
                    + (f" | {서비스내용}" if 서비스내용 else "")
                    + (f" | {할인율}" if 할인율 else "")
                    + (f" | 전월실적: {shared_실적}" if shared_실적 else "")
                    + (f" | 월한도: {row_한도}" if row_한도 else ""),
                혜택수치=혜택수치, 혜택단위=혜택단위,
                전월실적=shared_실적, 최대한도=parse_max_benefit(row_한도),
                적용가맹점=incl_txt, 제외가맹점=excl_txt,
                서브탭명=서브탭명,
                is_업종=row_is_업종,
            ))
        return result

    def _parse_titArea(el, current_소제목, 서브탭명):
        """titArea div: h3.tit 소제목 + 하위 li/dl/table 파싱 → make_row 반환."""
        h3 = el.find("h3", class_="tit")
        if not h3:
            return current_소제목, []

        rate_map: dict[str, str] = {}
        h3_text_full = clean(h3.get_text())
        for m in re.finditer(r"([가-힣a-zA-Z\s]+?)\s*([\d.]+%)", h3_text_full):
            key = m.group(1).strip()
            val = m.group(2).strip()
            if key and len(key) >= 2:
                rate_map[key] = val
                first_word = key.split()[0]
                if first_word != key:
                    rate_map.setdefault(first_word, val)

        p_txts = h3.find_all("p", class_="txt")
        p_merchant = None
        for p in p_txts:
            txt_val = clean(p.get_text())
            if txt_val and not re.fullmatch(r"[\d.]+%|[\d,]+원|면제", txt_val):
                p_merchant = p
                break

        if p_merchant:
            h3_copy = h3.__copy__()
            for p in h3_copy.find_all("p", class_="txt"):
                p.decompose()
            prefix = clean(h3_copy.get_text())
            suffix = clean(p_merchant.get_text())
            tit = f"{prefix} {suffix}".strip() if prefix else suffix
        else:
            tit = clean(h3.get_text())
        if tit:
            current_소제목 = tit

        p_merchants_from_txt: list[str] = []
        if p_merchant:
            from bs4 import BeautifulSoup as _BS
            p_copy = _BS(str(p_merchant), "html.parser").find("p") or _BS(str(p_merchant), "html.parser")
            ems = p_copy.find_all("em")
            for em in p_copy.find_all("em"):
                em.decompose()
            text_nodes = clean(p_copy.get_text())
            BENEFIT_WORDS = re.compile(r"^(면제|할인|적립|캐시백|무료|서비스|제공)\s*$")
            text_is_benefit = not text_nodes or BENEFIT_WORDS.match(text_nodes)
            if text_is_benefit and ems:
                for em_tag in ems:
                    em_txt = clean(em_tag.get_text())
                    em_txt = re.sub(r"[\d.]+%|[\d,]+원|면제|할인$", "", em_txt).strip()
                    if em_txt and len(em_txt) >= 2 and not re.search(r"수수료$|요금$|이용료$", em_txt):
                        p_merchants_from_txt.append(em_txt)
            else:
                raw_txt = re.sub(r"[\d.]+%|[\d,]+원|면제|할인$", "", text_nodes).strip()
                if raw_txt:
                    p_merchants_from_txt = [
                        p for p in _split_by_comma(raw_txt)
                        if p and len(p) >= 2
                        and not re.search(r"수수료$|요금$|이용료$", p)
                    ]

        all_items = []
        include_cls_kw = ("include", "apply", "대상", "적용")
        exclude_cls_kw = ("exclude", "except", "제외")
        explicit_include, explicit_exclude = [], []

        for child in el.find_all(["ul", "ol", "dl"]):
            child_cls = " ".join(child.get("class", []))
            if any(k in child_cls for k in ("mT", "caution")):
                continue
            is_incl = any(k in child_cls for k in include_cls_kw)
            is_excl = any(k in child_cls for k in exclude_cls_kw)
            child_items = [clean(t.get_text())
                           for t in child.find_all(["li", "dt", "dd"])
                           if clean(t.get_text())]
            if is_incl:
                explicit_include.extend(child_items)
            elif is_excl:
                explicit_exclude.extend(child_items)
            else:
                all_items.extend(child_items)

        if explicit_include or explicit_exclude:
            incl_list = explicit_include
            excl_list = explicit_exclude
        else:
            incl_list, excl_list = split_merchants(all_items)

        # 소제목에서 혜택수치 추출
        율_m = re.search(r"([\d.]+%|[\d,]+원)", current_소제목)
        혜택율 = 율_m.group(1) if 율_m else ""
        혜택수치 = re.sub(r"[^\d.]", "", 혜택율.replace(",", "")) if 혜택율 else ""
        혜택단위 = "%" if "%" in 혜택율 else "원" if "원" in 혜택율 else ""

        # 소제목에서 베이스 가맹점명 추출 ([업종] 브래킷)
        bracket_m = re.search(r"\[(.+?)\]", current_소제목)
        if bracket_m:
            bv = bracket_m.group(1).strip()
            ab = re.sub(r"^\[.*?\]\s*", "", current_소제목).strip()
            base_가맹점 = f"{bv} / {ab}" if ab else bv
        else:
            base_가맹점 = current_소제목

        # 적용가맹점: 우선순위 - p.txt추출 > incl_list > all_items > base_가맹점
        # base_가맹점이 수수료/혜택설명어면 가맹점으로 쓰지 않음
        # "국내 가맹점", "해외 가맹점" 은 업종명이 아니라 적용범위 → 소제목 유지, 가맹점은 공란
        _REGION_ONLY = re.compile(r"^(국내|해외)\s*(전체\s*)?가맹점$")
        BASE_NOISE = re.compile(r"수수료|면제|이자율|이용료|할인한도|반환|유예|안내|약관")
        if p_merchants_from_txt:
            # p.txt 추출값도 지역어면 공란
            filtered_p = [m for m in p_merchants_from_txt if not _REGION_ONLY.match(m)]
            적용가맹점 = ", ".join(filtered_p)
        elif incl_list:
            적용가맹점 = ", ".join(incl_list)
        elif all_items:
            적용가맹점 = ", ".join(all_items)
        else:
            if BASE_NOISE.search(base_가맹점) or _REGION_ONLY.match(base_가맹점.strip()):
                적용가맹점 = ""
            else:
                적용가맹점 = base_가맹점
        제외가맹점 = ", ".join(excl_list)

        내용 = current_소제목 + (" | " + " / ".join(all_items) if all_items else "")

        # ── 하위 table.tblH가 '구분|할인대상' 2컬럼이면 per-row 생성 ──
        # 이 경우 단일 행 대신 구분별 여러 행을 반환
        sub_tbl = el.find("table", class_="tblH")
        if sub_tbl and rate_map:
            thead = sub_tbl.find("thead")
            tbody = sub_tbl.find("tbody")
            if thead and tbody:
                hdr_texts = [clean(th.get_text()) for th in thead.find_all(["th","td"])]
                is_2col = (
                    len(hdr_texts) == 2 and
                    any(k in hdr_texts[0] for k in ("구분",)) and
                    any(k in hdr_texts[1] for k in ("할인대상", "이용처", "대상"))
                )
                if is_2col:
                    sub_rows = []
                    for tr in tbody.find_all("tr"):
                        cells = tr.find_all(["th","td"])
                        if len(cells) < 2:
                            continue
                        구분 = clean(cells[0].get_text())
                        대상_raw = clean(cells[1].get_text())
                        대상_clean = re.sub(
                            r"\s*(이동통신\s*)?자동납부\s*요금$|"
                            r"\s+멤버십\s+자동납부\s*요금$|"
                            r"\s+자동납부요금$", "", 대상_raw
                        ).strip()
                        merchants = ", ".join(
                            p.strip() for p in re.split(r"[,，]\s*", 대상_clean) if p.strip()
                        )
                        row_rate = (
                            rate_map.get(구분, "") or
                            rate_map.get(구분.split()[0] if 구분 else "", "")
                        )
                        rv, ru = extract_benefit_value(구분, row_rate)
                        sub_rows.append(make_row(
                            소제목=current_소제목,
                            혜택명=f"{구분} {row_rate}".strip() if row_rate else 구분,
                            내용=f"{구분} | {대상_raw}" + (f" | {row_rate}" if row_rate else ""),
                            혜택수치=rv, 혜택단위=ru,
                            적용가맹점=merchants,
                            서브탭명=서브탭명,
                        ))
                    if sub_rows:
                        return current_소제목, sub_rows

        row = make_row(
            소제목=current_소제목, 혜택명=current_소제목,
            내용=내용, 혜택수치=혜택수치, 혜택단위=혜택단위,
            적용가맹점=적용가맹점, 제외가맹점=제외가맹점,
            서브탭명=서브탭명,
        )
        return current_소제목, [row]

    def parse_subtab(container, 서브탭명="", _소제목=None):
        """서브탭 컨테이너 안의 섹션을 순서대로 파싱."""
        result = []
        current_소제목 = _소제목 if _소제목 is not None else 서브탭명
        current_rate_map: dict[str, str] = {}

        titDep2_sections = parse_titDep2_section(container)
        if titDep2_sections:
            for sec in titDep2_sections:
                h4_text = sec["section_title"]
                inc = sec["include_merchants"]
                exc = sec["exclude_merchants"]
                율_m = re.search(r"([\d.]+)%", h4_text)
                혜택수치_v = 율_m.group(1) if 율_m else ""
                혜택단위_v = "%" if 율_m else ""
                clean_title = re.sub(r"^\[.*?\]\s*", "", h4_text).strip()
                clean_title = re.sub(r"\s*\d+%.*$", "", clean_title).strip() or h4_text
                result.append(make_row(
                    소제목=clean_title, 혜택명=clean_title, 내용=h4_text,
                    혜택수치=혜택수치_v, 혜택단위=혜택단위_v,
                    적용가맹점=", ".join(inc), 제외가맹점=", ".join(exc),
                    서브탭명=서브탭명,
                ))
            return result

        for el in container.children:
            if not hasattr(el, "name") or not el.name:
                continue
            if el.name in ("h2", "h3", "h4", "h5"):
                cls = " ".join(el.get("class", []))
                if "blind" in cls:
                    continue
                txt = clean(el.get_text())
                if txt:
                    current_소제목 = txt
                continue
            if el.name == "table":
                cap = el.find("caption")
                if cap:
                    cap_txt = clean(cap.get_text())
                    if cap_txt and cap_txt not in ("서비스", "구분"):
                        current_소제목 = cap_txt
                result.extend(parse_table(el, current_소제목, 서브탭명,
                                          ctx_rate_map=current_rate_map))
                current_rate_map = {}
                continue
            if el.name in ("ul", "ol"):
                el_cls = " ".join(el.get("class", []))
                if any(k in el_cls for k in ("mT15", "mT20", "mT30", "caution")):
                    continue
                items = [clean(li.get_text()) for li in el.find_all("li", recursive=False)
                         if clean(li.get_text())]
                if not items:
                    continue
                combined_text = current_소제목 + " ".join(items)
                is_merchant_list = any(k in combined_text for k in
                    ("가맹점", "업종", "이용처", "브랜드", "할인처", "적립처",
                     "편의점", "카페", "마트", "주유", "백화점", "외식", "영화"))
                if is_merchant_list:
                    incl_list, excl_list = split_merchants(items)
                    if result and not result[-1].get("적용가맹점"):
                        result[-1]["적용가맹점"] = ", ".join(incl_list)
                        result[-1]["excluded_merchants"] = ", ".join(excl_list)
                    else:
                        혜택수치, 혜택단위 = extract_benefit_value(current_소제목, " ".join(items))
                        result.append(make_row(
                            소제목=current_소제목, 혜택명=current_소제목,
                            내용=" / ".join(items),
                            혜택수치=혜택수치, 혜택단위=혜택단위,
                            적용가맹점=", ".join(incl_list),
                            제외가맹점=", ".join(excl_list),
                            서브탭명=서브탭명,
                        ))
                else:
                    for 구분 in items:
                        혜택수치, 혜택단위 = extract_benefit_value(current_소제목, 구분)
                        result.append(make_row(
                            소제목=current_소제목, 혜택명=구분,
                            내용=구분, 혜택수치=혜택수치, 혜택단위=혜택단위,
                            서브탭명=서브탭명,
                        ))
                continue
            if el.name == "p":
                txt = clean(el.get_text())
                if not txt:
                    continue
                if len(txt) <= 80 and re.search(r"팩|선택|택\d|서비스", txt):
                    current_소제목 = txt
                else:
                    혜택수치, 혜택단위 = extract_benefit_value(current_소제목, txt)
                    result.append(make_row(
                        소제목=current_소제목, 혜택명=txt[:80],
                        내용=txt, 혜택수치=혜택수치, 혜택단위=혜택단위,
                        서브탭명=서브탭명,
                    ))
                continue
            if el.name == "div":
                cls = " ".join(el.get("class", []))
                if "titArea" in cls:
                    current_소제목, rows_from_area = _parse_titArea(el, current_소제목, 서브탭명)
                    result.extend(rows_from_area)
                    h3_el = el.find("h3", class_="tit")
                    if h3_el:
                        h3_txt = clean(h3_el.get_text())
                        _rmap: dict[str, str] = {}
                        for _m in re.finditer(r"([가-힣a-zA-Z\s]+?)\s*([\d.]+%)", h3_txt):
                            _k = _m.group(1).strip()
                            _v = _m.group(2).strip()
                            if _k and len(_k) >= 2:
                                _rmap[_k] = _v
                                _rmap.setdefault(_k.split()[0], _v)
                        if _rmap:
                            current_rate_map = _rmap
                    continue
                sub_result, current_소제목, sub_rmap = parse_subtab_ret(el, 서브탭명, current_소제목)
                result.extend(sub_result)
                if sub_rmap:
                    current_rate_map.update(sub_rmap)
        return result

    def parse_subtab_ret(container, 서브탭명, current_소제목):
        """재귀 호출용: (result, current_소제목, rate_map) 반환."""
        result = []
        current_rate_map: dict[str, str] = {}

        titDep2_sections = parse_titDep2_section(container)
        if titDep2_sections:
            for sec in titDep2_sections:
                h4_text = sec["section_title"]
                inc = sec["include_merchants"]
                exc = sec["exclude_merchants"]
                율_m = re.search(r"([\d.]+)%", h4_text)
                혜택수치_v = 율_m.group(1) if 율_m else ""
                혜택단위_v = "%" if 율_m else ""
                clean_title = re.sub(r"^\[.*?\]\s*", "", h4_text).strip()
                clean_title = re.sub(r"\s*\d+%.*$", "", clean_title).strip() or h4_text
                result.append(make_row(
                    소제목=clean_title, 혜택명=clean_title, 내용=h4_text,
                    혜택수치=혜택수치_v, 혜택단위=혜택단위_v,
                    적용가맹점=", ".join(inc), 제외가맹점=", ".join(exc),
                    서브탭명=서브탭명,
                ))
            return result, current_소제목, current_rate_map

        for el in container.children:
            if not hasattr(el, "name") or not el.name:
                continue
            if el.name in ("h2", "h3", "h4", "h5"):
                if "blind" in " ".join(el.get("class", [])):
                    continue
                txt = clean(el.get_text())
                if txt:
                    current_소제목 = txt
                continue
            if el.name == "table":
                cap = el.find("caption")
                if cap:
                    cap_txt = clean(cap.get_text())
                    if cap_txt and cap_txt not in ("서비스", "구분"):
                        current_소제목 = cap_txt
                result.extend(parse_table(el, current_소제목, 서브탭명,
                                          ctx_rate_map=current_rate_map))
                current_rate_map = {}
                continue
            if el.name in ("ul", "ol"):
                el_cls = " ".join(el.get("class", []))
                if any(k in el_cls for k in ("mT15", "mT20", "mT30", "caution")):
                    continue
                items = [clean(li.get_text()) for li in el.find_all("li", recursive=False)
                         if clean(li.get_text())]
                if not items:
                    continue
                combined_text = current_소제목 + " ".join(items)
                is_merchant_list = any(k in combined_text for k in
                    ("가맹점", "업종", "이용처", "브랜드", "할인처", "적립처",
                     "편의점", "카페", "마트", "주유", "백화점", "외식", "영화"))
                if is_merchant_list:
                    incl_list, excl_list = split_merchants(items)
                    if result and not result[-1].get("적용가맹점"):
                        result[-1]["적용가맹점"] = ", ".join(incl_list)
                        result[-1]["excluded_merchants"] = ", ".join(excl_list)
                    else:
                        혜택수치, 혜택단위 = extract_benefit_value(current_소제목, " ".join(items))
                        result.append(make_row(
                            소제목=current_소제목, 혜택명=current_소제목,
                            내용=" / ".join(items),
                            혜택수치=혜택수치, 혜택단위=혜택단위,
                            적용가맹점=", ".join(incl_list),
                            제외가맹점=", ".join(excl_list),
                            서브탭명=서브탭명,
                        ))
                else:
                    for 구분 in items:
                        혜택수치, 혜택단위 = extract_benefit_value(current_소제목, 구분)
                        result.append(make_row(
                            소제목=current_소제목, 혜택명=구분,
                            내용=구분, 혜택수치=혜택수치, 혜택단위=혜택단위,
                            서브탭명=서브탭명,
                        ))
                continue
            if el.name == "p":
                txt = clean(el.get_text())
                if not txt:
                    continue
                if len(txt) <= 80 and re.search(r"팩|선택|택\d|서비스", txt):
                    current_소제목 = txt
                else:
                    혜택수치, 혜택단위 = extract_benefit_value(current_소제목, txt)
                    result.append(make_row(
                        소제목=current_소제목, 혜택명=txt[:80],
                        내용=txt, 혜택수치=혜택수치, 혜택단위=혜택단위,
                        서브탭명=서브탭명,
                    ))
                continue
            if el.name == "div":
                cls = " ".join(el.get("class", []))
                if "titArea" in cls:
                    current_소제목, rows_from_area = _parse_titArea(el, current_소제목, 서브탭명)
                    result.extend(rows_from_area)
                    h3_el = el.find("h3", class_="tit")
                    if h3_el:
                        _txt = clean(h3_el.get_text())
                        _rmap: dict[str, str] = {}
                        for _m in re.finditer(r"([가-힣a-zA-Z\s]+?)\s*([\d.]+%)", _txt):
                            _k = _m.group(1).strip()
                            _v = _m.group(2).strip()
                            if _k and len(_k) >= 2:
                                _rmap[_k] = _v
                                _rmap.setdefault(_k.split()[0], _v)
                        if _rmap:
                            current_rate_map.update(_rmap)
                    continue
                sub_r, current_소제목, sub_rmap = parse_subtab_ret(el, 서브탭명, current_소제목)
                result.extend(sub_r)
                if sub_rmap:
                    current_rate_map.update(sub_rmap)
        return result, current_소제목, current_rate_map

    subtab_pattern = re.compile(rf"^{re.escape(tab_id)}\d+$")
    subtabs = div.find_all("div", id=subtab_pattern)
    if not subtabs:
        has_direct_content = bool(
            div.find("table", recursive=False) or
            div.find("table") or
            div.find("h4", class_="titDep2") or
            div.find("div", class_=lambda c: c and "benefitBox" in " ".join(c))
        )
        if not has_direct_content:
            parent = div.parent
            if parent:
                subtabs = [d for d in parent.find_all("div", id=subtab_pattern)
                           if d is not div]

    if subtabs:
        for sub in subtabs:
            sid = sub.get("id", "")
            서브탭명 = subtab_names.get(sid, "")
            if not 서브탭명:
                h = sub.find(["h2", "h3", "h4"])
                서브탭명 = clean(h.get_text()) if h else sid
            rows.extend(parse_subtab(sub, 서브탭명))
    else:
        benefit_list = div.find("div", class_="benefitList1")
        target_div = benefit_list if benefit_list else div
        for li in target_div.find_all("li"):
            wrap = li.find("div", class_="wrap")
            search_el = wrap if wrap else li
            tit = search_el.find("strong", class_="tit")
            txt_el = search_el.find("span", class_="txt")
            if tit and txt_el:
                소분류 = clean(tit.get_text())
                내용_raw = clean(txt_el.get_text())
                혜택수치, 혜택단위 = extract_benefit_value(소분류, 내용_raw)
                rows.append(make_row(
                    소제목=소분류, 혜택명=소분류, 내용=내용_raw,
                    혜택수치=혜택수치, 혜택단위=혜택단위,
                    적용가맹점=소분류,
                ))
        if not rows:
            rows.extend(parse_subtab(div, ""))
    return rows

def parse_notice_tabs_for_benefit(soup, notice_tab_ids: list[str]) -> list:
    """notice 탭 파싱 → card_benefit 유의사항 행. 비어있으면 tabCon03 fallback."""
    fallback_ids = ["tabCon03"] if not notice_tab_ids else notice_tab_ids
    all_rows = []
    seen_texts: set[str] = set()
    for tid in fallback_ids:
        rows = parse_tab_for_notices(soup, tid)
        for r in rows:
            key = r.get("content", "")
            if key not in seen_texts:
                seen_texts.add(key)
                all_rows.append(r)
    return all_rows


def parse_fee_tabs(soup, fee_tab_ids: list[str]) -> tuple:
    """fee 탭 파싱 → (요약 dict, 상세 행 list). 비어있으면 tabCon02 fallback."""
    fallback_ids = ["tabCon02"] if not fee_tab_ids else fee_tab_ids
    merged_summary = {
        "국내전용_일반": "", "해외겸용_일반": "",
        "국내전용_프리미엄": "", "해외겸용_프리미엄": "",
        "연회비_비고": "", "결제네트워크브랜드": "",
    }
    all_detail: list[dict] = []
    for tid in fallback_ids:
        summary, detail = parse_tab02_by_id(soup, tid)
        all_detail.extend(detail)
        for key, val in summary.items():
            if val and not merged_summary.get(key):
                merged_summary[key] = val
    return merged_summary, all_detail


def parse_tab_for_notices(soup, tab_id: str) -> list:
    """확인사항 탭 → card_benefit 유의사항 행 생성."""
    rows = []
    seen = set()

    tab_div = soup.find("div", id=tab_id)
    if not tab_div:
        return rows
    sub_pattern = re.compile(rf"^{re.escape(tab_id)}\d+$")
    sub_divs = tab_div.find_all("div", id=sub_pattern)
    containers = sub_divs if sub_divs else [tab_div]

    def walk_list(list_tag, 소제목):
        for li in list_tag.find_all("li", recursive=False):
            # 중첩 ul/ol/p 제거 후 부모 텍스트만 추출
            from bs4 import BeautifulSoup as BS
            li_copy = BS(str(li), "html.parser").find("li")
            for nested in li_copy.find_all(["ul", "ol", "p"]):
                nested.decompose()
            parent_txt = clean(li_copy.get_text())
            if parent_txt and len(parent_txt) > 4 and parent_txt not in seen:
                seen.add(parent_txt)
                rows.append({
                    "탭":        "확인사항",
                    "benefit_group":  "확인사항",
                    "benefit_title": 소제목,
                    "혜택명":    parent_txt[:80],
                    "benefit_summary":  "",
                    "content":      parent_txt,
                    "benefit_value":  "", "benefit_unit": "",
                    "전월실적":  "", "최대한도": "",
                    "적용가맹점": "", "excluded_merchants": "",
                })
            # 중첩 항목도 같은 소제목으로 재귀
            for nested_ul in li.find_all(["ul", "ol"], recursive=False):
                walk_list(nested_ul, 소제목)

    def parse_section(container, default_sub="확인사항"):
        current_sub = default_sub
        for el in container.children:
            if not hasattr(el, "name") or not el.name:
                continue
            if el.name in ("h2", "h3", "h4", "h5"):
                current_sub = clean(el.get_text()) or default_sub
            elif el.name in ("ul", "ol"):
                walk_list(el, current_sub)
            elif el.name == "div":
                parse_section(el, current_sub)

    for container in containers:
        parse_section(container)
    return rows


# 연회비 탭 안에서 실제 연회비 섹션으로 인정할 키워드
_FEE_SECTION_KW  = ("연회비", "annual", "fee", "본인카드", "가족카드", "발급")
# 연회비 탭 안에서 스킵할 비연회비 섹션 키워드
_SKIP_SECTION_KW = ("이용한도", "출금한도", "직불한도", "후불교통", "이용가능", "한도안내",
                    "출금", "이체", "해외ATM", "ATM", "이용금액")

def _is_fee_section(section_name: str) -> bool:
    """섹션명이 연회비 섹션인지 판별"""
    if not section_name:
        return True  # 섹션명 없으면 연회비로 간주 (첫 테이블)
    low = section_name
    if any(k in low for k in _SKIP_SECTION_KW):
        return False
    return True  # 연회비 키워드 없어도 기본 허용 (신용카드는 섹션명 없는 경우 많음)

def _is_fee_table(table) -> bool:
    """
    테이블이 실제 연회비 금액 테이블인지 구조로 검증.
    - thead th에 VISA/MasterCard/국내전용/발급유형 포함 → 연회비
    - caption에 "연회비" 포함 → 연회비
    - 모든 셀 텍스트에 숫자+원 패턴만 있고 "한도"/"일" 등 이용한도 키워드 있으면 → 스킵
    """
    cap = table.find("caption")
    if cap:
        cap_txt = clean(cap.get_text())
        if any(k in cap_txt for k in _SKIP_SECTION_KW):
            return False
        if "연회비" in cap_txt:
            return True

    thead = table.find("thead")
    if thead:
        header_txt = clean(thead.get_text())
        # 이용한도 테이블 헤더 패턴
        if any(k in header_txt for k in ("1회", "1일", "월간", "한도", "출금", "이체")):
            return False
        # 연회비 테이블 헤더 패턴
        if any(k in header_txt for k in ("VISA", "Master", "UnionPay", "국내전용", "해외겸용",
                                          "국제브랜드", "발급유형", "연회비")):
            return True

    # tbody 첫 번째 th 텍스트가 "일반"/"프리미엄"/"모바일"/"총 연회비" → 연회비
    tbody = table.find("tbody")
    if tbody:
        first_th = tbody.find("th")
        if first_th:
            th_txt = clean(first_th.get_text())
            if any(k in th_txt for k in ("일반", "프리미엄", "모바일", "총 연회비", "연회비")):
                return True
            # "1회", "1일", "월간", 숫자만 → 이용한도
            if re.match(r"^(1회|1일|월간|비고|이용일|출금일|\d)$", th_txt):
                return False

    return True  # 불명확하면 허용 (연회비로 처리)


def parse_tab02_by_id(soup, tab_id: str) -> tuple:
    """연회비 탭 파싱 → (요약 dict, 상세 행 list)."""
    summary = {
        "국내전용_일반": "", "해외겸용_일반": "",
        "국내전용_프리미엄": "", "해외겸용_프리미엄": "",
        "연회비_비고": "", "결제네트워크브랜드": "",
    }
    detail_rows = []

    # 서브탭(tabConXX0 등) 우선, 없으면 메인 탭
    div = soup.find("div", id=tab_id + "0") or soup.find("div", id=tab_id)
    if not div:
        return summary, detail_rows

    current_section = ""
    brands = []
    col_headers = []
    seen_notice: set[str] = set()

    def _add_notice(소제목, txt):
        """연회비 탭 안내문을 유의사항 행으로 추가"""
        txt = clean(txt)
        if not txt or len(txt) <= 4 or txt in seen_notice:
            return
        seen_notice.add(txt)
        detail_rows.append({
            "탭":        "연회비",
            "benefit_group":  "연회비",
            "benefit_title": 소제목 or "연회비 안내",
            "혜택명":    txt[:80],
            "content":      txt,
            "benefit_value":  "", "benefit_unit": "",
            "전월실적":  "", "최대한도":  "",
            "적용가맹점": "", "excluded_merchants": "",
        })

    def _walk_ul(ul_tag, 소제목):
        """ul의 li를 순회하며 안내 텍스트 수집 (중첩 포함)"""
        from bs4 import BeautifulSoup as BS
        for li in ul_tag.find_all("li", recursive=False):
            li_copy = BS(str(li), "html.parser").find("li")
            for nested in li_copy.find_all(["ul", "ol", "p"]):
                nested.decompose()
            parent_txt = clean(li_copy.get_text())
            _add_notice(소제목, parent_txt)
            # 중첩 ul도 같은 소제목으로 재귀
            for sub_ul in li.find_all(["ul", "ol"], recursive=False):
                _walk_ul(sub_ul, 소제목)

    # ── h2/h3/h4/table/ul을 순서대로 처리 ──────────────────────
    for tag in div.find_all(["h2", "h3", "h4", "table", "ul"]):
        # ── 섹션 헤딩 ──────────────────────────────────────────
        if tag.name in ("h2", "h3", "h4"):
            # blind 클래스 스크린리더용 헤딩은 섹션명으로 안 씀
            if "blind" in " ".join(tag.get("class", [])):
                continue
            current_section = clean(tag.get_text())
            col_headers = []
            continue

        if tag.name == "ul":
            if not _is_fee_section(current_section):
                continue
            if tag.find_parent("ul"):
                continue
            _walk_ul(tag, current_section or "연회비 안내")
            continue

        if tag.name == "table":
            if not _is_fee_section(current_section):
                continue
            if not _is_fee_table(tag):
                continue

            thead = tag.find("thead")
            tbody = tag.find("tbody")
            if not tbody:
                continue

            if thead:
                for th in thead.find_all("th"):
                    t = clean(th.get_text())
                    t_upper = t.upper()
                    for brand, aliases in [("VISA", ["VISA"]), ("Master", ["MASTER"]),
                                           ("UnionPay", ["UNIONPAY", "UPI"])]:
                        if any(a in t_upper for a in aliases) and brand not in brands:
                            brands.append(brand)
                    if "국내전용" in t and "Local" not in brands:
                        brands.append("Local")
                col_headers = [
                    clean(th.get_text()) for th in thead.find_all("th")
                    if clean(th.get_text()) and "구분" not in clean(th.get_text())
                ]

            is_본인 = "본인" in current_section or current_section in ("", "연회비")
            is_가족 = "가족" in current_section
            구분명 = "본인" if is_본인 else "가족"

            # 합계 컬럼 인덱스 (summary 추출용)
            합계_idx = next(
                (i for i, h in enumerate(col_headers) if "합계" in h), -1
            )

            for tr in tbody.find_all("tr"):
                ths = tr.find_all("th")
                tds = tr.find_all("td")

                # th가 없는 행(모바일 단독 등) → 이전 th label 재사용
                if not ths:
                    row_label = "모바일"
                    all_tds = tds
                else:
                    row_label = clean(ths[0].get_text())
                    all_tds = tds

                # 이용한도 행 스킵
                if re.match(r"^(1회|1일|월간|비고|이용일|출금일)$", row_label):
                    continue

                raw_texts = [clean(td.get_text()) for td in all_tds]
                vals = [fee_to_number(t) for t in raw_texts]

                for i, raw_txt in enumerate(raw_texts):
                    if not raw_txt or raw_txt in ("-", ""):
                        continue
                    if i < len(col_headers):
                        col_name = col_headers[i]
                    else:
                        _BRAND_FALLBACK = ["국내외겸용(Visa)", "국내외겸용(Master)", "국내외겸용(UnionPay)", "국내전용"]
                        col_name = _BRAND_FALLBACK[i] if i < len(_BRAND_FALLBACK) else f"옵션{i+1}"
                    val = vals[i] if i < len(vals) else ""
                    detail_rows.append({
                        "탭":        "연회비",
                        "benefit_group":  "연회비",
                        "benefit_title": current_section or "연회비",
                        "혜택명":    f"{구분명}_{col_name} {row_label}",
                        "content":      f"{구분명} {col_name} {row_label}: {raw_txt}",
                        "benefit_value":  val,
                        "benefit_unit":  "원" if val else "",
                        "전월실적":  "",
                        "최대한도":  "",
                        "적용가맹점": "",
                        "excluded_merchants": "",
                    })

                발급유형 = clean(all_tds[0].get_text()) if all_tds else ""
                is_일반행 = "일반" in row_label or "일반" in 발급유형
                is_모바일행 = "모바일" in row_label and "일반" not in row_label
                if is_일반행:
                    if is_본인:
                        dom_val = ""
                        for_val = ""
                        for i, col_name in enumerate(col_headers):
                            if i >= len(vals) or not vals[i]:
                                continue
                            col_upper = col_name.upper()
                            if "국내전용" in col_name or ("LOCAL" in col_upper and "VISA" not in col_upper):
                                dom_val = vals[i]
                            elif any(b in col_upper for b in ("VISA", "MASTER", "UNIONPAY", "UPI")) or "해외겸용" in col_name or "국내외겸용" in col_name:
                                for_val = vals[i]
                        if dom_val or for_val:
                            if dom_val:
                                summary["국내전용_일반"] = dom_val
                            if for_val:
                                summary["해외겸용_일반"] = for_val
                            if dom_val and not for_val:
                                summary["해외겸용_일반"] = dom_val
                            if for_val and not dom_val:
                                summary["국내전용_일반"] = for_val
                        else:
                            합계_val = vals[합계_idx] if 합계_idx >= 0 and 합계_idx < len(vals) else ""
                            if not 합계_val:
                                합계_val = next((v for v in reversed(vals) if v and re.search(r"\d", v)), "")
                            if 합계_val:
                                summary["국내전용_일반"] = 합계_val
                                summary["해외겸용_일반"] = 합계_val
                    elif is_가족:
                        dom_val = ""
                        for_val = ""
                        for i, col_name in enumerate(col_headers):
                            if i >= len(vals) or not vals[i]:
                                continue
                            col_upper = col_name.upper()
                            if "국내전용" in col_name or ("LOCAL" in col_upper and "VISA" not in col_upper):
                                dom_val = vals[i]
                            elif any(b in col_upper for b in ("VISA", "MASTER", "UNIONPAY", "UPI")) or "해외겸용" in col_name or "국내외겸용" in col_name:
                                for_val = vals[i]
                        if dom_val or for_val:
                            if dom_val:
                                summary["국내전용_프리미엄"] = dom_val
                            if for_val:
                                summary["해외겸용_프리미엄"] = for_val
                            if dom_val and not for_val:
                                summary["해외겸용_프리미엄"] = dom_val
                            if for_val and not dom_val:
                                summary["국내전용_프리미엄"] = for_val
                        else:
                            합계_val = vals[합계_idx] if 합계_idx >= 0 and 합계_idx < len(vals) else ""
                            if not 합계_val:
                                합계_val = next((v for v in reversed(vals) if v and re.search(r"\d", v)), "")
                            if 합계_val:
                                summary["국내전용_프리미엄"] = 합계_val
                                summary["해외겸용_프리미엄"] = 합계_val

                if is_모바일행 and vals:
                    mob_dom, mob_for = "", ""
                    for i, col_name in enumerate(col_headers):
                        if i >= len(vals) or not vals[i]: continue
                        col_upper = col_name.upper()
                        if "국내전용" in col_name or ("LOCAL" in col_upper and "VISA" not in col_upper):
                            mob_dom = vals[i]
                        elif any(b in col_upper for b in ("VISA", "MASTER", "UNIONPAY")) or "해외겸용" in col_name or "국내외겸용" in col_name:
                            mob_for = vals[i]
                    if not mob_dom and not mob_for and vals:
                        # col_headers 분리 불가 → 순서대로 할당
                        mob_dom = vals[0] if len(vals) > 0 else ""
                        mob_for = vals[1] if len(vals) > 1 else ""
                    parts = []
                    if mob_dom:
                        parts.append(f"모바일(국내): {int(mob_dom):,}원")
                    if mob_for:
                        parts.append(f"모바일(해외): {int(mob_for):,}원")
                    if parts:
                        existing = summary.get("연회비_비고", "")
                        note = " / ".join(parts)
                        summary["연회비_비고"] = f"{existing} / {note}".strip(" /") if existing else note

                # 기존 "총 연회비" 레이블 방식도 유지 (다른 카드 호환)
                if "총 연회비" in row_label:
                    if is_본인:
                        for i, col_name in enumerate(col_headers):
                            if i >= len(vals) or not vals[i]: continue
                            if "국내전용" in col_name or "국내" in col_name:
                                summary["국내전용_일반"] = vals[i]
                            elif any(b in col_name for b in ("VISA","Master","UnionPay","해외겸용","해외")):
                                summary["해외겸용_일반"] = vals[i]
                        if not summary["국내전용_일반"] and not summary["해외겸용_일반"]:
                            if len(vals) >= 2:
                                summary["해외겸용_일반"] = vals[0]
                                summary["국내전용_일반"] = vals[1]
                            elif len(vals) == 1:
                                summary["국내전용_일반"] = summary["해외겸용_일반"] = vals[0]
                    elif is_가족:
                        for i, col_name in enumerate(col_headers):
                            if i >= len(vals) or not vals[i]: continue
                            if "국내전용" in col_name or "국내" in col_name:
                                summary["국내전용_프리미엄"] = vals[i]
                            elif any(b in col_name for b in ("VISA","Master","UnionPay","해외겸용","해외")):
                                summary["해외겸용_프리미엄"] = vals[i]
                        if not summary["국내전용_프리미엄"] and not summary["해외겸용_프리미엄"]:
                            if len(vals) >= 2:
                                summary["해외겸용_프리미엄"] = vals[0]
                                summary["국내전용_프리미엄"] = vals[1]
                            elif len(vals) == 1:
                                summary["국내전용_프리미엄"] = summary["해외겸용_프리미엄"] = vals[0]

    if brands:
        summary["결제네트워크브랜드"] = ", ".join(brands)

    return summary, detail_rows

def parse_notices(soup) -> list:
    """card_notices.csv 전용. div.txtBox1_hide(이용전확인사항)와 div.txtBox1_bdr(법적고지)에서 수집."""
    rows = []
    seen: set[str] = set()

    LEGAL_KW = (
        "개인신용평점", "원리금", "상환능력", "신용카드 사용액",
        "금융거래 관련", "연체할 경우", "변제할 의무",
    )
    RATE_KW = ("연체이자율", "연체이자", "정상이자율", "이자율", "할부수수료율")

    def classify_text(txt: str, current_sub: str) -> str:
        if any(k in txt for k in LEGAL_KW):
            return "법적고지"
        if any(k in txt for k in RATE_KW) or any(k in current_sub for k in RATE_KW):
            return "연체이자율"
        return "이용전확인사항"

    def add_row(분류, sub, txt):
        txt = txt.strip()
        if txt and len(txt) > 3 and txt not in seen:
            seen.add(txt)
            resolved_sub = "법적고지" if 분류 == "법적고지" else sub
            rows.append((분류, resolved_sub, txt))

    _SUB_NORMALIZE = {
        "이용 전 확인사항": "이용전확인사항",
        "이용전 확인사항":  "이용전확인사항",
        "이용전확인 사항":  "이용전확인사항",
        "이용 전확인사항":  "이용전확인사항",
    }
    _NOISE_CONTENT = re.compile(
        r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}|^https?://|^www\."
    )

    def walk_notices(container, force_분류: str = "", force_sub: str = ""):
        """h태그(소제목)와 li/p(내용)를 순서대로 수집."""
        from bs4 import BeautifulSoup as BS
        current_sub = force_sub if force_sub else "이용전확인사항"
        is_hide_mode = (force_분류 == "__hide__")

        # 소제목처럼 보이는 짧은 명사구 패턴 (서술어 없음)
        _HEADING_LIKE = re.compile(
            r"^(무승인|구매|할인|적립|연체이자율|카드발급|이용실적\s*(기준|제외\s*대상)|"
            r"할인서비스\s*제공|일부\s*상품만\s*발급\s*가능|T&E\s*업종|"
            r"신용\s*결제\s*이용|단기카드대출.*이용|해외\s*이용\s*시\s*청구금액|"
            r"\[.*?\])\s*$"
        )

        def resolve_분류(txt, sub):
            if is_hide_mode:
                if any(k in txt for k in RATE_KW) or any(k in sub for k in RATE_KW):
                    return "연체이자율"
                return "이용전확인사항"
            if force_분류:
                return force_분류
            return classify_text(txt, sub)

        # 이미 처리된 element 추적 (descendants 순회 중 중복 방지)
        processed = set()

        for el in container.descendants:
            if not hasattr(el, "name") or not el.name:
                continue
            if id(el) in processed:
                continue

            if el.name in ("h2", "h3", "h4", "h5", "h6"):
                txt = clean(el.get_text())
                if txt:
                    current_sub = _SUB_NORMALIZE.get(txt, txt)
                continue

            if el.name == "strong":
                if el.find_parent("li") or el.find_parent("p"):
                    continue
                txt = clean(el.get_text())
                if txt and len(txt) <= 40 and not el.find(["ul", "ol", "li"]):
                    current_sub = _SUB_NORMALIZE.get(txt, txt)
                continue

            # 테이블 → 행/셀을 합쳐서 의미있는 텍스트면 한 행으로 저장
            if el.name == "table":
                # 이미 부모 table에서 처리된 경우 스킵
                if el.find_parent("table"):
                    continue
                rows_text = []
                for tr in el.find_all("tr"):
                    cells = [clean(td.get_text()) for td in tr.find_all(["th", "td"]) if clean(td.get_text())]
                    if cells:
                        rows_text.append(" : ".join(cells))
                for td_el in el.descendants:
                    if hasattr(td_el, "name"):
                        processed.add(id(td_el))
                combined = " / ".join(rows_text)
                if combined and len(combined) > 10 and not _NOISE_CONTENT.search(combined):
                    add_row(resolve_분류(combined, current_sub), current_sub, combined)
                continue

            if el.name == "li":
                if el.find_parent("li"):
                    continue
                li_copy = BS(str(el), "html.parser").find("li")

                # <p>, <strong> 내부 텍스트 먼저 수집
                for sub_el in li_copy.find_all(["p", "strong"]):
                    sub_txt = clean(sub_el.get_text())
                    if not sub_txt or len(sub_txt) <= 3:
                        continue
                    if _NOISE_CONTENT.search(sub_txt):
                        continue
                    # 소제목처럼 보이는 짧은 텍스트는 저장 안 함
                    if _HEADING_LIKE.match(sub_txt):
                        continue
                    add_row(resolve_분류(sub_txt, current_sub), current_sub, sub_txt)

                # 내부 태그 제거 후 나머지 텍스트
                for nested in li_copy.find_all(["ul", "ol", "p", "strong"]):
                    nested.decompose()
                txt = clean(li_copy.get_text())
                if not txt or len(txt) <= 3 or _NOISE_CONTENT.search(txt):
                    continue
                if _HEADING_LIKE.match(txt):
                    continue
                add_row(resolve_분류(txt, current_sub), current_sub, txt)
                continue

            if el.name == "p":
                if el.find_parent("li"):
                    continue
                txt = clean(el.get_text())
                if not txt or len(txt) <= 3 or _NOISE_CONTENT.search(txt):
                    continue
                if _HEADING_LIKE.match(txt):
                    continue
                add_row(resolve_분류(txt, current_sub), current_sub, txt)

    RATE_KW_SET = set(RATE_KW)

    def force_분류_hide(txt, sub):
        if any(k in txt for k in RATE_KW_SET) or any(k in sub for k in RATE_KW_SET):
            return "연체이자율"
        return "이용전확인사항"

    box_hide = soup.find("div", class_="txtBox1_hide")
    if box_hide:
        walk_notices(box_hide, force_분류="__hide__")

    box_bdr = None
    if box_hide:
        box_bdr = box_hide.find_next_sibling("div", class_="txtBox1_bdr")
    if not box_bdr:
        box_bdr = soup.find("div", class_="txtBox1_bdr")
    if box_bdr:
        walk_notices(box_bdr, force_분류="법적고지", force_sub="법적고지")

    return rows
_OVERSEAS_FEE_RE = re.compile(
    r"(국제브랜드\s*수수료|브랜드\s*수수료)\s*([\d.]+)%\s*면제"
    r"[,\s]+"
    r"(해외\s*서비스\s*수수료|서비스\s*수수료)\s*([\d.]+)%\s*면제",
    re.IGNORECASE,
)
_OVERSEAS_FEE_PLUS_RE = re.compile(
    r"(국제브랜드\s*수수료|브랜드\s*수수료)\s*([\d.]+)%"
    r"\s*\+\s*"
    r"(해외\s*서비스\s*수수료|서비스\s*수수료)\s*([\d.]+)%\s*\|?\s*면제",
    re.IGNORECASE,
)

_GROUP_LABEL_PREFIX = re.compile(
    r"^(국내\s*혜택|해외\s*혜택|Global\s*혜택|일상\s*혜택|KB\s*Pay\s*혜택)\s*"
)
_PURE_GROUP_LABEL = re.compile(
    r"^(국내\s*혜택|해외\s*혜택|Global\s*혜택|일상\s*혜택|KB\s*Pay\s*혜택)$"
)
_COND_ONLY_RE = re.compile(
    r"^(최초\s*발급|실적유예|유예기간|전월\s*이용실적이?\s*[\d,만천]+원\s*(이상|미만)(?!.*할인한도))",
    re.IGNORECASE,
)


def _split_overseas_fee(content: str, base_row: dict) -> list | None:
    """해외수수료 2종 합산 content를 2행으로 분리. 해당 없으면 None 반환."""
    for pat in (_OVERSEAS_FEE_RE, _OVERSEAS_FEE_PLUS_RE):
        m = pat.search(content)
        if m:
            r1 = dict(base_row)
            r1["value"] = m.group(2)
            r1["unit"] = "%"
            r1["benefit_type"] = "서비스"
            r1["benefit_content"] = f"국제브랜드수수료 {m.group(2)}% 면제"
            r1["benefit_summary"] = f"국제브랜드수수료 {m.group(2)}% 면제"

            r2 = dict(base_row)
            r2["benefit_id"] = str(base_row.get("benefit_id", "")) + "_2"
            r2["value"] = m.group(4)
            r2["unit"] = "%"
            r2["benefit_type"] = "서비스"
            r2["benefit_content"] = f"해외서비스수수료 {m.group(4)}% 면제"
            r2["benefit_summary"] = f"해외서비스수수료 {m.group(4)}% 면제"
            return [r1, r2]
    return None


def _postprocess_benefit_rows(rows: list) -> list:
    """
    1) 해외수수료 2종 합산 행 → 2행 분리 (X% 면제/X% + Y% 면제 두 패턴 모두 처리)
    2) benefit_summary/benefit_title의 '국내 혜택'/'해외 혜택' 그룹 접두사 제거
    3) benefit_summary가 순수 그룹명이면 공란
    4) benefit_content '/' 다중절 → value 없는 행의 첫 절만 유지
    5) 전월실적 조건 설명문 → value/unit/benefit_type 강제 정리
    6) 복합 혜택(% 2개 이상) → value/unit 공란
    """
    # 심의필 행 필터링 패턴
    _SHIMUI_RE = re.compile(r"여신금융협회\s*심의필|심의필\s*제\d+")

    # benefit_title이 뭉뚱그려진 경우 content에서 소제목 추출
    # "교육 관련 업종* | 5% | 전월실적: 400000 | 월한도: 1만원" → "교육 관련 업종*"
    def _extract_title_from_content(content: str, perf: str) -> str:
        """파이프 구분 content의 첫 절을 소제목으로 사용. 전월실적 구간 있으면 붙임."""
        if "|" not in content:
            return ""
        first = content.split("|")[0].strip()
        # 수치만 있는 경우(예: "5%") 제외
        if re.match(r"^[\d.]+\s*[%원]?$", first):
            return ""
        # 전월실적 구간 붙이기
        if perf and perf.strip():
            try:
                perf_int = int(float(perf))
                if perf_int >= 10000:
                    perf_label = f"{perf_int//10000}만원"
                    return f"{first} ({perf_label} 이상)"
            except ValueError:
                pass
        return first

    result = []
    for r in rows:
        content = str(r.get("benefit_content", "") or "")
        summary = str(r.get("benefit_summary", "") or "")

        # 심의필/여신금융협회 행 → 혜택이 아니라 법적고지, 필터링
        if _SHIMUI_RE.search(content):
            continue

        split = _split_overseas_fee(content, r)
        if split:
            result.extend(split)
            continue

        if _GROUP_LABEL_PREFIX.match(summary):
            r = dict(r)
            r["benefit_summary"] = _GROUP_LABEL_PREFIX.sub("", summary).strip()
            summary = r["benefit_summary"]

        if _GROUP_LABEL_PREFIX.match(content):
            r = dict(r)
            r["benefit_content"] = _GROUP_LABEL_PREFIX.sub("", content).strip()
            content = r["benefit_content"]

        if _PURE_GROUP_LABEL.match(summary):
            r = dict(r)
            r["benefit_summary"] = ""
            summary = ""

        # benefit_title이 뭉뚱그려진 경우(상세혜택, 서비스 요약 등) content에서 개선
        title = str(r.get("benefit_title", "") or "")
        if title in ("상세혜택", "서비스 요약") and "|" in content:
            improved = _extract_title_from_content(content, str(r.get("performance_level", "") or ""))
            if improved:
                r = dict(r)
                r["benefit_title"] = improved[:80]

        if "/" in content and not r.get("value"):
            r = dict(r)
            r["benefit_content"] = content.split("/")[0].strip()
            content = r["benefit_content"]

        if _COND_ONLY_RE.search(content):
            r = dict(r)
            r["value"] = ""
            r["unit"] = ""
            r["benefit_type"] = "서비스"

        content_now = str(r.get("benefit_content", "") or "")
        summary_now = str(r.get("benefit_summary", "") or "")
        if (len(re.findall(r"\d+(?:\.\d+)?%", content_now)) >= 2 or
                len(re.findall(r"\d+(?:\.\d+)?%", summary_now)) >= 2):
            r = dict(r)
            r["value"] = ""
            r["unit"] = ""

        result.append(r)
    return result

_benefit_id_counter = 0
_notice_id_counter  = 0
