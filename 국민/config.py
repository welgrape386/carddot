# config.py - KB국민카드 크롤링 설정

import os

# ── URL 설정
BASE_URL       = "https://card.kbcard.com/CRD/DVIEW/"
CARD_PAGE_CODE = "HCAMCXPRICAC0076"

# ── 카드사 고정값
CARD_COMPANY      = "국민"
CARD_NAME_DEFAULT = "KB국민카드"

# ── 브라우저 설정
BROWSER_HEADLESS = True
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ── Anthropic API 키 (환경변수로 설정)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── 크롤링 대상 카드 (cooperation_code)
CARD_LIST = [
    "09922",  # KB ALL 카드
    "09771",  # KB YOU Prime 카드
    "09790",  # KB NEED Edu 카드
    "09562",  # 트래블러스 체크카드
    "07964",  # 노리2(KB Pay) 체크카드
    "07972",  # 노리2(Global) 체크카드
]

# ── CSV 필드 정의 (삼성카드와 동일 컬럼 구조)
INFO_FIELDS = [
    "card_id", "company", "card_name", "card_type",
    "network", "is_domestic_foreign", "has_transport",
    "annual_fee_dom_basic", "annual_fee_dom_premium",
    "annual_fee_for_basic", "annual_fee_for_premium",
    "annual_fee_notes",
    "min_performance", "extra_performance",
    "summary", "image_url",
    "link_url", "has_cashback", "updated_at",
]

BENEFIT_FIELDS = [
    "benefit_id",
    "card_id",
    "row_type",           # 혜택 / 유의사항 / 연회비
    "benefit_group",
    "benefit_title",
    "benefit_summary",
    "category",
    "category_id",        # 카테고리 ID (1~21)
    "on_offline",         # Online / Offline / Both
    "region",             # 국내 / 해외 / 둘다
    "benefit_type",       # 할인 / 포인트적립 / 마일리지 / 캐시백 / 서비스
    "value",
    "unit",               # % / 원 / M포인트
    "target_merchants",
    "excluded_merchants",
    "min_amount",         # 건당 최소 결제금액 조건
    "performance_level",
    "max_count",          # 월 최대 횟수
    "max_limit",
    "benefit_content",
    "updated_at",
]

NOTICE_FIELDS = [
    "notice_id",
    "card_id",
    "notice_category",
    "sub_category",
    "notice_content",
    "updated_at",
]

EVENT_FIELDS = [
    "card_id", "company", "card_name",
    "origin_event_code", "event_title", "event_link",
    "start_date", "end_date",
    "event_type", "section",
    "event_content",
    "updated_at",
]

