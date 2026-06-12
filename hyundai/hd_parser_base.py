import os
import csv
import json
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(override=True)

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
_BASE_DIR    = os.path.dirname(os.path.abspath(__file__))   # hd/parser/
_HD_DIR      = os.path.dirname(_BASE_DIR)                   # hd/

CARDS_JSON   = os.path.join(_HD_DIR, "hd_ouput", "최종본", "hd_cards.json")
HTML_OUT_DIR = os.path.join(_HD_DIR, "html")
OUTPUT_DIR   = os.path.join(_BASE_DIR, "output")

MODEL      = "claude-haiku-4-5-20251001"
MAX_TOKENS = 8192
COMPANY    = "현대"

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
    "fee_content",
    "updated_at",
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
    "benefit_content", "ui_title", "ui_content", "ui_table",
    "updated_at",
]

NOTICE_FIELDS = [
    "notice_id", "card_id",
    "notice_content", "updated_at",
]

# ─────────────────────────────────────────────
# 카테고리 ID 매핑
# ─────────────────────────────────────────────
CATEGORY_ID_MAP = {
    "온라인쇼핑": 1, "패션/뷰티": 2, "슈퍼마켓/생활잡화": 3,
    "백화점/아울렛/면세점": 4, "대중교통/택시": 5, "자동차/주유": 6,
    "반려동물": 7, "구독/스트리밍": 8, "레저/스포츠": 9,
    "페이/간편결제": 10, "문화/엔터": 11, "생활비": 12,
    "편의점": 13, "카페/베이커리": 14, "배달": 15,
    "외식": 16, "여행/숙박": 17, "항공": 18,
    "해외": 19, "교육/육아": 20, "의료": 21, "기타": 22,
}

CATEGORY_KEYWORD_MAP = [
    ("기타",              ["M 긴급적립", "긴급적립", "선지급 포인트", "세이브-오토",
                          "메탈 플레이트", "Metal", "플레이트 제공",
                          "Concierge", "컨시어지"]),
    ("페이/간편결제",     ["Apple Pay", "애플페이", "간편결제", "삼성페이", "카카오페이",
                          "네이버페이", "제로페이", "페이코"]),
    ("기타",              ["국내외 가맹점", "제휴사 마일리지", "H-Coin", "상품권 교환", "M포인트 교환"]),
    ("온라인쇼핑",        ["온라인 쇼핑몰", "네이버쇼핑", "쿠팡", "G마켓", "지마켓", "옥션",
                          "11번가", "SSG.COM", "컬리", "M몰", "롯데ON", "W컨셉", "KREAM",
                          "하이마트 온라인", "29CM", "LGE.COM", "CJ ONSTYLE", "Hmall", "hmall"]),
    ("패션/뷰티",         ["올리브영", "패션", "뷰티", "무신사", "더한섬닷컴", "H패션몰",
                          "MLB", "이랜드몰", "아모레몰", "이니스프리", "스파브랜드"]),
    ("슈퍼마켓/생활잡화", ["마트", "이마트", "홈플러스", "롯데마트", "GS THE FRESH",
                          "이마트 에브리데이", "노브랜드", "다이소", "트레이더스"]),
    ("백화점/아울렛/면세점", ["백화점", "아울렛", "면세점", "갤러리아", "신세계", "신라면세점",
                             "롯데면세점", "현대면세점", "더한섬닷컴", "신세계V"]),
    ("대중교통/택시",     ["버스", "지하철", "기차", "대중교통", "택시", "KTX", "SRT",
                          "카카오택시", "티머니", "후불교통",
                          "K-패스", "기후동행카드", "후불형 기후동행"]),
    ("자동차/주유",       ["주유", "자동차", "하이패스", "GS칼텍스", "SK에너지", "오일뱅크",
                          "현대자동차", "기아", "신차 구매", "블루핸즈", "타이어픽"]),
    ("반려동물",          ["반려동물", "펫프렌즈", "어바웃펫", "강아지대통령", "고양이대통령"]),
    ("구독/스트리밍",     ["구독", "스트리밍", "넷플릭스", "유튜브 프리미엄", "멜론",
                          "스포티파이", "웨이브", "왓챠", "티빙", "지니뮤직",
                          "Google One", "ChatGPT", "Perplexity", "디즈니+",
                          "AI 구독", "디지털 콘텐츠", "인앱 결제"]),
    ("레저/스포츠",       ["골프", "골프장", "티노파이브", "테일러메이드", "피트니스", "헬스장",
                          "필라테스", "요가", "테니스", "수영장", "레저", "스포츠",
                          "워터파크", "테마파크", "스키", "경기관람"]),
    ("문화/엔터",         ["영화", "놀이공원", "공연", "CGV", "메가박스", "롯데시네마",
                          "에버랜드", "롯데월드", "콘서트", "아쿠아플라넷"]),
    ("생활비",            ["통신", "SKT", "KT", "LG유플러스", "LGU+", "LG U+", "보험", "현대해상",
                          "공과금", "도시가스", "렌탈", "자동납부", "아파트 관리비", "ATM",
                          "이동통신", "통신 요금", "이동통신 요금"]),
    ("편의점",            ["편의점", "세븐일레븐", "GS25", "CU", "이마트24", "미니스톱"]),
    ("카페/베이커리",     ["커피전문점", "커피", "카페", "베이커리", "스타벅스", "투썸", "이디야",
                          "메가커피", "빽다방", "할리스", "파리바게뜨", "뚜레쥬르",
                          "배스킨라빈스", "공차", "던킨"]),
    ("배달",              ["배달", "배민", "배달의민족", "요기요", "쿠팡이츠", "땡겨요"]),
    ("외식",              ["패스트푸드", "외식", "일반음식점", "음식점", "아웃백", "레스토랑", "VIPS",
                          "도미노피자", "파파존스", "피자헛", "롯데리아", "쉐이크쉑",
                          "맥도날드", "버거킹", "KFC", "맘스터치"]),
    ("여행/숙박",         ["여행", "숙박", "호텔", "렌터카", "야놀자", "여기어때",
                          "에어비앤비", "카모아", "SK렌터카", "PRIVIA 여행", "KKday",
                          "그랜드 워커힐", "비스타 워커힐", "더 플라자", "워커힐 서울"]),
    ("항공",              ["공항라운지", "라운지", "항공", "대한항공", "아시아나",
                          "마일리지", "발레파킹", "인천국제공항", "에어프레미아"]),
    ("해외",              ["해외 가맹점", "해외이용", "해외결제", "외화", "해외직구",
                          "해외 온·오프라인"]),
    ("교육/육아",         ["학원", "서점", "육아", "교육", "유치원", "어린이집",
                          "교보문고", "야나두"]),
    ("의료",              ["병원", "약국", "의료", "치과", "한의원", "피부과"]),
    ("기타",              ["제휴사 마일리지", "H-Coin", "상품권 교환", "M포인트 교환"]),
]

