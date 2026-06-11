import os, re, csv, json, sys
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(override=True)

# ─────────────────────────────────────────────
# 경로 설정 (__file__ 기준)
# ─────────────────────────────────────────────
_BASE_DIR    = os.path.dirname(os.path.abspath(__file__))   # scheduler/kb/

CARDS_JSON   = os.path.join(_BASE_DIR, "claud", "최종본", "kb_cards.json")
HTML_OUT_DIR = os.path.join(_BASE_DIR, "kb_html")
OUTPUT_DIR   = os.path.join(_BASE_DIR, "output")

MODEL      = "claude-haiku-4-5-20251001"
MAX_TOKENS = 8192
COMPANY    = "국민"

# ─────────────────────────────────────────────
# CSV 컬럼 정의
# ─────────────────────────────────────────────
INFO_FIELDS = [
    "card_id", "company", "card_name", "card_type", "network",
    "is_domestic_foreign", "has_transport",
    "annual_fee_dom_basic", "annual_fee_dom_premium",
    "annual_fee_for_basic", "annual_fee_for_premium",
    "annual_fee_notes", "min_performance",
    "summary", "image_url", "link_url", "has_cashback",
    "fee_content", "updated_at",
]

BENEFIT_FIELDS = [
    "benefit_id", "card_id", "row_type",
    "benefit_group", "benefit_title",
    "category", "category_id", "on_offline",
    "benefit_type", "benefit_value", "benefit_unit",
    "target_merchants",
    "performance_level", "performance_min", "performance_max",
    "min_amount", "max_count", "max_limit", "max_limit_unit",
    "group_max_limit", "group_max_limit_unit",
    "unit_amount",
    "benefit_content", "ui_title", "ui_content",
    "updated_at",
]

NOTICE_FIELDS = ["notice_id", "card_id", "notice_content", "updated_at"]

CATEGORY_ID_MAP = {
    "온라인쇼핑": 1, "패션/뷰티": 2, "슈퍼마켓/생활잡화": 3,
    "백화점/아울렛/면세점": 4, "대중교통/택시": 5, "자동차/주유": 6,
    "반려동물": 7, "구독/스트리밍": 8, "레저/스포츠": 9,
    "페이/간편결제": 10, "문화/엔터": 11, "생활비": 12,
    "편의점": 13, "카페/베이커리": 14, "배달": 15,
    "외식": 16, "여행/숙박": 17, "항공": 18,
    "해외": 19, "교육/육아": 20, "의료": 21, "기타": 22,
}