# ── 카테고리 데이터 (삼성카드 config.py와 동일 구조)
CATEGORY_DATA = [
    {"category_id": 1,  "category_name": "온라인쇼핑",          "category_list": ["온라인쇼핑", "지마켓", "11번가", "옥션", "위메프", "티몬", "롯데온", "SSG", "온라인 쇼핑", "온라인장보기"]},
    {"category_id": 2,  "category_name": "패션/뷰티",            "category_list": ["패션", "뷰티", "올리브영", "무신사", "H&M", "자라", "유니클로", "스파브랜드", "화장품", "미용", "취미/자기관리"]},
    {"category_id": 3,  "category_name": "슈퍼마켓/생활잡화",    "category_list": ["슈퍼마켓", "생활잡화", "이마트", "홈플러스", "롯데마트", "코스트코", "다이소"]},
    {"category_id": 4,  "category_name": "백화점/아울렛/면세점", "category_list": ["백화점", "아울렛", "면세점", "롯데백화점", "현대백화점", "신세계", "갤러리아"]},
    {"category_id": 5,  "category_name": "대중교통/택시",        "category_list": ["대중교통", "교통", "버스", "지하철", "택시", "기차", "KTX", "SRT", "철도", "T-money", "티머니", "후불교통"]},
    {"category_id": 6,  "category_name": "자동차/주유",          "category_list": ["주유", "자동차", "정비", "하이패스", "고속도로", "주차", "GS칼텍스", "SK에너지", "S-OIL", "현대오일뱅크"]},
    {"category_id": 7,  "category_name": "반려동물",             "category_list": ["반려동물", "펫", "동물병원", "반려"]},
    {"category_id": 8,  "category_name": "구독/스트리밍",        "category_list": ["구독", "스트리밍", "넷플릭스", "웨이브", "티빙", "왓챠", "디즈니플러스", "유튜브 프리미엄", "멜론", "FLO", "OTT", "쇼핑 멤버십", "쿠팡 로켓와우", "네이버플러스 멤버십"]},
    {"category_id": 9,  "category_name": "레저/스포츠",          "category_list": ["레저", "스포츠", "골프", "피트니스", "헬스", "워터파크", "테마파크", "스키"]},
    {"category_id": 10, "category_name": "페이/간편결제",        "category_list": ["간편결제", "KB Pay", "삼성페이", "네이버페이", "카카오페이", "PAYCO", "페이코", "토스페이"]},
    {"category_id": 11, "category_name": "문화/엔터",            "category_list": ["영화", "놀이공원", "공연", "CGV", "메가박스", "롯데시네마", "문화", "엔터", "뮤지컬", "전시", "인터파크 티켓", "에버랜드", "롯데월드"]},
    {"category_id": 12, "category_name": "생활비",               "category_list": ["이동통신", "통신", "SKT", "KT", "LG U+", "LG U＋", "알뜰폰", "Liiv M", "보험", "공과금", "전기요금", "가스요금", "국민연금", "건강보험", "렌탈", "자동납부", "정기결제", "자동이체", "관리비"]},
    {"category_id": 13, "category_name": "편의점",               "category_list": ["편의점", "GS25", "CU", "세븐일레븐", "미니스톱", "이마트24"]},
    {"category_id": 14, "category_name": "커피/카페/베이커리",   "category_list": ["커피", "카페", "베이커리", "스타벅스", "이디야", "커피빈", "투썸", "메가커피", "빽다방", "파리바게뜨", "뚜레쥬르", "제과", "디저트"]},
    {"category_id": 15, "category_name": "배달",                 "category_list": ["배달", "배달의민족", "배민", "요기요", "쿠팡이츠", "땡겨요"]},
    {"category_id": 16, "category_name": "외식",                 "category_list": ["외식", "음식점", "레스토랑", "식당", "맥도날드", "버거킹", "KFC", "롯데리아", "아웃백", "빕스", "패밀리레스토랑", "전국맛집"]},
    {"category_id": 17, "category_name": "여행/숙박",            "category_list": ["여행", "숙박", "호텔", "렌터카", "야놀자", "여기어때", "에어비앤비", "모텔", "리조트", "펜션"]},
    {"category_id": 18, "category_name": "항공",                 "category_list": ["항공", "대한항공", "아시아나", "공항라운지", "라운지", "마일리지"]},
    {"category_id": 19, "category_name": "해외",                 "category_list": ["해외", "해외 가맹점", "해외이용", "해외겸용", "국제브랜드", "환율"]},
    {"category_id": 20, "category_name": "교육/육아",            "category_list": ["교육", "학원", "서점", "육아", "학교납입금", "등록금", "유아", "어린이", "학습", "문화센터", "학습지"]},
    {"category_id": 21, "category_name": "의료",                 "category_list": ["의료", "병원", "약국", "한의원", "치과", "건강", "일상케어"]},
]

# ── 카테고리 → On/Offline 매핑
ON_OFF_MAP = {
    "온라인쇼핑":           "Online",
    "패션/뷰티":            "Both",
    "슈퍼마켓/생활잡화":    "Offline",
    "백화점/아울렛/면세점": "Offline",
    "대중교통/택시":        "Offline",
    "자동차/주유":          "Offline",
    "반려동물":             "Both",
    "구독/스트리밍":        "Online",
    "레저/스포츠":          "Both",
    "페이/간편결제":        "Both",
    "문화/엔터":            "Both",
    "생활비":               "Online",
    "편의점":               "Offline",
    "커피/카페/베이커리":   "Both",
    "배달":                 "Online",
    "외식":                 "Both",
    "여행/숙박":            "Both",
    "항공":                 "Both",
    "해외":                 "Both",
    "교육/육아":            "Both",
    "의료":                 "Both",
}

# ── 카테고리 → 지역 매핑
LOCATION_MAP = {
    "온라인쇼핑":           "국내",
    "패션/뷰티":            "국내",
    "슈퍼마켓/생활잡화":    "국내",
    "백화점/아울렛/면세점": "국내",
    "대중교통/택시":        "국내",
    "자동차/주유":          "국내",
    "반려동물":             "국내",
    "구독/스트리밍":        "국내",
    "레저/스포츠":          "국내",
    "페이/간편결제":        "국내",
    "문화/엔터":            "국내",
    "생활비":               "국내",
    "편의점":               "국내",
    "커피/카페/베이커리":   "국내",
    "배달":                 "국내",
    "외식":                 "국내",
    "여행/숙박":            "국내",
    "항공":                 "국내",
    "해외":                 "해외",
    "교육/육아":            "국내",
    "의료":                 "국내",
}
