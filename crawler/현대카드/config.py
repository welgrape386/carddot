import re

# =============================================
# URL / 이미지 기본 경로
# =============================================
IMG_BASE_URL = "https://www.hyundaicard.com"

# card_id 추출 패턴: URL의 cardWcd 파라미터
CARD_ID_PATTERN = re.compile(r"[Cc]ard[Ww]cd=([A-Z0-9]+)")

# 카드사 판단 (URL 도메인 기반)
COMPANY_MAP = {
    "hyundaicard.com": "현대카드",
    "samsungcard.com": "삼성카드",
    "kbcard.com":      "KB국민카드",
    "shinhancard.com": "신한카드",
}

# =============================================
# 브라우저 설정
# =============================================
BROWSER_HEADLESS = True
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# =============================================
# 출력 파일 경로
# =============================================
OUTPUT_DIR     = "output"
OUTPUT_INFO    = f"{OUTPUT_DIR}/card_info.csv"
OUTPUT_BENEFIT = f"{OUTPUT_DIR}/card_benefit.csv"
OUTPUT_NOTICE  = f"{OUTPUT_DIR}/card_notices.csv"
OUTPUT_EVENTS  = f"{OUTPUT_DIR}/card_events.csv"

# =============================================
# CSV 컬럼 정의 (csv_base 기준)
# =============================================
INFO_FIELDS = [
    "card_id", "company", "card_name", "card_type", "network",
    "is_domestic_foreign", "has_transport",
    "annual_fee_dom_basic", "annual_fee_dom_premium",
    "annual_fee_for_basic", "annual_fee_for_premium",
    "annual_fee_notes", "min_performance", "summary",
    "image_url", "link_url", "has_cashback", "updated_at",
]

BENEFIT_FIELDS = [
    "benefit_id", "card_id", "row_type", "benefit_group", "benefit_title",
    "benefit_summary", "benefit_content",
    "category", "category_id", "on_offline", "region",
    "benefit_type", "benefit_value", "benefit_unit",
    "target_merchants", "excluded_merchants",
    "performance_level", "performance_min", "performance_max",
    "min_amount", "max_count", "max_limit", "max_limit_unit",
    "updated_at",
]

NOTICE_FIELDS = [
    "notice_id", "card_id", "notice_category", "sub_category",
    "notice_content", "updated_at",
]

EVENT_FIELDS = [
    "card_id", "company", "card_name", "origin_event_code",
    "event_title", "event_link", "start_date", "end_date",
    "event_type", "section", "event_content", "updated_at",
]