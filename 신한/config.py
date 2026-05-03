# ── 신한카드 크롤링 대상 카드 목록
# (카드명, URL) 튜플 리스트로 확장 가능
CARDS = [
    {
        "카드명": "신한카드 Point Plan+",
        "카드종류": "신용",
        "파일명": "PointPlanPlus",
        "url": "https://www.shinhancard.com/pconts/html/card/apply/credit/1228407_2207.html",
    },
    {
        "카드명": "신한카드 Point Plan",
        "카드종류": "신용",
        "파일명": "PointPlan",
        "url": "https://www.shinhancard.com/pconts/html/card/apply/credit/1226113_2207.html",
    },
    {
        "카드명": "신한카드 SOL트래블",
        "카드종류": "신용",
        "파일명": "SOLTravel",
        "url": "https://www.shinhancard.com/pconts/html/card/apply/credit/1227751_2207.html",
    },
    {
        "카드명": "신한카드 SOL트래블 체크",
        "카드종류": "체크",
        "파일명": "SOLTravel_check",
        "url": "https://www.shinhancard.com/pconts/html/card/apply/check/1225714_2206.html",
    },
    {
        "카드명": "신한카드 Point Plan 체크",
        "카드종류": "체크",
        "파일명": "PointPlan_check",
        "url": "https://www.shinhancard.com/pconts/html/card/apply/check/1226114_2206.html",
    },
    {
        "카드명": "신한카드 Hey Young 체크",
        "카드종류": "체크",
        "파일명": "HeyYoung_check",
        "url": "https://www.shinhancard.com/pconts/html/card/apply/check/1196867_2206.html",
    },
]

# ── 브라우저 설정
BROWSER_HEADLESS = True
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ── 신한카드 공통 설정
BASE_URL = "https://www.shinhancard.com"

# ── 카드사 고정값
CARD_COMPANY = "신한"