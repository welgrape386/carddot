# config.py - 삼성카드 크롤링 설정

from itertools import count

# ── 크롤링 대상 카드 목록
CARD_LIST = ["AAP1731", "ABP1689", "ABP1384", "ABP1383", "AAP1483", "AAP1452"]

# ── URL 설정
BASE_URL = "https://www.samsungcard.com/home/card/cardinfo/PGHPPCCCardCardinfoDetails001?code="
CDN_BASE = "https://static11.samsungcard.com"
LIST_URLS = [
    "https://www.samsungcard.com/home/card/cardinfo/PGHPPDCCardCardinfoRecommendPC001?webViewFirstPage=true&tabIndex=1",
    "https://www.samsungcard.com/home/card/cardinfo/PGHPPDCCardCardinfoRecommendPC001?webViewFirstPage=true&tabIndex=2",
]

# ── 카드사 고정값
CARD_COMPANY = "삼성"

# ── 브라우저 설정
BROWSER_HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ── 전역 시퀀스 (notice_id, benefit_id)
NOTICE_ID_SEQ = count(1)
BENEFIT_SEQ   = count(1)

# ── 카테고리 데이터
CATEGORY_DATA = [
    {"category_id": 1,  "category_name": "온라인쇼핑",          "category_list": ["온라인쇼핑", "삼성카드 쇼핑", "G마켓", "옥션", "11번가", "인터파크", "쿠팡", "티몬", "위메프", "SSG.COM", "롯데ON", "마켓컬리", "오아시스마켓"]},
    {"category_id": 2,  "category_name": "패션/뷰티",            "category_list": ["패션", "뷰티", "올리브영", "유니클로", "자라", "H&M", "8SECONDS"]},
    {"category_id": 3,  "category_name": "슈퍼마켓/생활잡화",    "category_list": ["슈퍼마켓", "생활잡화", "이마트", "트레이더스", "롯데마트", "홈플러스", "에브리데이", "빅마켓", "다이소"]},
    {"category_id": 4,  "category_name": "백화점/아울렛/면세점", "category_list": ["백화점", "아울렛", "면세점", "신세계", "롯데", "현대", "갤러리아", "동아", "대구백화점", "AK플라자", "NC 대전 유성점", "NC 대전유성점", "신세계사이먼 프리미엄 아울렛", "현대프리미엄아울렛"]},
    {"category_id": 5,  "category_name": "대중교통/택시",        "category_list": ["대중교통", "택시"]},
    {"category_id": 6,  "category_name": "자동차/주유",          "category_list": ["자동차", "주유", "SK에너지", "GS칼텍스", "현대오일뱅크", "S-OIL"]},
    {"category_id": 7,  "category_name": "반려동물",             "category_list": ["반려동물"]},
    {"category_id": 8,  "category_name": "구독/스트리밍",        "category_list": ["구독", "스트리밍", "넷플릭스", "웨이브", "티빙", "왓챠", "멜론", "FLO"]},
    {"category_id": 9,  "category_name": "레저/스포츠",          "category_list": ["레저", "스포츠", "에버랜드", "롯데월드", "서울랜드", "통도환타지아", "대전오월드", "경주월드", "이월드", "캐리비안베이", "아쿠아환타지아", "캘리포니아비치", "중흥골드스파", "디오션리조트 워터파크", "스파밸리"]},
    {"category_id": 10, "category_name": "페이/간편결제",        "category_list": ["페이", "간편결제", "삼성페이", "네이버페이", "카카오페이", "PAYCO", "스마일페이", "coupay", "SSGPAY", "L.PAY"]},
    {"category_id": 11, "category_name": "문화/엔터",            "category_list": ["문화", "엔터", "YES24", "인터파크 도서", "알라딘", "교보문고"]},
    {"category_id": 12, "category_name": "생활비",               "category_list": ["생활비", "SKT", "KT", "LG U+"]},
    {"category_id": 13, "category_name": "편의점",               "category_list": ["편의점"]},
    {"category_id": 14, "category_name": "커피/카페/베이커리",   "category_list": ["커피", "카페", "베이커리", "스타벅스", "이디야커피", "커피빈", "투썸플레이스", "블루보틀", "파리바게뜨", "배스킨라빈스", "던킨", "카페베네", "탐앤탐스", "엔제리너스", "할리스", "파스쿠찌", "아티제", "폴 바셋"]},
    {"category_id": 15, "category_name": "배달",                 "category_list": ["배달", "배달의민족", "요기요"]},
    {"category_id": 16, "category_name": "외식",                 "category_list": ["외식", "쉐이크쉑", "써브웨이"]},
    {"category_id": 17, "category_name": "여행/숙박",            "category_list": ["여행", "숙박"]},
    {"category_id": 18, "category_name": "항공",                 "category_list": ["항공"]},
    {"category_id": 19, "category_name": "해외",                 "category_list": ["해외"]},
    {"category_id": 20, "category_name": "교육/육아",            "category_list": ["교육", "육아", "씽크빅", "교원", "대교", "한솔교육"]},
    {"category_id": 21, "category_name": "의료",                 "category_list": ["의료"]},
]