# ─────────────────────────────────────────────
# 섹션 스킵 / 분류 패턴
# ─────────────────────────────────────────────
BOX_SKIP_FIRST = 5
BOX_SKIP_LAST  = 2

SKIP_TITLE_PATTERNS = [
    r"Visa/Amex\s*플래티넘서비스",
    r"카드\s*이용\s*유의사항",
    r"해외\s*결제\s*이용\s*안내",
    r"카드\s*디자인",
    r"앞면",
    r"뒷면",
    r"Metal",
    r"Header\s*타이틀",
    r"header\s*title",
    r"^혜택$",
]

NOTICE_TITLE_PATTERNS = [
    r"혜택\s*제공\s*기준",
    r"M포인트\s*사용\s*기준",
    r"이용\s*금액\s*산정",
]

SKIP_MODAL_PATTERNS = [
    r"연회비", r"Metal", r"Glossy", r"Header\s*타이틀", r"header\s*title",
    r"Visa/Amex\s*플래티넘서비스", r"Visa\s*플래티넘서비스",
    r"Visa\s*Infinite\s*서비스", r"Visa\s*Signature\s*서비스",
    r"카드\s*이용\s*유의사항",
    r"SNS", r"패밀리", r"로그아웃", r"전화상담", r"신청을\s*시작",
    r"카드\s*디자인", r"앞면", r"뒷면",
    r"카드\s*종류\s*선택",
    r"^부가서비스$",
    r"이용\s*관련\s*안내사항",
    r"Visa/Amex\s*플래티넘\s*서비스",
    r"^Z\s*work$",
    r"^Black\s*&\s*Black$",
    r"^Fluid$",
    r"^Solid$",
    r"쓱\s*망고",
]