# 순서 중요: 위에서부터 우선 적용
CATEGORY_KEYWORD_MAP = [
    ("페이/간편결제",     ["KB Pay", "KB페이", "카카오페이", "네이버페이", "삼성페이", "간편결제"]),
    ("대중교통/택시",     ["시내버스", "지하철", "고속버스", "시외버스", "후불교통", "대중교통", "카카오택시", "택시"]),
    ("카페/베이커리",     ["스타벅스", "투썸", "이디야", "커피", "카페", "베이커리", "파리바게뜨", "뚜레쥬르", "제과", "아이스크림"]),
    ("편의점",            ["GS25", "CU", "세븐일레븐", "이마트24", "편의점"]),
    ("배달",              ["배달의민족", "배민", "요기요", "쿠팡이츠", "마켓컬리", "배달앱"]),
    ("외식",              ["음식점", "외식", "패밀리레스토랑", "아웃백", "VIPS", "일반음식점", "뷔페", "F&B", "홈구장", "홈구장 내", "패스트푸드", "맥도날드", "버거킹", "롯데리아"]),
    ("구독/스트리밍",     ["넷플릭스", "유튜브 프리미엄", "웨이브", "티빙", "디즈니", "OTT", "왓챠", "스포티파이"]),
    ("온라인쇼핑",        ["쿠팡", "네이버쇼핑", "11번가", "G마켓", "옥션", "SSG", "온라인쇼핑"]),
    ("문화/엔터",         ["CGV", "롯데시네마", "메가박스", "영화", "인터파크"]),
    ("레저/스포츠",       ["에버랜드", "롯데월드", "놀이공원", "골프", "헬스장", "스포츠센터", "수영장", "볼링", "스키장", "테니스", "스포츠"]),
    ("패션/뷰티",         ["올리브영", "무신사", "패션", "뷰티", "화장품", "미용실"]),
    ("생활비",            ["이동통신", "SKT", "KT", "LGU+", "Liiv M", "통신요금", "인터넷", "타행이체", "자동화기기", "코웨이", "렌탈료", "관리비", "아파트", "건강보험"]),
    ("교육/육아",         ["교육", "서점", "도서", "학원", "온라인서점", "교보문고", "YES24", "웅진씽크빅", "비상교육", "비상온리원", "밀크T"]),
    ("의료",              ["병원", "약국", "한의원", "치과", "의료"]),
    ("해외",              ["해외가맹점", "해외 가맹점", "해외결제", "해외 결제", "해외 이용"]),
    ("항공",              ["항공", "공항", "마일리지", "대한항공", "아시아나", "제주항공"]),
    ("여행/숙박",         ["호텔", "숙박", "야놀자", "여기어때", "여행"]),
    ("자동차/주유",       ["주유", "GS칼텍스", "SK에너지", "현대오일뱅크", "셀프세차", "자동차", "주차장", "세차장", "손해보험", "자동차보험료", "차량보험"]),
    ("슈퍼마켓/생활잡화", ["이마트", "홈플러스", "롯데마트", "코스트코", "대형마트"]),
    ("백화점/아울렛/면세점", ["백화점", "아울렛", "면세점", "현대백화점", "롯데백화점", "신세계"]),
    ("반려동물",          ["반려동물", "펫", "동물병원"]),
]

# 한국식+서양식 금액 패턴 (1만원, 3천원, 1만5천원, 5,000원 등)
_KR_AMOUNT_RE = re.compile(r'\d[\d,]*\s*원|\d+만\s*\d*천?\s*원|\d+천\s*원')

# ─────────────────────────────────────────────
# 스킵 패턴
# ─────────────────────────────────────────────
SKIP_BOX_PATTERNS = [
    r"할인\(적립\)\s*서비스\s*제외매출",
    r"할인\(적립\)\s*서비스\s*적용",
    r"이용\s*실적\s*기준",
    r"전월\s*실적\s*제외",
    r"적립제외\s*대상",
    r"연체이자율",
    r"연회비\s*반환",
    r"상품설명서\s*보기",
    r"상품관련\s*서비스",
    r"서비스\s*요약",
    r"서비스\s*한눈에\s*보기",
    r"적립\s*서비스\s*제외\s*대상",
    r"캐시\s*안내",
    r"CU.*포인트.*적립|포인트.*적립.*CU",
    r"모바일\s*단독카드",
    r"해외이용\s*TIP|해외\s*이용\s*TIP",
    r"^연회비",
    r"^할인한도",
    r"^확인사항",
    r"^이용\s*전\s*확인사항",
    r"^$",
]

CONTENT_SKIP_PATTERNS = [
    re.compile(r'최초\s*발급\s*후.*통합할인한도'),
    re.compile(r'사용\s*등록일.*통합할인한도'),
    re.compile(r'동일\s*계열\s*카드.*사용\s*등록일'),
]

PERF_SKIP_PATTERNS = [
    re.compile(r'이용\s*실적이?\s*없는\s*경우에도'),
    re.compile(r'실적에\s*관계없이'),
    re.compile(r'최초\s*카드?\s*사용\s*등록일.*할인'),
    re.compile(r'최초\s*사용\s*등록일로부터.*일간'),
    re.compile(r'실적\s*유예기간.*할인'),
    re.compile(r'유예기간\s*중.*실적'),
    re.compile(r'제공조건\s*[:：].*전월\s*이용실적.*최초'),
    re.compile(r'실적\s*유예기간.*전월\s*이용실적'),
    re.compile(r'다음\s*달?\s*말일.*실적\s*유예기간'),
    re.compile(r'최초\s*카드?\s*사용\s*등록일로부터.*다음\s*달?\s*말일'),
]

