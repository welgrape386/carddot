"""
classifier.py - KB국민카드 혜택 텍스트 분류 유틸
  - 카테고리 / 혜택유형 / 가맹점 필터링 / 수치 추출
"""

import re
import json
import urllib.request
from config import CATEGORY_DATA, ON_OFF_MAP, LOCATION_MAP, ANTHROPIC_API_KEY


# ── 카테고리명 → ID 매핑 ──────────────────────────────────────

CATEGORY_ID_MAP: dict[str, int] = {
    item["category_name"]: item["category_id"]
    for item in CATEGORY_DATA
}

# ── 카테고리 분류 (키워드 매핑) ──────────────────────────────

CATEGORY_MAP = [
    ("해외", [
        "해외", "해외 가맹점", "해외이용", "해외겸용", "해외 이용",
        "해외서비스 수수료", "국제브랜드 수수료", "국제브랜드", "환율",
    ]),
    ("교육/육아", [
        "교육", "학원", "서점", "육아", "학교납입금", "초·중·고",
        "대학등록금", "등록금", "유아", "어린이", "학습", "문화센터", "학습지",
    ]),
    ("의료", [
        "의료", "병원", "약국", "한의원", "치과", "한방", "건강",
        "일상케어",
    ]),
    ("구독/스트리밍", [
        "구독", "스트리밍", "넷플릭스", "웨이브", "티빙", "왓챠", "디즈니플러스",
        "유튜브 프리미엄", "유튜브프리미엄", "멜론", "FLO", "OTT", "쇼핑 멤버십",
        "쿠팡 로켓와우", "네이버플러스 멤버십", "로켓와우 멤버십",
        "구글플레이스토어", "앱스토어", "App Store", "Google Play", "모바일",
    ]),
    ("자동차/주유", [
        "주유", "자동차", "정비", "하이패스", "고속도로", "주차",
        "GS칼텍스", "SK에너지", "S-OIL", "현대오일뱅크", "오토",
    ]),
    ("배달", [
        "배달", "배달의민족", "배민", "요기요", "쿠팡이츠", "땡겨요",
    ]),
    ("온라인쇼핑", [
        "온라인쇼핑", "지마켓", "11번가", "옥션", "위메프", "티몬",
        "롯데온", "SSG", "온라인 쇼핑", "온라인장보기",
    ]),
    ("패션/뷰티", [
        "패션", "뷰티", "올리브영", "무신사", "H&M", "자라", "유니클로",
        "스파브랜드", "스파 브랜드", "화장품", "미용",
        "취미/자기관리",
    ]),
    ("슈퍼마켓/생활잡화", [
        "마트", "슈퍼마켓", "이마트", "홈플러스", "롯데마트", "코스트코",
        "생활잡화", "다이소",
    ]),
    ("백화점/아울렛/면세점", [
        "백화점", "아울렛", "면세점", "롯데백화점", "현대백화점", "신세계", "갤러리아",
    ]),
    ("대중교통/택시", [
        "대중교통", "교통", "버스", "지하철", "택시", "기차", "KTX", "SRT",
        "철도", "T-money", "티머니", "후불교통",
    ]),
    ("반려동물", [
        "반려동물", "펫", "동물병원", "반려",
    ]),
    ("레저/스포츠", [
        "레저", "스포츠", "골프", "게임", "피트니스", "헬스", "경기관람",
        "워터파크", "테마파크", "스키",
    ]),
    ("페이/간편결제", [
        "간편결제", "KB Pay", "삼성페이", "네이버페이", "카카오페이",
        "PAYCO", "페이코", "토스페이",
    ]),
    ("문화/엔터", [
        "영화", "놀이공원", "공연", "CGV", "메가박스", "롯데시네마",
        "문화", "엔터", "뮤지컬", "전시",
        "인터파크 티켓", "인터파크티켓",
        "에버랜드", "롯데월드",
    ]),
    ("생활비", [
        "이동통신", "통신", "SKT", "KT", "LG U+", "LG U＋", "알뜰폰", "Liiv M",
        "보험", "생명보험", "손해보험",
        "공과금", "전기요금", "가스요금", "수도요금", "4대 사회보험",
        "국민연금", "건강보험", "4대보험", "도시가스",
        "금융수수료", "이자", "금융",
        "렌탈", "자동납부", "정기결제", "자동이체",
        "생활요금", "생활대금", "생활",
        "아파트관리비", "관리비",
        "통신/보험", "보험료",
        "전월실적 채워드림",
        "월간 통합할인한도", "통합할인한도",
    ]),
    ("편의점", [
        "편의점", "GS25", "CU", "세븐일레븐", "미니스톱", "이마트24",
    ]),
    ("커피/카페/베이커리", [
        "커피", "카페", "베이커리", "스타벅스", "이디야", "커피빈", "투썸",
        "메가커피", "빽다방", "파리바게뜨", "뚜레쥬르", "카페베네",
        "제과", "디저트", "빵집", "아이스크림",
    ]),
    ("외식", [
        "외식", "음식점", "레스토랑", "식당", "맥도날드", "버거킹", "KFC",
        "롯데리아", "아웃백", "빕스", "패밀리레스토랑", "전국맛집", "맛집",
    ]),
    ("여행/숙박", [
        "여행", "숙박", "호텔", "렌터카", "야놀자", "여기어때", "에어비앤비",
        "모텔", "리조트", "펜션",
    ]),
    ("항공", [
        "항공", "대한항공", "아시아나", "공항라운지", "라운지", "마일리지",
        "제주항공", "진에어", "에어서울", "에어부산",
    ]),
]