NOTICE_ROW_MODAL_PATTERNS = [
    r"카드\s*신청을\s*위해\s*미리\s*준비",
    r"기본\s*및\s*추가\s*혜택은.*회원\s*대상",
    r"^SPECTRUM$",
    r"Visa\s*Signature\s*서비스",
    r"금융\s*교육\s*콘텐츠",
    r"^상품\s*안내$",
    r"멤버십\s*리워즈.*사용",
    r"Membership\s*Rewards.*사용",
]

MERGE_AS_ONE_PATTERNS = [
    r"^혁신금융서비스$",
    r"^바우처$",
    r"예스24\s*특화\s*혜택",
    r"블루멤버스\s*포인트\s*적립",
]

NOTICE_MODAL_GROUPS = [
    r"메탈\s*플레이트",
    r"체크카드\s*이용\s*안내",
    r"Z\s*family\s*메탈",
]

GROUP_BENEFIT_TYPE_MAP = {
    r"M포인트\s*사용처":           "서비스",
    r"M포인트\s*사용":             "서비스",
    r"M포인트\s*적립":             "포인트",
    r"멤버십\s*리워즈.*적립":      "포인트",
    r"멤버십\s*리워즈.*사용":      "포인트",
    r"Amex\s*PLATINUM.*서비스":    "서비스",
    r"Amex\s*THE\s*PLATINUM":      "서비스",
    r"블루멤버스\s*포인트\s*적립": "포인트",
    r"네이버페이\s*포인트\s*적립": "포인트",
    r"SSG\s*MONEY\s*적립":         "포인트",
    r"스마일캐시\s*적립":          "포인트",
    r"올리브영.*리워드":           "포인트",
    r"크레딧\s*적립":              "포인트",
    r"할인\s*서비스":                  "할인",
    r"기본\s*혜택\(항공\s*마일리지형\)": "마일리지",
    r"기본\s*혜택\(M포인트형\)":       "포인트",
    r"정부\s*지원\s*혜택":         "서비스",
    r"GENESIS\s*CARD":             "서비스",
    r"GS칼텍스\s*특화\s*혜택":     "할인",
    r"우대\s*서비스":              "서비스",
    r"메탈\s*플레이트":            "서비스",
    r"기본\s*혜택":                "할인",
}

USAGE_PLACE_TITLES = {
    "일상 사용처",
}


# ─────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────
def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def load_cards_json() -> list:
    if not os.path.exists(CARDS_JSON):
        return []
    with open(CARDS_JSON, encoding="utf-8") as f:
        return json.load(f)

def upsert_csv(filepath: str, new_rows: list, fieldnames: list, key_col: str = "card_id"):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    existing = []
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8-sig") as f:
            existing = list(csv.DictReader(f))
    new_keys = {r[key_col] for r in new_rows}
    merged   = [r for r in existing if r.get(key_col) not in new_keys] + new_rows
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged)
    print(f"  [저장] {filepath} -> {len(merged)}행")


def format_benefit_content(text: str) -> str:
    import re
    if not text or '\n' not in text:
        return text.strip()

    text = re.sub(r'\[([^\]]*?)\n\s*([^\]]*?)\]',
                  lambda m: f'[{m.group(1).strip()} {m.group(2).strip()}]', text)

    lines_pre = []
    for line in text.split('\n'):
        lines_pre.append(line.strip())
    text = '\n'.join(lines_pre)

    lines = text.split('\n')
    result = []

    for i, line in enumerate(lines):
        s = line.strip()

        if not s:
            if result and result[-1] != '':
                result.append('')
            continue

        if s.startswith('[') and ']' in s:
            result.append(s)
            continue

        if s.startswith('-'):
            result.append(s)
            continue

        next_line = next(
            (lines[j].strip() for j in range(i + 1, min(i + 4, len(lines)))
             if lines[j].strip()),
            ''
        )
        is_subheader = (
            2 <= len(s) <= 15
            and ':' not in s
            and not re.search(r'\d+\s*[%원만천]', s)
            and not s.endswith('=')
            and not s.endswith(':')
            and not s.endswith('이상') and not s.endswith('미만')
            and not s.endswith('등')
            and not re.search(r'(적용|제외|사용|이용|가능|불가|없음|입니다|니다|습니다)$', s)
            and next_line
            and len(next_line) > len(s)
        )

        if is_subheader:
            result.append(f'[{s}]')
        else:
            result.append(s)

    while result and result[-1] == '':
        result.pop()

    return '\n'.join(result)