SKIP_LINE_PATTERNS = CONTENT_SKIP_PATTERNS + PERF_SKIP_PATTERNS

NOTICE_BOX_PATTERNS = [
    r"서비스\s*요약",
    r"포인트리\s*안내",
]

# ─────────────────────────────────────────────
# Claude API
# ─────────────────────────────────────────────
_client = None

def get_client():
    global _client
    if _client is None:
        api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
        _client = anthropic.Anthropic(api_key=api_key)
    return _client

_token_usage = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0, "calls": 0}

def call_claude(system: str, user: str, max_tokens: int = MAX_TOKENS) -> str:
    for attempt in range(3):
        resp = get_client().messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text.strip()
        _token_usage["input"]       += resp.usage.input_tokens
        _token_usage["output"]      += resp.usage.output_tokens
        _token_usage["cache_write"] += getattr(resp.usage, "cache_creation_input_tokens", 0)
        _token_usage["cache_read"]  += getattr(resp.usage, "cache_read_input_tokens", 0)
        _token_usage["calls"]       += 1
        if resp.stop_reason == "max_tokens":
            max_tokens = min(max_tokens * 2, 16000)
            continue
        return text
    return text

def print_token_summary():
    i  = _token_usage["input"]
    o  = _token_usage["output"]
    cw = _token_usage["cache_write"]
    cr = _token_usage["cache_read"]
    c  = _token_usage["calls"]
    cost = (i * 0.0000008) + (o * 0.000004) + (cw * 0.000001) + (cr * 0.00000008)
    cache_info = f" | 캐시쓰기 {cw:,} / 캐시읽기 {cr:,}" if (cw + cr) else ""
    print(f"  [TOK] {c}회 | 입력 {i:,} / 출력 {o:,}{cache_info} | ${cost:.4f} ({cost*1400:.1f}원)")

def reset_token_usage():
    for k in _token_usage:
        _token_usage[k] = 0

def parse_json_response(text: str) -> list:
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    for fn in [
        lambda t: json.loads(t),
        lambda t: json.loads(re.search(r"\[.*\]", t, re.DOTALL).group(0)),
        lambda t: json.loads(re.search(r"\{.*\}", t, re.DOTALL).group(0)),
    ]:
        try:
            r = fn(text)
            return r if isinstance(r, list) else [r]
        except:
            pass
    raise ValueError(f"JSON 파싱 실패: {text[:200]}")

# ─────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────
def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def now_date():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def upsert_csv(filepath, new_rows, fieldnames, key_col="card_id"):
    for r in new_rows:
        if key_col == "card_id" and r.get("card_id"):
            r["card_id"] = str(r["card_id"]).zfill(5)

    valid_rows = []
    for r in new_rows:
        non_key_vals = [v for k, v in r.items() if k != key_col and str(v).strip()]
        if non_key_vals:
            valid_rows.append(r)
        else:
            print(f"  [SKIP] {filepath} — {r.get(key_col,'?')} 빈 데이터 저장 방지")
    if not valid_rows:
        return

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    existing = []
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8-sig") as f:
            existing = list(csv.DictReader(f))
    new_keys = {r[key_col] for r in valid_rows}

    def norm_key(r):
        v = r.get(key_col, "")
        return v.zfill(5) if key_col == "card_id" and v.isdigit() else v

    merged = [r for r in existing if norm_key(r) not in new_keys] + valid_rows
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(merged)
    print(f"  [SAVE] {filepath} -> {len(merged)}행")