def get_category(소분류: str, 내용: str) -> str:
    """소분류명 + 내용 텍스트로 카테고리 분류"""
    combined = f"{소분류} {내용}"
    for cat_name, keywords in CATEGORY_MAP:
        if any(kw in combined for kw in keywords):
            return cat_name
    return ""


def get_category_id(cat_name: str) -> str:
    """카테고리명 → ID 반환 (없으면 빈 문자열)"""
    return str(CATEGORY_ID_MAP.get(cat_name, "")) if cat_name else ""


# ── 혜택유형 분류 ─────────────────────────────────────────────

def classify_benefit_type(소분류: str, 내용: str, 단위: str) -> str:
    combined = f"{소분류} {내용}"
    if "캐시백" in combined or "cashback" in combined.lower():
        return "캐시백"
    if "마일리지" in combined:
        return "마일리지"
    if "포인트" in combined:
        return "포인트적립"
    if 단위 == "%" or "할인" in combined:
        return "할인"
    if "무료" in combined or "면제" in combined or "서비스" in combined:
        return "서비스"
    return ""


# ── 가맹점 필터링 (화이트리스트) ─────────────────────────────

_KNOWN_BRANDS: set[str] = {
    "스타벅스", "이디야", "커피빈", "투썸플레이스", "메가커피", "빽다방",
    "할리스", "카페베네", "탐앤탐스", "폴바셋",
    "파리바게뜨", "뚜레쥬르", "브레댄코", "던킨",
    "배달의민족", "배달의 민족", "배민", "요기요", "쿠팡이츠", "땡겨요",
    "GS25", "CU", "세븐일레븐", "미니스톱", "이마트24",
    "쿠팡", "네이버플러스스토어", "네이버쇼핑", "지마켓", "11번가", "옥션",
    "위메프", "티몬", "인터파크", "인터파크 티켓", "롯데온", "SSG", "오아시스마켓", "마켓컬리",
    "넷플릭스", "웨이브", "티빙", "왓챠", "디즈니플러스", "디즈니+",
    "유튜브 프리미엄", "유튜브프리미엄", "멜론", "FLO", "지니뮤직", "시즌",
    "쿠팡 로켓와우", "네이버플러스 멤버십",
    "SKT", "KT", "LG U+", "LG U＋", "LG U", "Liiv M", "알뜰폰",
    "구글 플레이", "구글플레이스토어", "앱스토어", "App Store", "Google Play",
    "이마트", "홈플러스", "롯데마트", "코스트코", "트레이더스 홀세일 클럽",
    "올리브영", "무신사", "H&M", "자라", "유니클로",
    "CGV", "메가박스", "롯데시네마",
    "에버랜드", "롯데월드",
    "야놀자", "여기어때", "에어비앤비", "호텔스닷컴",
    "대한항공", "아시아나", "제주항공", "진에어", "에어서울",
    "맥도날드", "버거킹", "KFC", "롯데리아", "아웃백", "빕스", "맘스터치",
    "GS칼텍스", "SK에너지", "S-OIL", "현대오일뱅크",
    "다이소", "이케아",
}


def filter_brands(candidates: list) -> list:
    """가맹점 후보에서 알려진 브랜드명만 반환"""
    result = []
    seen: set = set()
    for raw in candidates:
        token = re.sub(r"\s+", " ", (raw or "").strip())
        if token and token in _KNOWN_BRANDS and token not in seen:
            result.append(token)
            seen.add(token)
    return result


# ── LLM 기반 브랜드 추출 + 카테고리 분류 ─────────────────────

def classify_merchants_with_llm(llm_input: str) -> dict:
    """Anthropic API를 통해 브랜드 추출 + 카테고리 분류"""
    VALID_CATEGORIES = [item["category_name"] for item in CATEGORY_DATA]

    empty = {}
    if not ANTHROPIC_API_KEY:
        return empty

    prompt = f"""다음은 카드 혜택 텍스트 목록입니다. 각 항목에서 실제 브랜드명과 카테고리를 추출하세요.

혜택 텍스트:
{llm_input}

각 항목(번호: 텍스트)에 대해 아래 JSON 형식으로 반환하세요.
유효한 카테고리: {', '.join(VALID_CATEGORIES)}

{{
  "0": {{"brands": ["브랜드A", "브랜드B"], "category": "카테고리명"}},
  "1": {{"brands": [], "category": "카테고리명"}},
  ...
}}

규칙:
- brands: 실제 가맹점/브랜드명만 포함 (업종명, 설명문 제외)
- category: 위 유효한 카테고리 중 하나만 사용, 해당 없으면 빈 문자열
- JSON만 반환, 설명 없음"""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
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


# ── 수치 추출 유틸 ────────────────────────────────────────────

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
    """건당 최소 결제금액 조건 추출 (전월실적 조건은 제외)"""
    if not content:
        return ""
    content_clean = re.sub(r"전월\s*이용실적[^\s]*\s*[\d,만천백]+원\s*이상", "", content)
    m = re.search(
        r"(?:건당\s*)?([\d,만천백]+)원\s*이상\s*(?:결제\s*)?시",
        content_clean
    )
    if m:
        return extract_number(m.group(1) + "원")
    return ""


def extract_max_count(content: str) -> str:
    """월 최대 횟수 추출"""
    if not content:
        return ""
    m = re.search(r"월\s*(\d+)\s*회", content)
    if m:
        return m.group(1)
    m = re.search(r"(\d+)회\s*/\s*[\d,만천백]+원", content)
    if m:
        return m.group(1)
    m = re.search(r"월한도\s*[:|]\s*월?\s*(\d+)\s*회", content)
    if m:
        return m.group(1)
    return ""


def extract_max_limit(content: str) -> str:
    """월 최대 한도 금액 추출"""
    if not content:
        return ""
    # 괄호 안 패턴: (월 N천원 이내)
    m_paren = re.search(r'\(월?\s*([^)]+)\)', content)
    m_slash = re.search(r'/\s*(.+)', content)
    text = content

    if m_paren:
        text = m_paren.group(1).strip()
    elif m_slash and re.search(r'\d+\s*회', content.split('/')[0]):
        text = m_slash.group(1).strip()

    # 회수·건당·% → 빈값
    if re.search(r'\d+\s*회|연\s*\d+|건당|%', text) and \
       not re.search(r'\d+[만천]원|\d{1,3},\d{3}원|\d+원', text):
        return ""

    # 한도 패턴: 월 N만원 / 할인한도: N천원
    m = re.search(r"(?:월\s*)?(?:할인한도|한도)\s*[:|]\s*월?\s*([\d,만천백]+)원", content)
    if m:
        return extract_number(m.group(1) + "원")

    total = 0
    for val, unit in re.findall(r"(\d+)(만|천)", text):
        total += int(val) * 10000 if unit == "만" else int(val) * 1000
    if total:
        return str(total)
    m = re.search(r"[\d,]+", text)
    return m.group(0).replace(",", "") if m else ""
