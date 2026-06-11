"""
main.py - 삼성카드 자동 크롤링 + AI 파싱 통합

실행:
  python main.py                   # 새 카드만
  python main.py --all             # 전체 재수집
  python main.py --card_id AAP1731 # 특정 카드만

cron (매일 오전 9시):
  0 9 * * * cd /your/project && python main.py >> pipeline.log 2>&1
"""

import asyncio, argparse, json, os, re, csv, sys
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import aiohttp
from collections import defaultdict

# em dash 등 cp949 미지원 문자를 터미널에 출력할 때 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(errors='replace')


# =============================================
# 설정
# =============================================

# FIX 1: API 키 하드코딩 제거
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY_SAMSUNG") or os.environ.get("ANTHROPIC_API_KEY", "")

PREFIX      = "samsung"
CARDS_JSON  = f"{PREFIX}_cards.json"
EVENTS_JSON = f"{PREFIX}_events.json"
CSV_DIR    = Path("output")
DEBUG_DIR  = Path("debug")
SAMSUNG    = "https://www.samsungcard.com"
STATIC     = "https://static11.samsungcard.com"
LIST_URL   = f"{SAMSUNG}/home/card/cardinfo/PGHPPCCCardCardinfoDetails001?code=AAP1731"
DETAIL_URL = f"{SAMSUNG}/home/card/cardinfo/PGHPPCCCardCardinfoDetails001"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

CATEGORY_MAP = {
    "온라인쇼핑": 1, "패션/뷰티": 2, "슈퍼마켓/생활잡화": 3,
    "백화점/아울렛/면세점": 4, "대중교통/택시": 5, "자동차/주유": 6,
    "반려동물": 7, "구독/스트리밍": 8, "레저/스포츠": 9,
    "페이/간편결제": 10, "문화/엔터": 11, "생활비": 12,
    "편의점": 13, "카페/베이커리": 14, "배달": 15,
    "외식": 16, "여행/숙박": 17, "항공": 18,
    "해외": 19, "교육/육아": 20, "의료": 21, "기타": 22,
}

BENEFIT_TYPECODES = {"001", "002", "003", "004", "005"}

# typeCode=""인 탭 중 안내로 확정된 제목 (전체 일치)
# 새 탭이 발견될 때마다 추가
INFO_TAB_NAMES = {
    # 결제 기능 안내
    "컨택리스(비접촉) 결제 지원",
    # 카드 안내
    "카드이용TIP",
    "카드 디자인 소개",
    "모바일카드 안내",
    # 카드 소재/디자인 안내 (혜택 없음)
    "LED PLATE",
    # BIZ/SFC 연동
    "BIZ SERVICE",
    "SFC 연동가맹점 할인",
    # 추가 안내 탭
    "추가 안내사항",
    "추가 안내 사항",
    "추가안내사항",
    "이용 안내",
}

# '서비스' 키워드가 있어도 서비스 행으로 만들지 않을 탭 패턴
# (Claude가 직접 파싱해야 하는 혜택 선택형 탭)
NON_SERVICE_TAB_KEYWORDS = [
    "옵션서비스",   # Needs & Identity 옵션서비스, My Shopping 옵션서비스 등
    "옵션 서비스",
    "닥터카서비스", # 엔진오일 교환 등 구체적 혜택이 있는 차량 서비스 → Claude 파싱
    "닥터카 서비스",
]

# '서비스' 키워드가 없어도 서비스 탭으로 처리할 패턴
EXTRA_SERVICE_TAB_KEYWORDS = [
    "무이자할부",       # 백화점·할인점 무이자할부 등
    "기후동행카드",     # 서울시 기후동행카드 후불교통 서비스
]

def is_service_tab(tab_name: str) -> bool:
    """탭 이름에 '서비스'가 포함되면 서비스 행으로 생성. 단 옵션서비스 등은 제외."""
    if any(kw in tab_name for kw in NON_SERVICE_TAB_KEYWORDS):
        return False
    return "서비스" in tab_name or any(kw in tab_name for kw in EXTRA_SERVICE_TAB_KEYWORDS)


# 특정 가맹점을 강제로 특정 카테고리에 매핑 (Claude 분류 오류 보정)
MERCHANT_CATEGORY_OVERRIDE: dict[str, str] = {
    "더플레이스":   "외식",
    "제일제면소":   "외식",
    "비비고":       "외식",
    "VIPS":         "외식",
    "빕스버거":     "외식",
    "CJ푸드빌":     "외식",
    "뚜레쥬르":     "카페/베이커리",
    "투썸플레이스": "카페/베이커리",
    "Mnet":         "구독/스트리밍",
    "티빙":         "구독/스트리밍",
    "웨이브":       "구독/스트리밍",
    "왓챠":         "구독/스트리밍",
    "멜론":         "구독/스트리밍",
    "FLO":          "구독/스트리밍",
    "지니뮤직":     "구독/스트리밍",
    "골프장":       "레저/스포츠",
    "골프연습장":   "레저/스포츠",
}

def _apply_merchant_category_override(benefits: list) -> list:
    """target_merchants에 강제 카테고리 매핑 대상 가맹점이 포함된 경우 카테고리를 보정.
    여러 가맹점이 섞인 행에서 카테고리가 달라지면 카테고리별로 행을 분리한다."""
    result = []
    for b in benefits:
        if b.get("row_type") != "주요혜택":
            result.append(b)
            continue

        mc = b.get("target_merchants", "").strip()
        if not mc:
            result.append(b)
            continue

        parts = [m.strip() for m in re.split(r',\s*', mc) if m.strip()]
        current_cat = b.get("category", "")

        # 각 가맹점의 최종 카테고리 결정
        cat_groups: dict = {}  # category → [merchant, ...]
        for merchant in parts:
            forced = MERCHANT_CATEGORY_OVERRIDE.get(merchant)
            cat = forced if forced else current_cat
            cat_groups.setdefault(cat, []).append(merchant)

        if len(cat_groups) == 1:
            # 모든 가맹점이 같은 카테고리 → 행 카테고리만 보정
            the_cat = next(iter(cat_groups))
            if the_cat != current_cat:
                print(f"  [가맹점카테고리 보정] group='{b.get('benefit_group','')}' mc={mc} {current_cat} → {the_cat}")
                b["category"] = the_cat
            result.append(b)
        else:
            # 카테고리가 섞임 → 카테고리별로 행 분리
            for cat, merchants in cat_groups.items():
                new_b = dict(b)
                new_b["category"] = cat
                new_b["target_merchants"] = ", ".join(merchants)
                print(f"  [가맹점카테고리 행분리] group='{b.get('benefit_group','')}' cat={cat} mc={merchants}")
                result.append(new_b)

    # 행 분리로 생긴 중복 합치기:
    # 같은 benefit_group+category+pm+bv+bt+on_offline 행이 여러 개면 target_merchants 합산 후 1개로
    merged_result = []
    seen_keys: dict = {}
    for b in result:
        if b.get("row_type") != "주요혜택":
            merged_result.append(b)
            continue
        key = (
            b.get("benefit_group", ""), b.get("category", ""),
            b.get("performance_min", ""), b.get("performance_max", ""),
            b.get("benefit_value", ""), b.get("benefit_unit", ""),
            b.get("benefit_type", ""), b.get("on_offline", ""),
            b.get("max_limit", ""), b.get("group_max_limit", ""),
        )
        if key in seen_keys:
            existing = seen_keys[key]
            existing_mc = existing.get("target_merchants", "")
            new_mc = b.get("target_merchants", "")
            if new_mc and new_mc not in existing_mc:
                existing["target_merchants"] = f"{existing_mc}, {new_mc}" if existing_mc else new_mc
        else:
            seen_keys[key] = b
            merged_result.append(b)

    return merged_result


def infer_service_tab_category(tab_name: str) -> str:
    """서비스 탭 이름 키워드로 카테고리 추론."""
    name = tab_name.replace(" ", "")
    if any(k in name for k in ["백화점", "면세점", "아울렛"]):
        return "백화점/아울렛/면세점"
    if any(k in name for k in ["항공", "마일리지", "스카이패스"]):
        return "항공"
    if any(k in name for k in ["여행", "호텔", "숙박", "리조트"]):
        return "여행/숙박"
    if any(k in name for k in ["골프", "스포츠", "레저"]):
        return "레저/스포츠"
    if any(k in name for k in ["주유", "자동차", "주차"]):
        return "자동차/주유"
    if any(k in name for k in ["쇼핑", "온라인"]):
        return "온라인쇼핑"
    if any(k in name for k in ["카페", "커피", "베이커리"]):
        return "카페/베이커리"
    if any(k in name for k in ["외식", "레스토랑", "식당"]):
        return "외식"
    if any(k in name for k in ["의료", "병원", "약국"]):
        return "의료"
    if any(k in name for k in ["교통", "후불"]):
        return "대중교통/택시"
    return "기타"


def is_info_by_tab_name(tab_name: str) -> bool:
    if tab_name in INFO_TAB_NAMES:
        return True
    return False

# =============================================
# CSV 설정
# =============================================

CSV_HEADERS = {
    "info": [
        "card_id", "company", "card_name", "card_type", "network",
        "is_domestic_foreign", "has_transport",
        "annual_fee_dom_basic", "annual_fee_dom_premium",
        "annual_fee_for_basic", "annual_fee_for_premium",
        "annual_fee_notes", "min_performance",
        "summary", "image_url", "link_url", "has_cashback", "fee_content", "updated_at",
    ],
    "benefit": [
        "benefit_id", "card_id", "row_type", "benefit_group",
        "benefit_title", "category", "category_id",
        "on_offline", "benefit_type", "benefit_value", "benefit_unit",
        "target_merchants",
        "performance_level", "performance_min", "performance_max",
        "min_amount", "unit_amount", "max_count", "max_limit", "max_limit_unit",
        "group_max_limit", "group_max_limit_unit", "updated_at", "ui_title", "ui_content",
    ],
    "notice": [
        "notice_id", "card_id", "notice_content", "updated_at",
    ],
    "event": [
        "event_id", "card_id", "company", "card_name", "origin_event_code",
        "event_title", "event_link", "start_date", "end_date",
        "event_type", "section", "event_content", "updated_at",
    ],
}

CSV_FILES = {
    "info":    "samsung_info.csv",
    "benefit": "samsung_benefit.csv",
    "notice":  "samsung_notices.csv",
    "event":   "samsung_events.csv",
}

def init_csv(reset: bool = False):
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    for key, filename in CSV_FILES.items():
        filepath = CSV_DIR / filename
        needs_reset = reset or not filepath.exists()
        if not needs_reset and filepath.exists():
            # 헤더가 현재 스키마와 다르면 재생성
            try:
                with open(filepath, "r", newline="", encoding="cp949") as f:
                    existing_headers = next(csv.reader(f), [])
                if existing_headers != CSV_HEADERS[key]:
                    print(f"  [init_csv] {filename} 헤더 불일치 → 재생성")
                    needs_reset = True
            except Exception:
                needs_reset = True
        if needs_reset:
            with open(filepath, "w", newline="", encoding="cp949") as f:
                csv.DictWriter(f, fieldnames=CSV_HEADERS[key]).writeheader()

def remove_card_from_csv(card_id: str):
    """특정 card_id의 기존 행을 모든 CSV에서 제거한다."""
    id_fields = {"info": "card_id", "benefit": "card_id", "notice": "card_id", "event": "card_id"}
    for key, filename in CSV_FILES.items():
        filepath = CSV_DIR / filename
        if not filepath.exists():
            continue
        with open(filepath, "r", newline="", encoding="cp949") as f:
            reader = csv.DictReader(f)
            rows = [r for r in reader if r.get(id_fields[key]) != card_id]
        with open(filepath, "w", newline="", encoding="cp949") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS[key])
            writer.writeheader()
            writer.writerows(rows)

# ·를 분리하면 안 되는 합성어 목록
_COMPOUND_MIDDOT_TERMS = [
    "병·의원",
    "국공립·사립",
]

def _normalize_merchants(s: str) -> str:
    """가맹점 구분자(·, /, &, 및)를 쉼표로 통일."""
    # 합성어 보호: 분리하면 안 되는 ·를 임시 플레이스홀더로 치환
    placeholders: dict = {}
    for i, term in enumerate(_COMPOUND_MIDDOT_TERMS):
        ph = f"\x00CMPD{i}\x00"
        if term in s:
            placeholders[ph] = term
            s = s.replace(term, ph)

    # '·' 가운데점, ' / ', ' & ', ' 및 ' → ', '
    s = re.sub(r'\s*[·]\s*', ', ', s)
    s = re.sub(r'\s*/\s*', ', ', s)
    s = re.sub(r'\s*&\s*', ', ', s)
    s = re.sub(r'\s*및\s*', ', ', s)
    # 연속 쉼표, 앞뒤 공백 정리
    s = re.sub(r',\s*,+', ',', s)
    s = s.strip(', ')

    # 합성어 복원
    for ph, term in placeholders.items():
        s = s.replace(ph, term)

    return s


def _normalize_row(row: dict) -> dict:
    """cp949로 인코딩할 수 없는 문자를 제거/치환, 가맹점 구분자 통일."""
    def clean(v: str, key: str = "") -> str:
        v = v.replace('\xa0', ' ').replace('​', '').replace('∙', '·')
        if key == "target_merchants":
            v = _normalize_merchants(v)
        return v.encode('cp949', errors='ignore').decode('cp949').strip()
    return {k: clean(v, k) if isinstance(v, str) else v for k, v in row.items()}

def save_csv(key: str, rows: list):
    if not rows: return
    rows = [_normalize_row(r) for r in rows]
    with open(CSV_DIR / CSV_FILES[key], "a", newline="", encoding="cp949") as f:
        csv.DictWriter(f, fieldnames=CSV_HEADERS[key], extrasaction="ignore").writerows(rows)


# =============================================
# 카드 목록 저장/로드
# =============================================

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {c["card_id"]: c for c in data} if isinstance(data, list) else data

def save_json(path: str, data: dict | list, label: str = ""):
    payload = sorted(data.values(), key=lambda c: c["card_id"]) if isinstance(data, dict) else data
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    if label:
        print(f"[완료] {path} 저장 ({len(payload)}개) - {label}")

def load_cards() -> dict:
    return load_json(CARDS_JSON)

def save_cards(cards: dict):
    save_json(CARDS_JSON, cards, "카드 목록")

def load_events() -> list:
    if not os.path.exists(EVENTS_JSON):
        return []
    with open(EVENTS_JSON, encoding="utf-8") as f:
        return json.load(f)

def save_events(events: list):
    existing  = load_events()
    seen      = {e["origin_event_code"] for e in existing}
    new_events = [e for e in events if e.get("origin_event_code") not in seen]
    merged    = existing + new_events
    with open(EVENTS_JSON, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"[완료] {EVENTS_JSON} 저장 (총 {len(merged)}개, 신규 {len(new_events)}개)")


# =============================================
# 프롬프트 (benefit만 AI 파싱)
# FIX 2: ui_title 규칙 단일 중괄호 → 이중 중괄호로 이스케이프
# =============================================

BENEFIT_PROMPT = """# 역할 (Role)

너는 삼성카드 혜택 데이터 파싱 및 분류 전문가야.

---

# 입력 데이터

**card_id**: {card_id}
**card_name**: {card_name}
**핵심혜택 요약 (ksp)**:
{ksp}

**혜택 상세 (bubble 탭 하나)**:
{bubble_content}

---

# 추출할 데이터 스키마

| 필드명 | 설명 |
| --- | --- |
| card_id | 카드 ID |
| row_type | 주요혜택 / 안내 |
| benefit_group | bubble tabName |
| benefit_title | 소제목 ([소제목] 태그 기준) |
| category | 카테고리 (다중값 쉼표 구분) |
| on_offline | Online / Offline / Both / 빈값 |
| benefit_type | 할인 / 캐시백 / 포인트 / 마일리지 / 서비스 |
| benefit_value | 혜택 수치만 |
| benefit_unit | % / 원 / 포인트 / 마일리지 |
| target_merchants | 할인/적립 대상 가맹점명 또는 업종명 (업종 접두사 제외: "음식점 :", "주유 :", "할인점 :" 등은 제거하고 뒤의 가맹점명만 입력) |
| performance_level | 전월실적 구간 텍스트 |
| performance_min | 전월실적 최솟값 (원 단위) |
| performance_max | 전월실적 최댓값 (없으면 빈값) |
| min_amount | 건당 최소 이용금액 |
| unit_amount | "N원당" 적립 기준금액 (예: 1500) |
| max_count | 월 최대 횟수 |
| max_limit | 월 최대 한도 |
| max_limit_unit | 한도 단위 |
| group_max_limit | benefit_group 내 모든 혜택이 공유하는 통합 월 한도 금액 |
| group_max_limit_unit | 통합 월 한도 단위 |
| ui_title | {{category}} {{benefit_value}}{{benefit_unit}} 적립/할인/캐시백 포맷 한 줄 요약 |

---

# 카테고리 목록
온라인쇼핑, 패션/뷰티, 슈퍼마켓/생활잡화, 백화점/아울렛/면세점,
대중교통/택시, 자동차/주유, 반려동물, 구독/스트리밍, 레저/스포츠,
페이/간편결제, 문화/엔터, 생활비, 편의점, 카페/베이커리,
배달, 외식, 여행/숙박, 항공, 해외, 교육/육아, 의료, 기타

---

# 파싱 규칙

### benefit_value ★ 가장 중요
- 혜택 수치만 추출. 전월실적/한도 수치 절대 금지

### benefit_type
- 할인: % 또는 원 단위로 깎아주는 것
- 캐시백: 결제 후 현금 환급
- 포인트: 포인트/리워드 적립 ("빅포인트", "모니머니", "리워드 적립")
- 마일리지: 항공 마일리지 적립
- 서비스: 위 외 부가서비스 ("공항 라운지", "보험", "무이자할부" 등)

### row_type
- 주요혜택: 독립적인 benefit_value가 명확히 존재하는 혜택 탭
  - benefit_value, benefit_unit, benefit_type 반드시 포함
  - category, target_merchants 반드시 포함
  - performance_min, performance_max, max_limit, max_limit_unit 반드시 포함
  - 실적 구간이 여러 개면 구간마다 행 분리
  - 카테고리가 여러 개면 카테고리마다 행 분리
  - ★ 연간/전월 이용금액 구간 × 업종 배율(기본/2배/5배 등) 2차원 표인 경우
    각 구간+업종 조합의 실제 계산된 % 값을 benefit_value에 입력할 것
    예) 600만원 미만 구간에서 기본 0.5%, 2배 업종 1%, 5배 업종 2.5%라면
        행1: pm=0~6000000, cat=기타, bv=0.5
        행2: pm=0~6000000, cat=학원/의료/여행/해외, bv=1
        행3: pm=0~6000000, cat=면세점/이동통신, bv=2.5
    benefit_value에 "0.5~5", "0.5~5배" 같은 범위 문자열 절대 금지 — 반드시 해당 구간의 실제값만 입력
- 안내: 아래 조건 중 하나라도 해당하면 안내로 분류
  1. benefit_value가 명확하지 않거나 없는 경우
  2. 다른 탭 혜택과의 중복 적용 안내, 이용처 목록, 결제 방법 설명만 있는 경우
  3. 할인/적립 혜택이 아닌 카드 기능 설명인 경우 (컨택리스 결제, NFC 지원 등)
  4. ★ 유의사항/주의사항/캐시백 제외 대상/적립 제외 대상 섹션에만 언급된 내용 → 절대 주요혜택으로 파싱 금지
     예) 유의사항에 "S-OIL 이용 시 보너스포인트와 빅포인트 중 높은 포인트 적립" → 안내
     예) 유의사항에 "보너스클럽 및 S-OIL 이용 시 ..." → 안내 (별도 주요혜택 행 생성 금지)
  - 안내로 분류 시 benefit_group만 채우고 나머지 필드 전부 빈값으로 출력
  - 판단이 애매한 경우 → 안내로 분류 (보수적으로 판단)

### target_merchants
- 원문에 있는 대상점 텍스트를 그대로 입력할 것
- 임의로 축약하거나 수정하지 말 것
- ★★ 업종 접두사(예: "음식점 :", "주유 :", "할인점 :", "음식 :" 등)는 target_merchants에 포함하지 말 것
  접두사를 제거하고 뒤에 오는 가맹점명/업종명만 입력
  예) "음식점 : 한식, 양식, 일식" → target_merchants="한식, 양식, 일식"
  예) "주유 : 전국 주유소 및 LPG 충전소" → target_merchants="전국 주유소, LPG 충전소"
  예) "할인점 : 이마트, 홈플러스, 롯데마트" → target_merchants="이마트, 홈플러스, 롯데마트"
- ★ 가맹점 목록이 길어도 절대 생략하지 말 것 ("..." 금지, 잘라내기 금지)
- ★ 표(대상점 표)에 업종별로 가맹점이 나열된 경우, 해당 업종의 모든 가맹점을 빠짐없이 포함할 것
  예: 업종=백화점, 가맹점=신세계/롯데/현대/갤러리아/동아/대구백화점, AK플라자, NC 대전 유성점
      → target_merchants에 모두 포함
  예: 업종=온라인 쇼핑몰, 가맹점=삼성카드 쇼핑, G마켓, 옥션, 11번가, 인터파크, 쿠팡, 티몬, 위메프, SSG.COM, 롯데ON
      → 전부 포함
- 같은 category 내 여러 업종의 가맹점은 쉼표로 합쳐서 1행에 모두 입력
  예: 백화점 업종 + 프리미엄 아울렛 업종이 모두 category="백화점/아울렛/면세점"이면
      두 업종의 가맹점을 합쳐서 1행으로 출력

### 카테고리 규칙
- 카테고리별로 대상점이나 혜택 내용이 다르면 카테고리당 1행으로 반드시 분리
- 카테고리가 달라도 대상점과 혜택 내용이 완전히 동일하면 분리하지 않음
- 같은 카테고리이고 benefit_value, max_limit이 동일하면 target_merchants를 쉼표로 합쳐서 1행으로 출력
- 분리된 각 행마다 해당 카테고리의 가맹점만 target_merchants에 입력 (없으면 빈값)
- ★ target_merchants에 "국내외 가맹점", "전 가맹점", "모든 가맹점" 등 전체 적용 표현이 있으면
  category="기타"로 분류할 것 (카드 이름이 항공/마일리지 관련이어도 무관)
  target_merchants 값은 반드시 원문 그대로 유지
- ★ "해외 가맹점", "해외 직접구매" 등 해외 이용 관련 대상점은 category="해외"로 분류
- ★ "신선식품 배송", "마켓컬리", "오아시스마켓" 등 식품 배송 가맹점은 category="슈퍼마켓/생활잡화"로 분류
- ★ "오늘의집", "집꾸미기" 등 인테리어/홈데코 온라인 플랫폼은 category="온라인쇼핑"으로 분류
- ★ "무신사", "W컨셉", "SSF", "한섬몰" 등 온라인 패션 전문몰은 category="패션/뷰티"로 분류
  단, 패션/뷰티 가맹점과 다른 카테고리 가맹점이 같은 할인율이라도 카테고리가 다르면 별도 행으로 분리
- ★ "넷플릭스", "웨이브", "티빙", "왓챠", "시즌", "멜론", "FLO", "지니뮤직", "유튜브 프리미엄", "Spotify" 등
  스트리밍/구독 서비스는 category="구독/스트리밍"으로 분류 (문화/엔터와 혼합 금지)
- ★ "온라인서점", "YES24", "교보문고", "알라딘" 등 서점 관련은 category="문화/엔터"로 분류
- ★ "학원", "어린이집", "유치원", "학습지", "씽크빅", "교원", "대교", "한솔교육" 등 교육 관련은 category="교육/육아"로 분류
- ★ "산후조리원"은 category="의료"로 분류
- ★ "이마트", "홈플러스", "롯데마트", "빅마켓", "코스트코", "트레이더스" 등 대형마트·할인점은
  category="슈퍼마켓/생활잡화"로 분류 (category="배달앱/생활편의" 또는 "기타" 금지)
- ★ "이동통신", "SKT", "KT", "LG U+", "알뜰폰", "통신요금", "휴대폰요금", "아파트 관리비", "관리비" 등
  통신요금·생활요금 관련 가맹점은 category="생활비"로 분류 (category="기타" 금지)
- ★ "VIPS", "빕스버거", "비비고", "뚜레쥬르", "투썸플레이스", "제일제면소", "더플레이스", "CJ푸드빌" 등
  CJ 계열 외식/베이커리 브랜드는 레스토랑/식음료 업종이므로 category="외식" 또는 "카페/베이커리"로 분류
  (더플레이스, 제일제면소, 비비고, VIPS, 빕스버거 → category="외식", 뚜레쥬르·투썸플레이스 → category="카페/베이커리")
- ★ "Mnet", "티빙", "웨이브", "왓챠", "멜론", "FLO", "지니뮤직" 등 음악·동영상 스트리밍 서비스는
  category="구독/스트리밍"으로 분류 (category="문화/엔터" 금지). CGV와 같은 행에 나와도 반드시 분리할 것
  예) CGV+Mnet+티빙 → 행1: CGV 문화/엔터 / 행2: Mnet, 티빙 구독/스트리밍

### 혜택 수치 분기 처리
- "A는 30% 할인, B는 50% 할인" 또는 "30% 또는 50% 할인"처럼 대상점/조건에 따라 수치가 다른 경우
  각 수치별로 별도 행으로 반드시 분리
- 분리 시 해당 수치가 적용되는 대상점을 target_merchants에 각각 입력
- ★ 유의사항에서 특정 가맹점에 다른 배율/할인율이 명시된 경우 (예: "올리브영은 5배 적립")
  해당 가맹점을 기본 배율 행의 target_merchants에서 반드시 제외하고 별도 행으로 분리
  예) 대상점: "A, B, C, D" + 유의사항: "D는 5배"
  → 행1: target_merchants="A, B, C" bv=2배
  → 행2: target_merchants="D" bv=5배
  (D를 행1에도 포함시키는 것은 금지)
- ★ "N배~M배 적립" 형태(배율 범위 탭)의 파싱 규칙:
  - 서비스안내의 최솟값(예: "2배~5배"에서 2배)이 대부분 가맹점의 기본 배율
  - 유의사항에서 "A는 M배"처럼 명시된 가맹점만 다른 배율 부여 가능
  - ★ 다른 탭의 할인금액("4,000원 할인")을 이 탭의 가맹점 배율("4배")로 절대 혼동하지 말 것
  - 명시되지 않은 가맹점은 반드시 최소 배율(기본 배율) 사용
- 본문 요약에 "A% 또는 B%"로 표현된 경우, 상세 표(패키지 조합표 등)를 반드시 우선 참조하여
  어떤 가맹점이 어떤 수치를 받는지 정확히 매핑할 것
  예: 요약에 "커피 30% 또는 50%"라고 나와도, 상세 표에서
      스타벅스 → 50%, 커피전문점 → 30%로 명시되어 있으면
      반드시 2행으로 분리하고 각 가맹점에 정확한 수치를 입력
- 절대로 높은 수치를 여러 가맹점에 일괄 적용하지 말 것
- 나머지 컬럼은 모든 행에 동일하게 복사
- 산후조리원 → 의료
- ★ category 필드에 절대 다중 카테고리를 쉼표로 넣지 말 것
  예: "페이/간편결제,해외" → 잘못된 출력
  → 반드시 페이/간편결제 1행 / 해외 1행으로 분리할 것
- ★ 대상점이 다른 카테고리는 benefit_value가 같아도 반드시 분리

### 전월실적
- "전월 30만원 이상" → performance_min: 300000
- "전월 30~60만원" → performance_min: 300000, performance_max: 600000
- 한도 구간표가 있으면 구간마다 반드시 행 분리
  예: 30만원 이상 10,000원 / 60만원 이상 20,000원 → 2행으로 분리
      행1: performance_min: 300000, performance_max: 600000, max_limit: 10000
      행2: performance_min: 600000, performance_max: (빈값), max_limit: 20000
  예: 30만원 이상 2,000원 / 60만원 이상 4,000원 / 100만원 이상 6,000원 → 3행으로 분리
      행1: performance_min: 300000, performance_max: 600000, max_limit: 2000
      행2: performance_min: 600000, performance_max: 1000000, max_limit: 4000
      행3: performance_min: 1000000, performance_max: (빈값), max_limit: 6000
- 구간별 혜택 다르면 구간마다 행 분리
- 주요혜택 행의 performance_min, max_limit을 절대 비워두지 말 것
- "발급월+N개월까지 전월실적 미달 시에도 제공"은 이용조건 설명일 뿐이며
  별도 행으로 절대 생성하지 말 것

### 전월실적 최솟값 없는 구간
- "30만원 미만" 구간은 performance_min: 0, performance_max: 300000
- 한도가 "-" 또는 없음이면 max_limit: "" (빈값)

### 자동 맞춤 혜택
- "A/B/C 중 가장 많이 쓴 1개 영역에 적용" 형태는
  카테고리별로 행 분리하되 max_limit은 반드시 빈값으로 두고
  group_max_limit에 통합 한도 입력
- max_limit에 절대 값을 넣지 말 것

### 택1 선택형 패키지 / 옵션서비스
- "A/B/C 중 택1" 또는 "옵션서비스" 탭에서 여러 옵션이 제시된 경우 각 옵션의 행을 모두 생성
- benefit_group = 탭 이름 (예: "라이프스타일 패키지 (택1)", "My Shopping 옵션서비스")
- 각 옵션의 한도는 max_limit에 개별 입력 — group_max_limit은 빈값
  (택1 옵션은 선택한 옵션의 한도만 적용되므로 옵션 간 한도를 공유하지 않음)
- 하나의 옵션 안에서 카테고리가 다른 가맹점이 함께 나오면 카테고리별로 행을 분리하되
  해당 옵션의 통합 한도는 분리된 각 행의 max_limit에 동일하게 입력

### 패키지 조합표 처리 (패키지1/패키지2/... 형태)
- "구분(택1)", "패키지1", "패키지2" 등 여러 패키지 조합이 표로 제시된 경우
  아래 절차를 반드시 순서대로 따를 것

  [Step 1] 표의 모든 행(패키지1~N)을 순서대로 읽으면서
           각 셀에 등장하는 (가맹점명, 수치, benefit_type) 쌍을 전부 목록화한다.
           예:
             패키지1 → (스타벅스, 50%, 할인), (오픈마켓, 7%, 할인), (소셜커머스, 1%, 적립), (트렌디숍, 1%, 적립)
             패키지2 → (스타벅스, 50%, 할인), (소셜커머스, 7%, 할인), (오픈마켓, 1%, 적립), (트렌디숍, 1%, 적립)
             패키지3 → (스타벅스, 50%, 할인), (트렌디숍, 7%, 할인), (오픈마켓, 1%, 적립), (소셜커머스, 1%, 적립)
             패키지4 → (커피전문점, 30%, 할인), (오픈마켓, 7%, 할인), (소셜커머스, 1%, 적립), (트렌디숍, 1%, 적립)
             패키지5 → (커피전문점, 30%, 할인), (소셜커머스, 7%, 할인), (오픈마켓, 1%, 적립), (트렌디숍, 1%, 적립)
             패키지6 → (커피전문점, 30%, 할인), (트렌디숍, 7%, 할인), (오픈마켓, 1%, 적립), (소셜커머스, 1%, 적립)

  [Step 2] 위 목록에서 중복을 제거하여 고유한 (가맹점, 수치, benefit_type) 쌍만 추린다.
           결과:
             (스타벅스, 50%, 할인)
             (커피전문점, 30%, 할인)   ← 스타벅스와 수치가 다르므로 반드시 별도 행
             (오픈마켓, 7%, 할인)
             (소셜커머스, 7%, 할인)
             (트렌디숍, 7%, 할인)
             (오픈마켓, 1%, 적립)
             (소셜커머스, 1%, 적립)
             (트렌디숍, 1%, 적립)

  [Step 3] 수치와 benefit_type이 동일한 가맹점끼리 합쳐서 행 수를 줄인다.
           최종 rows:
             스타벅스 50% 할인 → 1행
             커피전문점 30% 할인 → 1행  (50%로 올리거나 스타벅스와 합치면 절대 안 됨)
             오픈마켓, 소셜커머스, 트렌디숍 7% 할인 → 1행
             오픈마켓, 소셜커머스, 트렌디숍 1% 적립 → 1행

  [금지 사항]
  - 서로 다른 수치를 가진 가맹점을 한 행에 합치는 것 (예: 스타벅스50%와 커피전문점30%를 같은 행에 넣는 것)
  - 요약 문구의 수치("30% 또는 50%")를 근거로 여러 가맹점에 동일 수치를 적용하는 것
  - 상세 표보다 상위 요약을 우선하는 것 → 반드시 상세 표 기준으로 추출

  - 패키지 조합 상세는 ui_content에 자동 포함되므로 rows에는 대표값만 출력

### 통합 월 한도 처리
- "통합 월 할인한도", "통합 월 한도", "통합 월 적립한도", "통합 월 캐시백한도" 문구가
  표 제목이든 이용조건 텍스트든 어디에 나오든 반드시 한도값을 기록할 것
- ★ 이용조건에 "통합 월 할인한도 : N원" 형태로 나와도 반드시 기록 (누락 금지)

- 판단 기준:
  - "통합 월 N원", "통합한도 N원" 처럼 여러 카테고리가 N원을 공유하는 경우
    → 해당 카테고리 행 모두에 group_max_limit=N, max_limit 빈값
  - "각 월 최대 N원", "각각 N원" 처럼 카테고리별로 개별 한도가 N원인 경우
    → 각 행에 max_limit=N, group_max_limit 빈값
  - 해당 탭에서 출력 행이 카테고리 1개인 경우 → max_limit에 입력, group_max_limit 빈값
  - max_limit과 group_max_limit을 동시에 채우지 말 것
  - ★ "일 1회", "월 5회", "연 12회" 등 이용 횟수 제한은 group_max_limit이 아닌 max_count에 입력
    (group_max_limit/max_limit은 원/포인트 단위 금액 한도에만 사용)
  - ★ 옵션서비스 탭에서 옵션1과 옵션2의 한도 문구가 다르면 옵션별로 위 기준을 각각 적용
    예: 옵션1 "각 월 최대 10,000원" → 옵션1 행에 ml=10000, gml 빈값
        옵션2 "통합 월 10,000원" → 옵션2 행에 gml=10000, ml 빈값

- 실적 구간별 통합 한도 패턴 (한도가 실적에 따라 다른 경우):
  "전월 이용금액대별 통합 월 캐시백한도" / "전월 이용금액대별 통합 월 할인한도" / "전월 이용금액대별 통합 월 적립한도" 같은 제목 아래
  실적 구간별 한도가 표로 표시될 때:
    30만원 이상: 2,000원   → performance_min=300000, group_max_limit=2000
    60만원 이상: 4,000원   → performance_min=600000, group_max_limit=4000
    100만원 이상: 6,000원  → performance_min=1000000, group_max_limit=6000
  ★★★ "N만원 이상" / "N만원 미만" 형태는 이용금액 실적 구간이므로 반드시 performance_min/performance_max에 입력
       절대로 group_max_limit에 넣지 말 것 — group_max_limit은 원/포인트 단위 혜택 한도값에만 사용
  ★★★ 표의 열 헤더("40만원 이상", "80만원 이상" 등) → performance_min (절대 gml 아님)
  ★★★ 표의 셀 값(3,000원, 6,000원 등 할인/적립 한도) → group_max_limit
  예) 표 헤더: 40만원 이상 | 80만원 이상  /  표 값: 3,000원 | 6,000원
      → 행1: performance_min=400000, group_max_limit=3000   ← gml=3000 (절대 400000이나 800000 아님)
      → 행2: performance_min=800000, group_max_limit=6000   ← gml=6000 (절대 400000이나 800000 아님)
  잘못된 예) performance_min=400000, group_max_limit=800000  ← gml에 실적구간값 800000 절대 금지
  잘못된 예) 표 헤더가 2개(40만/80만)인데 행을 1개만 생성 → 반드시 2행 생성
  잘못된 예) performance_min=400000, group_max_limit=80000   ← 이용조건의 "80만원"을 gml로 파싱 절대 금지
  마일리지 단위 예시:
    100만원 이상: 1,500마일리지 → performance_min=1000000, group_max_limit=1500, group_max_limit_unit=마일리지
    200만원 이상: 4,000마일리지 → performance_min=2000000, group_max_limit=4000, group_max_limit_unit=마일리지
  ★ 구간이 2개 이상이면 반드시 모든 구간을 행으로 생성할 것 (구간 누락 금지)
  ★ 각 구간의 한도는 해당 탭의 모든 카테고리 행에 동일하게 적용 (카테고리당 구간수만큼 행 생성)
  ★ max_limit은 빈값, group_max_limit에만 입력

- 카테고리별 개별 한도가 따로 명시된 경우 → max_limit만 입력, group_max_limit 빈값

### 행 분리 기준
1. 전월실적 구간이 다를 때
2. benefit_value가 다를 때
3. max_limit이 다를 때
4. 카테고리가 다를 때

### unit_amount
- "N원당 M마일/포인트" 형태의 적립 기준금액
- 예: "1,500원당 스카이패스 1마일리지 적립" → unit_amount: 1500
- 예: "1,000원당 1포인트 적립" → unit_amount: 1000
- benefit_unit이 마일리지/포인트이고 "N원당" 텍스트가 있는 경우만 입력
- "N원 이상", "N원 할인" 등 다른 형태는 절대 입력 금지
- 해당 없으면 반드시 빈값

### 삼성카드 특유
- "결제일할인" → benefit_type: "할인"
- "모니머니", "리워드 적립" → benefit_type: "포인트"
- ★ "건별 N원 이상 결제 시 M원 할인/캐시백" 형태의 탭은 반드시 주요혜택 행으로 파싱할 것
  - benefit_value: M, benefit_unit: "원", benefit_type: "할인" 또는 "캐시백"
  - min_amount: N (건별 최소 이용금액)
  - "통합 월 1회", "연 N회" 등 이용횟수 제한 → max_count에 입력
  예: "건별 30만원 이상 결제 시 50,000원 결제일할인, 통합 월 1회·연 2회"
    → benefit_value=50000, benefit_unit=원, benefit_type=할인, min_amount=300000, max_count=2
- ★ "N원 이하 X원 할인 / N원 초과 Y원 할인" 구조의 두 행이 있을 때:
  - 이하 케이스: min_amount 없음 (빈값). 혜택은 소액 결제에도 적용되므로 하한이 없음
  - 초과 케이스: min_amount=N (N원 초과부터 적용)
  예) 8,500원 이하 결제 → 1,500원 할인: min_amount= (빈값)
      8,500원 초과 결제 → 3,000원 할인: min_amount=8500
- ★ 영화관 탭이 오프라인/온라인 별도 탭으로 구성된 경우:
  - 탭 이름에 "(오프라인)"이 포함된 탭: target_merchants="CGV(오프라인)"
  - 탭 이름에 "(온라인)"이 포함된 탭: target_merchants="CGV(온라인)"
  - 두 탭 모두 동일한 performance_min 조건(예: 30만원 이상)이 적용되므로 반드시 둘 다 기입할 것
  - 발급월 예외 조건("발급월+N개월까지 이용금액에 관계없이")은 별도 행으로 분리하지 말 것 (무시)
  - ★★★ 이용조건/이용안내 섹션에 언급된 금액("40만원 이상~80만원 미만" 등)은 어떤 필드에도 파싱하지 말 것
    오직 할인기준/적립조건 표(헤더+값)에서만 performance_min과 group_max_limit/max_limit을 파싱할 것
    예) 이용조건: "40만원 이상~80만원 미만 실적구간 혜택 제공" → 완전 무시 (별도 행 생성 금지)
    예) 이용조건: "80만원 이상 시에는 해당 실적구간 혜택 제공" → 완전 무시 (gml에 80000 입력 금지)
- ★★ "일 N회, 연 M회" 형태의 이용횟수 제한이 있을 때: max_count에는 반드시 연 M회(M)를 입력
  ★★ "일 N회"는 일별 상한선일 뿐이므로 max_count에 절대 입력하지 않음
  예) "통합 일 1회, 연 3회 제공" → max_count=3 (절대 1이 아님)
  예) "일 1회, 연 3회 제공" → max_count=3 (절대 1이 아님)
- ★ 닥터카서비스 탭 파싱 시: 각 서비스 항목을 주요혜택 행으로 분리
  - 할인 금액이 명시된 항목: benefit_type="할인", benefit_value=금액, benefit_unit="원"
  - 무료 제공 항목: benefit_type="서비스", benefit_value="", benefit_unit=""
  - max_count: 연 N회를 max_count에 입력
  - target_merchants: 탭에 명시된 대상 가맹점(애니카랜드, 스피드메이트, 카젠, 오토오아시스 등)
  예) 엔진오일 교환 시 15,000원 현장할인 (연 1회)
    → row_type=주요혜택, bt=할인, bv=15000, bu=원, mc=애니카랜드, 스피드메이트, 카젠, 오토오아시스, cnt=1
  예) 차량 안전점검 무료 (연 1회)
    → row_type=주요혜택, bt=서비스, bv=, bu=, mc=애니카랜드, 스피드메이트, 카젠, 오토오아시스, cnt=1
- ★ 프로스포츠 할인 테이블 파싱 시:
  - 각 구단·좌석등급 조합을 별도 행으로 분리
  - ★★ benefit_value가 명시된 모든 행은 반드시 값을 입력할 것 (빈값 금지)
  - target_merchants: 구단명(종목) 형태 입력, 좌석등급이 다르면 구단명에 좌석등급 포함
  - max_count: 해당 행의 할인 매수 기입
  예) 삼성라이온즈(야구) 현장결제 1,000원 1매, 온라인예매 1,000원 2매
    → 행1: mc=삼성라이온즈(야구), bv=1000, cnt=1 / 행2: mc=삼성라이온즈(야구), bv=1000, cnt=2
  예) 삼성라이온즈 W/E석 현장결제/온라인예매 2,000원 4매
    → mc=삼성라이온즈(야구) W/E석, bv=2000, cnt=4

### ui_title 규칙
- 주요혜택 행에만 입력, 안내 행은 빈값
- 기본 포맷: {{category}} {{benefit_value}}{{benefit_unit}} {{표기}}
- category 다중값이면 · 로 구분
  예: "생활비·교육/육아 1천포인트 {{표기}}" 
- benefit_value 천 단위 표기: 1000 → 1천, 5000 → 5천, 10000 → 1만
- benefit_unit이 %이면 숫자 바로 뒤에 붙임: "외식 5% 할인"
- unit_amount가 있으면: {{category}} {{unit_amount}}원당 {{benefit_value}}{{benefit_unit}} {{표기}}
  예: "항공 1,500원당 1마일 {{표기}}" 
- benefit_type이 "서비스"이면 핵심 서비스 내용 한 줄 요약
  예: "항공 1,500원당 1마일 {{표기}}" 

### ui_title benefit_type 표기 변환
- 포인트 → "적립"
- 마일리지 → "적립"
- 할인 → "할인"
- 캐시백 → "캐시백"
- 서비스 → benefit_type 텍스트 사용 안 하고 서비스 내용 직접 서술

### 중요
- bubble_content에 명시된 내용만 파싱할 것
- ksp는 참고용이며, bubble_content에 없는 혜택을 ksp에서 추출하여 행을 생성하지 말 것
- ★★ 대상점 표에 없는 업종/가맹점으로 행을 생성하지 말 것
  예: 탭의 대상점 표가 "이동통신, 아파트 관리비"만 있으면 대중교통/택시, 배달 등 행 생성 절대 금지
  다른 탭 내용을 추론하거나 혼용하지 말 것 — 해당 bubble_content에 있는 대상점만 사용
- ★★ 유의사항/할인 제외 대상/전월 이용금액 산정 기준 등의 섹션에서 언급된 업종·가맹점·혜택명은
  해당 탭의 혜택이 아님 — 절대 행으로 생성하지 말 것
  예: "전월 이용금액 산정 시 대중교통·택시 10% 할인/배달앱 10% 할인...은 제외" →
      대중교통/택시, 배달 행 생성 금지 (이 탭 혜택이 아니라 실적 계산 제외 목록임)
- ★ tab_name에 "추가" 또는 "추가적립"이 포함된 탭에서는 해당 탭의 추가 혜택 대상만 파싱할 것
  "기본 N마일리지 + 추가 N마일리지의 형태로 적립" 등 기본 적립 설명은 참조 정보이며
  기본 적립("국내외 가맹점" 등 전체 가맹점 대상)으로 별도 행을 생성하지 말 것
- ★ "옵션 서비스", "옵션서비스" 탭에서 "택1" 방식으로 여러 옵션이 제시된 경우
  각 옵션을 별도 행으로 모두 파싱할 것 (사용자가 선택 가능한 혜택이므로 전부 포함)

---

# 출력 형식
JSON 배열만 출력. 설명, 마크다운 코드블록 불필요."""


# =============================================
# __NUXT__ 데이터 추출
# =============================================

async def get_nuxt_data(page):
    return await page.evaluate("""
        () => {
            try {
                const n = window.__NUXT__;
                const d = n?.data?.[0] ?? n?.state ?? n?.payload?.data?.[0] ?? null;
                return (d && typeof d === 'object' && !Array.isArray(d)) ? d : null;
            } catch(e) { return null; }
        }
    """)

async def goto_and_wait(page, url, nuxt_check):
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    try:
        await page.wait_for_function(nuxt_check, timeout=30000)
    except Exception:
        await page.wait_for_timeout(8000)


# =============================================
# Step 1: 카드 목록 수집
# =============================================

async def get_card_list(page):
    print("카드 목록 수집 중...")
    await goto_and_wait(page, LIST_URL,
        "() => { try { return !!(window.__NUXT__?.data?.[0]?.wcms); } catch(e) { return false; } }")

    data = await get_nuxt_data(page)
    if not data or not isinstance(data, dict):
        raise RuntimeError("__NUXT__ 데이터를 찾을 수 없음")

    wcms    = data.get("wcms", [])
    pd_list = wcms if isinstance(wcms, list) else wcms.get("pdList", [])
    cards   = [{"card_id": c["code"], "card_name": "", "page_url": f"{DETAIL_URL}?code={c['code']}"}
               for c in pd_list if isinstance(c, dict) and c.get("code")]
    print(f"카드 목록 수집 완료: {len(cards)}개")
    return cards


# =============================================
# Step 2: 카드 상세 크롤링
# =============================================

def _parse_package_table_pairs(detail_text: str, raw_html: str) -> set:
    """패키지 탭에서 (가맹점, 수치, 타입) 쌍을 추출하는 공통 헬퍼.

    우선순위:
    1. raw_html 테이블 직접 파싱 (형식 A: 행=가맹점 / 형식 B: 열=가맹점)
    2. detail_text의 '패키지N: 가맹점 수치% 타입' 형식 (폴백)
    """
    pairs: set = set()

    if raw_html:
        soup = BeautifulSoup(raw_html, "html.parser")
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            header_cells = [c.get_text(" ", strip=True) for c in rows[0].find_all(["th", "td"])]
            if not header_cells:
                continue
            # 형식 A: 헤더 열에 '패키지N' → 각 행의 첫 셀이 가맹점명
            # 형식 B: 헤더 열에 가맹점명  → 각 행의 첫 셀이 패키지명
            is_format_a = any(re.search(r'패키지\d*', h) for h in header_cells[1:])
            for tr in rows[1:]:
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                if not cells:
                    continue
                if is_format_a:
                    merchant = cells[0]
                    for val in cells[1:]:
                        m = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(할인|적립)', val)
                        if m:
                            pairs.add((merchant, m.group(1), m.group(2)))
                else:
                    for col_idx, val in enumerate(cells[1:], 1):
                        if col_idx >= len(header_cells):
                            break
                        merchant = header_cells[col_idx]
                        m = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(할인|적립)', val)
                        if m:
                            pairs.add((merchant, m.group(1), m.group(2)))

    if not pairs:
        for row in re.findall(r'^패키지\d+:\s*(.+)$', detail_text, re.MULTILINE):
            for item in [i.strip() for i in row.split(',')]:
                m = re.match(r'^(.+?)\s+(\d+(?:\.\d+)?)\s*%\s*(할인|적립)', item)
                if m:
                    pairs.add((m.group(1).strip(), m.group(2), m.group(3)))

    return pairs


def extract_package_summary(detail_text: str, raw_html: str = "") -> str:
    """패키지 탭 (가맹점, 수치, 타입) 쌍을 Claude용 요약 문자열로 변환."""
    pairs = _parse_package_table_pairs(detail_text, raw_html)
    if not pairs:
        return ""

    merchant_rates: dict = defaultdict(set)
    for merchant, rate, type_ in pairs:
        merchant_rates[merchant].add((rate, type_))

    fixed_pairs = {(m, *next(iter(rv))) for m, rv in merchant_rates.items() if len(rv) == 1}
    grouped: dict = defaultdict(list)
    for merchant, rate, type_ in fixed_pairs:
        grouped[(rate, type_)].append(merchant)

    lines = ["## 패키지 혜택 요약 (반드시 이 기준으로만 행 생성 — 아래 원본 표보다 이 요약이 우선):"]
    for (rate, type_), merchants in sorted(grouped.items(), key=lambda x: -float(x[0][0])):
        lines.append(f"- {', '.join(sorted(merchants))}: {rate}% {type_}")
    for merchant, rv in merchant_rates.items():
        if len(rv) > 1:
            combos = " 또는 ".join(f"{r}% {t}" for r, t in sorted(rv, key=lambda x: -float(x[0])))
            lines.append(f"- {merchant}: {combos} (패키지에 따라 다름 → 수치별로 반드시 행 분리)")
    lines.append("※ 수치가 다른 가맹점은 절대 같은 행에 합치지 말 것\n")
    return '\n'.join(lines)


def get_package_merchant_rates(detail_text: str, raw_html: str = "") -> dict:
    """수치가 고정된(모든 패키지에서 동일한) 가맹점 → (rate, type) 매핑 반환."""
    pairs = _parse_package_table_pairs(detail_text, raw_html)
    merchant_rates: dict = defaultdict(set)
    for merchant, rate, type_ in pairs:
        merchant_rates[merchant].add((rate, type_))
    return {m: next(iter(rv)) for m, rv in merchant_rates.items() if len(rv) == 1}


def _fix_ui_title_consistency(rows: list) -> list:
    """ui_title의 수치·타입이 benefit_value·benefit_type과 다르면 ui_title 기준으로 교정."""
    TYPE_MAP = {"적립": "포인트", "할인": "할인", "캐시백": "캐시백"}
    for row in rows:
        if row.get("row_type") != "주요혜택":
            continue
        ui_title = row.get("ui_title", "")
        if not ui_title:
            continue
        m = re.search(r'(\d+(?:\.\d+)?)(%?)\s*(할인|캐시백|적립)', ui_title)
        if not m:
            continue
        ui_value = m.group(1)
        ui_type  = TYPE_MAP.get(m.group(3), "")
        if not ui_type:
            continue
        # 범위형 benefit_value("~", "배" 포함)는 교정 건너뜀 — 교정 시 최댓값으로 덮어써져 실제값 손실
        raw_bv = str(row.get("benefit_value", "")).strip()
        if "~" in raw_bv or "배" in raw_bv:
            continue
        if raw_bv != ui_value or row.get("benefit_type", "").strip() != ui_type:
            print(f"  [ui_title 교정] {row.get('benefit_id','')} value {row.get('benefit_value')}→{ui_value}, type {row.get('benefit_type')}→{ui_type}")
            row["benefit_value"] = ui_value
            row["benefit_type"]  = ui_type
    return rows


def _remove_issue_month_rows(benefits: list) -> list:
    """발급월 예외(발급월+N개월까지 실적 미달 시에도 제공)가 별도 행으로 잘못 파싱된 경우 제거.
    같은 benefit_group+category+on_offline에서 performance_min>0 행이 있는데,
    performance_min=0/'' 이고 performance_max도 빈 행 → 발급월 예외로 간주하여 제거.
    on_offline이 다른 행은 별개 채널이므로 서로 영향 없음."""
    from collections import defaultdict
    group_cat_has_positive: dict = defaultdict(bool)
    for b in benefits:
        if b.get("row_type") != "주요혜택":
            continue
        try:
            if int(str(b.get("performance_min", "") or 0)) > 0:
                key = (b.get("benefit_group", ""), b.get("category", ""), b.get("on_offline", ""))
                group_cat_has_positive[key] = True
        except (ValueError, TypeError):
            pass

    result = []
    for b in benefits:
        if b.get("row_type") == "주요혜택":
            key  = (b.get("benefit_group", ""), b.get("category", ""), b.get("on_offline", ""))
            pm   = str(b.get("performance_min", "") or "").strip()
            pmax = str(b.get("performance_max", "") or "").strip()
            if group_cat_has_positive.get(key) and pm in ("0", "") and pmax == "":
                print(f"  [발급월 예외 제거] group='{b.get('benefit_group')}' cat='{b.get('category')}' on_off='{b.get('on_offline','')}' merchants='{b.get('target_merchants','')}'")
                continue
        result.append(b)
    return result


def _remove_empty_merchant_rows(rows: list) -> list:
    """benefit_group 내에 target_merchants가 있는 행이 존재하는데
    target_merchants가 없는 행이 섞여 있으면 해당 행을 제거 (Claude 환각 방지)."""
    from collections import defaultdict
    group_has_merchant: dict = defaultdict(bool)
    for row in rows:
        if row.get("row_type") == "주요혜택" and row.get("target_merchants", "").strip():
            group_has_merchant[row.get("benefit_group", "")] = True

    result = []
    for row in rows:
        if (
            row.get("row_type") == "주요혜택"
            and row.get("benefit_type") != "서비스"  # 서비스 타입은 merchants 없어도 정상
            and group_has_merchant.get(row.get("benefit_group", ""))
            and not row.get("target_merchants", "").strip()
        ):
            print(f"  [환각 제거] benefit_group='{row.get('benefit_group')}' category='{row.get('category')}' → target_merchants 없음")
            continue
        result.append(row)
    return result


UNIVERSAL_MERCHANT_KEYWORDS = ["국내외 가맹점", "전 가맹점", "전체 가맹점", "국내외 전 가맹점", "모든 가맹점"]


def _is_universal_merchant(merchants: str) -> bool:
    if not merchants.strip():
        return True
    return any(kw in merchants for kw in UNIVERSAL_MERCHANT_KEYWORDS)


def _merge_extra_earn_totals(benefits: list) -> list:
    """추가 적립 그룹의 특정 가맹점 행에 기본 적립률을 합산하여 합산 적립률로 표시.
    부수 효과: 추가 적립 그룹의 범용 가맹점 행(할루시네이션)과
               기본 적립 그룹의 중복 특정 가맹점 행을 제거."""

    # 기본 적립 그룹에서 범용 가맹점 행의 base 적립률 수집
    # key: (card_id, benefit_type, benefit_unit, performance_min) → base benefit_value
    base_earn: dict = {}
    for b in benefits:
        if b.get("row_type") != "주요혜택":
            continue
        if "추가" in b.get("benefit_group", ""):
            continue
        if not _is_universal_merchant(b.get("target_merchants", "")):
            continue
        key = (
            b.get("card_id", ""),
            b.get("benefit_type", ""),
            b.get("benefit_unit", ""),
            str(b.get("performance_min", "") or ""),
        )
        if key not in base_earn:
            base_earn[key] = b.get("benefit_value", "")

    if not base_earn:
        return benefits

    def _split_merchants(s: str) -> list:
        """·, ,, / 등으로 구분된 가맹점 문자열을 개별 가맹점 리스트로 분리."""
        parts = re.split(r'[,·/]', s)
        return [p.strip() for p in parts if p.strip()]

    # 추가 적립 그룹에 있는 개별 가맹점 목록 (중복 제거 기준)
    extra_specific_merchants: set = set()
    for b in benefits:
        if b.get("row_type") != "주요혜택":
            continue
        if "추가" not in b.get("benefit_group", ""):
            continue
        for m in _split_merchants(b.get("target_merchants", "")):
            if not _is_universal_merchant(m):
                extra_specific_merchants.add(m)

    result = []
    for b in benefits:
        if b.get("row_type") != "주요혜택":
            result.append(b)
            continue

        group = b.get("benefit_group", "")
        merchants = b.get("target_merchants", "")

        # 추가 적립 그룹의 범용 가맹점 행 → 기본 적립 설명 오파싱이므로 제거
        if "추가" in group and _is_universal_merchant(merchants):
            print(f"  [추가적립 범용가맹점 제거] group='{group}' merchants='{merchants}'")
            continue

        # 기본 적립 그룹의 특정 가맹점 행이 추가 적립 그룹에도 존재하면 → 중복 제거
        # 단, benefit_type/unit이 base_earn과 동일한 경우에만 제거 (할인/캐시백 등 다른 혜택 행은 보존)
        if "추가" not in group and not _is_universal_merchant(merchants):
            merchant_list = _split_merchants(merchants)
            if extra_specific_merchants and any(m in extra_specific_merchants for m in merchant_list):
                _dedup_key = (
                    b.get("card_id", ""),
                    b.get("benefit_type", ""),
                    b.get("benefit_unit", ""),
                    str(b.get("performance_min", "") or ""),
                )
                if _dedup_key in base_earn:
                    print(f"  [기본탭 중복 제거] group='{group}' merchants='{merchants}'")
                    continue

        # 추가 적립 그룹의 특정 가맹점 행 → benefit_value를 기본+추가 합산으로 업데이트
        if "추가" in group and not _is_universal_merchant(merchants):
            key = (
                b.get("card_id", ""),
                b.get("benefit_type", ""),
                b.get("benefit_unit", ""),
                str(b.get("performance_min", "") or ""),
            )
            base_value = base_earn.get(key)
            if base_value:
                try:
                    old_extra = b.get("benefit_value", "")
                    total_float = float(str(base_value)) + float(str(old_extra or 0))
                    total_str = str(int(total_float)) if total_float == int(total_float) else str(total_float)
                    b = dict(b)
                    # ui_title 내 구 수치 → 합산 수치로 교체 (첫 번째 숫자만)
                    old_extra_int = str(int(float(str(old_extra or 0)))) if old_extra else ""
                    if old_extra_int:
                        b["ui_title"] = re.sub(
                            r'(?<!\d)' + re.escape(old_extra_int) + r'(?!\d)',
                            total_str, b.get("ui_title", ""), count=1,
                        )
                    b["benefit_value"] = total_str
                    print(f"  [추가적립 합산] '{merchants}': 기본 {base_value} + 추가 {old_extra} = 합산 {total_str}")
                except (ValueError, TypeError):
                    pass

        result.append(b)

    return result


def _fix_package_rows(rows: list, merchant_rate: dict) -> list:
    """Claude가 잘못 합친 가맹점/수치를 프로그래밍으로 교정"""
    from collections import defaultdict
    new_rows = []
    for row in rows:
        if row.get("row_type") != "주요혜택":
            new_rows.append(row)
            continue
        merchants = [m.strip() for m in str(row.get("target_merchants", "")).split(',') if m.strip()]
        known = {m: merchant_rate[m] for m in merchants if m in merchant_rate}
        if not known:
            new_rows.append(row)
            continue
        # 모든 가맹점이 같은 수치면 그대로
        if len(set(known.values())) <= 1:
            new_rows.append(row)
            continue
        # 수치가 다른 가맹점이 섞임 → 분리
        buckets = defaultdict(list)
        unknown = []
        for m in merchants:
            if m in known:
                buckets[known[m]].append(m)
            else:
                unknown.append(m)
        for (rate, type_), ms in sorted(buckets.items(), key=lambda x: -float(x[0][0])):
            nr = dict(row)
            nr["benefit_value"] = rate
            nr["benefit_type"] = "할인" if type_ == "할인" else "포인트"
            nr["target_merchants"] = ', '.join(ms)
            new_rows.append(nr)
        if unknown:
            nr = dict(row)
            nr["target_merchants"] = ', '.join(unknown)
            new_rows.append(nr)
    return new_rows


def html_to_text(html: str) -> str:
    if not html: return ""
    soup = BeautifulSoup(html, "html.parser")
    lines, seen = [], set()
    for elem in soup.find_all(["h5", "p", "li", "tr"]):
        if elem.name == "h5" and "tit04" in (elem.get("class") or []):
            text = elem.get_text(" ", strip=True)
            if text and text not in seen:
                seen.add(text)
                lines.append(f"[소제목] {text}")
        elif elem.name == "tr":
            cells = [c.get_text(" ", strip=True) for c in elem.find_all(["th", "td"])]
            cells = [c for c in cells if c]
            if not cells:
                continue
            if len(cells) == 1:
                row = cells[0]
            elif len(cells) == 2:
                row = f"{cells[0]}: {cells[1]}"
            else:
                row = f"{cells[0]}: {', '.join(cells[1:])}"
            if row and row not in seen:
                seen.add(row)
                lines.append(row)
        elif elem.name in ["p", "li"]:
            if elem.find_parent(["table"]): continue
            text = elem.get_text(" ", strip=True)
            if text and len(text) > 2 and text not in seen:
                seen.add(text)
                lines.append(text)
    return "\n".join(lines)


def parse_fee_notes(fee_html: str) -> str:
    if not fee_html: return ""
    soup = BeautifulSoup(fee_html, "html.parser")

    for table in soup.find_all("table"):
        caption = table.find("caption")
        if caption and "가족" in caption.get_text():
            parent = table.find_parent("div")
            if parent: parent.decompose()
            else: table.decompose()

    for h4 in soup.find_all("h4"):
        if "가족" in h4.get_text():
            parent = h4.find_parent("div", class_="indv")
            if parent: parent.decompose()

    notes = []
    for span in soup.find_all("span", class_=["alert_s_new", "attention_s"]):
        text = span.get_text(" ", strip=True)
        if text:
            notes.append(text)
    return " / ".join(notes) if notes else ""


def build_ui_from_html(tab_name: str, raw_html: str) -> tuple[str, str]:
    if not raw_html:
        return tab_name, ""

    soup = BeautifulSoup(raw_html, "html.parser")
    lines, seen = [], set()

    for elem in soup.find_all(["h5", "table", "p", "li"]):
        if elem.name == "h5" and "tit04" in (elem.get("class") or []):
            text = elem.get_text(" ", strip=True)
            if text and text not in seen:
                seen.add(text)
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(f"[{text}]")

        elif elem.name == "table":
            if elem.find_parent("table"): continue
            for caption in elem.find_all("caption"):
                caption.decompose()
            rows_html = []
            for tr in elem.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if not cells: continue
                cells_html = []
                for cell in cells:
                    tag     = cell.name
                    colspan = f' colspan="{cell.get("colspan")}"' if cell.get("colspan") else ""
                    rowspan = f' rowspan="{cell.get("rowspan")}"' if cell.get("rowspan") else ""
                    text    = cell.get_text(" ", strip=True)
                    cells_html.append(f'<{tag}{colspan}{rowspan}>{text}</{tag}>')
                rows_html.append(f'<tr>{"".join(cells_html)}</tr>')
            if rows_html:
                table_html = f'<table class="benefit-table">{"".join(rows_html)}</table>'
                if table_html not in seen:
                    seen.add(table_html)
                    lines.append(table_html)

        elif elem.name in ["p", "li"]:
            if elem.find_parent(["table"]): continue
            text = elem.get_text(" ", strip=True)
            if text and len(text) > 2 and text not in seen:
                seen.add(text)
                lines.append(text)

    return tab_name, "\n".join(lines)


def format_date(value: str) -> str:
    v = (value or "").split("-")[0]
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}" if len(v) >= 8 else ""


async def crawl_card(page, card, session):
    await goto_and_wait(page, card["page_url"],
        "() => { try { return !!(window.__NUXT__?.data?.[0]?.wcms); } catch(e) { return false; } }")

    data = await get_nuxt_data(page)
    if not data or not isinstance(data, dict):
        print(f"  [{card['card_id']}] __NUXT__ 데이터 없음")
        return None

    detail = data.get("wcms", {}).get("detail", {})
    if not detail:
        print(f"  [{card['card_id']}] detail 데이터 없음")
        return None

    sell_start_dt = ""
    try:
        span = page.locator("#sellStrtdt")
        if await span.count() > 0:
            sell_start_dt = (await span.inner_text()).strip()
    except Exception as e:
        print(f"  출시일자 추출 실패: {e}")

    async def fetch_bubble(item):
        path = item.get("serviceUrl", "")
        if not path: return None
        url = path if path.startswith("http") else f"{STATIC}{path}"
        try:
            async with session.get(url) as r:
                if r.status == 200:
                    type_code = item.get("typeCode", "")
                    tab_nm    = item.get("tabName", "")
                    # 서비스 탭은 typeCode와 무관하게 반드시 포함
                    is_info = (
                        not is_service_tab(tab_nm)
                        and (
                            item.get("hideSummaryTab", False)
                            or type_code in ("006", "007")
                            or (type_code not in BENEFIT_TYPECODES and type_code != "")
                            or (type_code == "" and is_info_by_tab_name(tab_nm))
                        )
                    )
                    # ↓ fetch_html_part()와 동일하게 인코딩 처리
                    raw = await r.read()
                    try:
                        html = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        html = raw.decode("euc-kr", errors="replace")

                    return {
                        "tab_name":    item.get("tabName", ""),
                        "type_code":   type_code,
                        "detail_text": html_to_text(html),
                        "raw_html":    html,
                        "is_info_tab": is_info,
                    }
        except Exception as e:
            print(f"  bubble fetch 실패 [{item.get('tabName', '')}]: {e}")
            return None

    async def fetch_html_part(key, path):
        if not path: return key, ""
        url = path if path.startswith("http") else f"{STATIC}{path}"
        try:
            async with session.get(url) as r:
                if r.status == 200:
                    raw = await r.read()
                    try:
                        text = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        text = raw.decode("euc-kr", errors="replace")
                    return key, text
        except Exception as e:
            print(f"  html_part fetch 실패 [{key}]: {e}")
        return key, ""

    async def fetch_event(banner):
        path = banner.get("evtUrl", "")
        if not path: return None
        url = path if path.startswith("http") else f"{STATIC}{path}"
        try:
            async with session.get(url) as r:
                if r.status == 200:
                    raw = await r.read()
                    try:
                        html = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        html = raw.decode("euc-kr", errors="replace")
                    return {
                        "id":    banner.get("id", ""),
                        "title": banner.get("evtTitle", ""),
                        "url":   url,
                        "start": banner.get("sDate", ""),
                        "end":   banner.get("eDate", ""),
                        "html":  html,
                    }
        except Exception as e:
            print(f"  event fetch 실패: {e}")
        return None

    # FIX 6: bannerList isinstance 체크 추가
    card_banners = [b for b in (data.get("bannerList") or [])
                    if isinstance(b, dict) and b.get("code") == card["card_id"]]

    bubble_results, html_results, event_results = await asyncio.gather(
        asyncio.gather(*[fetch_bubble(item) for item in (detail.get("bubble") or [])]),
        asyncio.gather(*[fetch_html_part(k, v) for k, v in (detail.get("htmlList") or {}).items()]),
        asyncio.gather(*[fetch_event(b) for b in card_banners]),
    )

    return {
        "card_id":    card["card_id"],
        "card_name":  re.sub(r"<[^>]+>", "", detail.get("cardTitle", "")).strip(),
        "ksp":        [k.get("title", "") if isinstance(k, dict) else k for k in (detail.get("ksp") or [])],
        "bubbles":    [r for r in bubble_results if r],
        "html_parts": {k: v for k, v in html_results if v},
        "events":     [r for r in event_results if r],
        "image_url":  STATIC + (detail.get("imgInfo") or {}).get("pcImg1", ""),
        "sell_start_dt": sell_start_dt,
    }

# =============================================
# Claude API
# =============================================

async def call_claude(prompt: str, session: aiohttp.ClientSession) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
    async with session.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 16000,
            "messages":   [{"role": "user", "content": prompt}],
        }
    ) as resp:
        result = await resp.json()
        if "content" not in result:
            raise RuntimeError(f"API 오류: {result}")
        return result["content"][0]["text"]


def safe_json(text: str):
    text = re.sub(r"```json|```", "", text).strip()
    # 1차 시도: 전체 파싱
    try:
        return json.loads(text)
    except Exception:
        pass
    # 2차 시도: 첫 번째 JSON 배열만 추출
    try:
        m = re.search(r'\[.*\]', text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    # 3차 시도: 첫 번째 JSON 객체만 추출
    try:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            result = json.loads(m.group())
            return [result] if isinstance(result, dict) else result
    except Exception as e:
        print(f"  JSON 파싱 실패: {e}")
    return []

# =============================================
# Step 3: 파싱
# =============================================

def _parse_annual_fee(fee_html: str) -> dict:
    soup   = BeautifulSoup(fee_html, "html.parser")
    result = {"dom": 0, "for": 0}

    def _to_int(text):
        text = text.replace(",", "").replace("원", "").replace("무료", "0").strip()
        m = re.search(r"\d+", text)
        return int(m.group()) if m else 0

    for table in soup.find_all("table"):
        caption = table.find("caption")
        if caption and "가족" in caption.get_text():
            continue
        for tr in table.find_all("tr"):
            th = tr.find("th")
            if not th or ("총 연회비" not in th.get_text() and "총연회비" not in th.get_text()):
                continue
            tds = tr.find_all("td")
            if not tds:
                continue
            if len(tds) >= 2:
                result["for"] = _to_int(tds[0].get_text())
                result["dom"] = _to_int(tds[1].get_text())
            else:
                v = _to_int(tds[0].get_text())
                result["for"] = result["dom"] = v
            return result
    return result


def _parse_network(fee_html: str) -> str:
    text = BeautifulSoup(fee_html, "html.parser").get_text()
    networks = []
    if "Mastercard" in text or "마스터" in text:
        networks.append("Mastercard")
    if "VISA" in text or "비자" in text:
        networks.append("VISA")
    if "AMEX" in text or "아멕스" in text:
        networks.append("AMEX")
    if not networks:
        networks.append("Mastercard" if "해외겸용" in text else "Local")
    return ",".join(networks)


def parse_info(card_data: dict, min_performance=0, has_cashback=False) -> dict:
    card_id    = card_data["card_id"]
    card_name  = card_data["card_name"]
    fee_html   = card_data["html_parts"].get("feeUrl", "")
    fee_text   = BeautifulSoup(fee_html, "html.parser").get_text() if fee_html else ""
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if card_id.startswith("ABP") or "체크" in card_name:
        card_type = "체크"
    elif card_id.startswith("ACP"):
        card_type = "신용"
    elif "하이브리드" in card_name:
        card_type = "하이브리드"
    else:
        card_type = "신용"

    fees = _parse_annual_fee(fee_html) if fee_html else {"dom": 0, "for": 0}
    _, fee_content = build_ui_from_html("연회비", fee_html)

    return {
        "card_id":                card_id,
        "company":                "삼성",
        "card_name":              card_name,
        "card_type":              card_type,
        "network":                _parse_network(fee_html) if fee_html else "Local",
        "is_domestic_foreign":    "true" if "해외겸용" in fee_text else "false",
        "has_transport":          "true" if "후불교통" in fee_text else "false",
        "annual_fee_dom_basic":   fees["dom"],
        "annual_fee_dom_premium": 0,
        "annual_fee_for_basic":   fees["for"],
        "annual_fee_for_premium": 0,
        "annual_fee_notes":       parse_fee_notes(fee_html),
        "min_performance":        min_performance,
        "summary":                " | ".join(card_data.get("ksp", [])),
        "image_url":              card_data.get("image_url", ""),
        "link_url":               f"{DETAIL_URL}?code={card_id}",
        "has_cashback":           str(has_cashback).lower(),
        "fee_content":            fee_content,
        "updated_at":             updated_at,
    }


# FIX 3: performance_min 타입 안전 변환 헬퍼
def _to_int_safe(val) -> int | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        return int(str(val).strip())
    except Exception:
        return None


async def parse_benefits(card_data: dict, session: aiohttp.ClientSession) -> list:
    updated_at      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    benefits        = []
    benefit_counter = 0
    ksp_text        = "\n".join(f"- {k}" for k in card_data["ksp"])

    # 패키지 관련 탭을 하나로 병합: "패키지" 키워드를 가진 비안내 탭끼리 묶음
    # 첫 번째 탭이 대표, 나머지는 merged_into 표시
    package_tabs = [
        b for b in card_data["bubbles"]
        if not b.get("is_info_tab") and "패키지" in b.get("tab_name", "")
    ]
    merged_tab_names = set()
    if len(package_tabs) > 1:
        primary = package_tabs[0]
        extra_content = "\n\n".join(
            f"[{t['tab_name']}]\n{t['detail_text']}"
            for t in package_tabs[1:]
        )
        primary["detail_text"] = primary["detail_text"] + "\n\n" + extra_content
        merged_tab_names = {t["tab_name"] for t in package_tabs[1:]}

    # 중복 탭명 추적: 같은 이름의 탭이 여럿이면 Claude에게 전달 시 번호를 붙여 구분
    _tab_name_seen: dict = {}

    for b in card_data["bubbles"]:
        # 안내탭 또는 병합된 탭 건너뜀
        if b.get("is_info_tab") or b.get("tab_name") in merged_tab_names:
            continue

        tab_name = b.get("tab_name", "")
        # 중복 탭명 처리: Claude가 동일 이름 탭을 하나로 취급하지 않도록 내용 기반 접미사 부여
        _tab_name_seen[tab_name] = _tab_name_seen.get(tab_name, 0) + 1
        if _tab_name_seen[tab_name] > 1:
            _detail = (b.get("detail_text", "") or "")
            if any(kw in _detail for kw in ["홈페이지", "앱을 통해", "온라인 가맹점", "앱 결제"]):
                tab_name = f"{tab_name} (온라인)"
            elif any(kw in _detail for kw in ["현장", "오프라인"]):
                tab_name = f"{tab_name} (오프라인)"
            else:
                tab_name = f"{tab_name} ({_tab_name_seen[tab_name]})"
        ui_title, ui_content = build_ui_from_html(tab_name, b["raw_html"])

        # 서비스 탭: Claude 없이 코드에서 직접 서비스 행 생성
        if is_service_tab(tab_name):
            svc_category = infer_service_tab_category(tab_name)
            benefit_counter += 1
            benefits.append({
                "benefit_id":           f"{card_data['card_id']}_B{benefit_counter:04d}",
                "card_id":              card_data["card_id"],
                "row_type":             "주요혜택",
                "benefit_group":        tab_name,
                "benefit_title":        tab_name,
                "category":             svc_category,
                "category_id":          str(CATEGORY_MAP.get(svc_category, "")),
                "on_offline":           "",
                "benefit_type":         "서비스",
                "benefit_value":        "",
                "benefit_unit":         "",
                "target_merchants":     "",
                "performance_level":    "",
                "performance_min":      "",
                "performance_max":      "",
                "min_amount":           "",
                "unit_amount":          "",
                "max_count":            "",
                "max_limit":            "",
                "max_limit_unit":       "",
                "group_max_limit":      "",
                "group_max_limit_unit": "",
                "updated_at":           updated_at,
                "ui_title":             tab_name,
                "ui_content":           ui_content,
            })
            continue

        bubble_content_str = f"[{tab_name}]\n{b['detail_text']}"

        # 전월 이용금액 산정 제외 목록 제거 (한 줄 단위, DOTALL 없이)
        # 각 탭 유의사항에 카드 전체 혜택이 나열되어 Claude가 다른 탭 혜택을 잘못 파싱하는 문제 방지
        bubble_content_str = re.sub(
            r'전월 이용금액 산정 시,.+',
            '전월 이용금액 산정 시 일부 항목 제외',
            bubble_content_str,
        )

        # 패키지 탭: 프로그래밍으로 요약을 추출해서 Claude에게 먼저 제공
        if "패키지" in tab_name:
            # debug: raw HTML 저장 (테이블 형식 확인용)
            safe_tab = re.sub(r'[\\/:*?"<>|]', '_', tab_name)
            debug_path = DEBUG_DIR / f"{card_data['card_id']}_{safe_tab}.html"
            debug_path.write_text(b.get('raw_html', ''), encoding='utf-8')

            pkg_summary = extract_package_summary(b['detail_text'], b.get('raw_html', ''))
            print(f"  [패키지 요약]\n{pkg_summary}")
            if pkg_summary:
                bubble_content_str = pkg_summary + "\n" + bubble_content_str

        # Claude API 호출 - detail_text 사용 (최대 3회 재시도)
        _prompt = BENEFIT_PROMPT.format(
            card_id        = card_data["card_id"],
            card_name      = card_data["card_name"],
            ksp            = ksp_text,
            bubble_content = bubble_content_str,
        )
        rows = []
        _retry_hint = ""
        for _attempt in range(3):
            _cur_prompt = _prompt + _retry_hint
            raw = await call_claude(_cur_prompt, session)
            rows = safe_json(raw)
            if not isinstance(rows, list):
                continue
            # 전월실적 구간이 표에 2개 이상 있는데 파싱 결과에 1개만 있으면 재시도
            _pm_vals = [str(r.get("performance_min","")).strip() for r in rows if str(r.get("performance_min","")).strip() not in ("","0")]
            _unique_pm = set(_pm_vals)
            _has_multi_pm_text = ("만원 이상" in bubble_content_str and
                                  bubble_content_str.count("만원 이상") >= 2)
            if _has_multi_pm_text and len(_unique_pm) < 2:
                # 누락된 pm 구간 텍스트에서 추출해서 힌트 추가
                import re as _re2
                _pm_matches = _re2.findall(r'(\d+)만원 이상', bubble_content_str)
                _pm_hints = sorted(set(int(m)*10000 for m in _pm_matches))
                _found = sorted(int(p) for p in _unique_pm if p.isdigit())
                _missing = [p for p in _pm_hints if p not in _found]
                _retry_hint = (
                    f"\n\n[중요 재시도 지시] 이전 파싱에서 performance_min={_found} 구간만 포함됐습니다. "
                    f"표에 {[f'{p//10000}만원 이상' for p in _pm_hints]} 구간이 모두 있으므로 "
                    f"누락된 performance_min={_missing} 구간 행을 반드시 포함해주세요."
                )
                print(f"  [재시도 {_attempt+1}] 탭='{tab_name}' pm누락={_missing} → 힌트 추가 후 재시도")
                continue
            break
        else:
            print(f"  [경고] '{tab_name}' 3회 재시도 후에도 실적구간 누락")

        if not isinstance(rows, list):
            continue

        # ui_title과 benefit_value/benefit_type 불일치 교정 (모든 탭)
        rows = _fix_ui_title_consistency(rows)
        # 가맹점 없는 행 제거 (Claude 환각 방지)
        rows = _remove_empty_merchant_rows(rows)

        # 패키지 탭: Claude가 잘못 합친 가맹점/수치를 코드로 교정
        if "패키지" in tab_name:
            merchant_rate = get_package_merchant_rates(b['detail_text'], b.get('raw_html', ''))
            if merchant_rate:
                rows = _fix_package_rows(rows, merchant_rate)

        for row in rows:
            row_type = row.get("row_type", "안내")

            if row_type == "주요혜택":
                # 발급월 혜택은 별도 행 생성 안 함 (ui_content에만 포함)
                if "발급월" in str(row.get("performance_level", "")):
                    continue
                benefit_counter += 1

                category = row.get("category", "")
                category_ids = ",".join(
                    str(CATEGORY_MAP[c.strip()])
                    for c in category.split(",")
                    if c.strip() in CATEGORY_MAP
                )

                benefits.append({
                    "benefit_id":           f"{card_data['card_id']}_B{benefit_counter:04d}",
                    "card_id":              card_data["card_id"],
                    "row_type":             "주요혜택",
                    "benefit_group":        row.get("benefit_group", tab_name),
                    "benefit_title":        row.get("benefit_title", ""),
                    "category":             category,
                    "category_id":          category_ids,
                    "on_offline":           row.get("on_offline", ""),
                    "benefit_type":         row.get("benefit_type", ""),
                    "benefit_value":        row.get("benefit_value", ""),
                    "benefit_unit":         row.get("benefit_unit", ""),
                    "target_merchants":     row.get("target_merchants", ""),
                    "performance_level":    row.get("performance_level", ""),
                    "performance_min":      row.get("performance_min", ""),
                    "performance_max":      row.get("performance_max", ""),
                    "min_amount":           row.get("min_amount", ""),
                    "unit_amount":          row.get("unit_amount", ""),
                    "max_count":            row.get("max_count", ""),
                    "max_limit":            row.get("max_limit", ""),
                    "max_limit_unit":       row.get("max_limit_unit", ""),
                    "group_max_limit":      row.get("group_max_limit", ""),
                    "group_max_limit_unit": row.get("group_max_limit_unit", ""),
                    "updated_at":           updated_at,
                    "ui_title":             row.get("ui_title", "") or row.get("service_content", "") or b["tab_name"],
                    "ui_content":           ui_content,
                })


    # 머지 로직 - benefit_value/type 포함하여 수치가 다른 행은 합치지 않음
    merged = {}
    for b in benefits:
        key = (
            b.get("card_id", ""),
            b.get("benefit_group", ""),
            b.get("category", ""),
            b.get("performance_min", ""),
            b.get("performance_max", ""),
            b.get("max_limit", ""),
            b.get("benefit_value", ""),
            b.get("benefit_type", ""),
            b.get("on_offline", ""),  # 현장/온라인 다른 혜택은 별도 행 유지
        )
        if key in merged:
            existing = merged[key].get("target_merchants", "")
            new      = b.get("target_merchants", "")
            if new and new not in existing:
                merged[key]["target_merchants"] = f"{existing}, {new}"
        else:
            merged[key] = b

    benefits = list(merged.values())

    # 중복 탭명 구분용 접미사를 benefit_group에서 제거 (숫자·오프라인·온라인)
    import re as _re
    for _b in benefits:
        _bg = _b.get("benefit_group", "")
        _cleaned = _re.sub(r'\s*\((오프라인|온라인|\d+)\)$', '', _bg)
        if _cleaned != _bg:
            print(f"  [탭명 접미사 제거] benefit_group '{_bg}' → '{_cleaned}'")
            _b["benefit_group"] = _cleaned

    # 발급월 예외 행 제거 (performance_min=0/'' 이고 같은 그룹+카테고리에 performance_min>0 행 존재)
    benefits = _remove_issue_month_rows(benefits)

    # 유의사항 중복 행 제거: 다른 benefit_group에 동일한 (mc, bv, bu, bt)가 pm>0으로 존재하는데
    # 이 행은 pm='' → 유의사항에서 잘못 파싱된 중복 행으로 판단하여 제거
    # 같은 benefit_group 내의 pm 구간 차이는 정상이므로 제거하지 않음
    _mc_bv_pm_groups: dict = {}  # (mc,bv,bu,bt) → pm>0인 benefit_group 집합
    for _b in benefits:
        if _b.get("row_type") != "주요혜택":
            continue
        _pm = str(_b.get("performance_min", "") or "").strip()
        try:
            if int(_pm) > 0:
                _k = (
                    _b.get("target_merchants", ""),
                    str(_b.get("benefit_value", "")),
                    _b.get("benefit_unit", ""),
                    _b.get("benefit_type", ""),
                )
                _mc_bv_pm_groups.setdefault(_k, set()).add(_b.get("benefit_group", ""))
        except (ValueError, TypeError):
            pass
    _benefits_filtered = []
    for _b in benefits:
        if _b.get("row_type") == "주요혜택":
            _pm = str(_b.get("performance_min", "") or "").strip()
            if _pm in ("", "0"):
                _k = (
                    _b.get("target_merchants", ""),
                    str(_b.get("benefit_value", "")),
                    _b.get("benefit_unit", ""),
                    _b.get("benefit_type", ""),
                )
                _cur_grp = _b.get("benefit_group", "")
                _other_groups = _mc_bv_pm_groups.get(_k, set()) - {_cur_grp}
                if _other_groups:  # 다른 benefit_group에서만 pm>0 행이 있을 때 제거
                    print(f"  [유의사항 중복 제거] group='{_cur_grp}' mc={_b.get('target_merchants','')} bv={_b.get('benefit_value','')} pm없음 → 다른 그룹({_other_groups})에 pm>0 동일 행 존재")
                    continue
        _benefits_filtered.append(_b)
    benefits = _benefits_filtered

    # 가맹점 카테고리 강제 보정 (더플레이스→외식 등 Claude 분류 오류 보정)
    benefits = _apply_merchant_category_override(benefits)

    # 전 가맹점 행 카테고리 보정: target_merchants가 "국내외 가맹점" 등 전체 표현이면 → 기타
    _ALL_MC_KEYWORDS = ["국내외 가맹점", "모든 가맹점", "전 가맹점", "국내 모든 가맹점", "국내외 모든 가맹점"]
    for _b in benefits:
        if _b.get("row_type") != "주요혜택":
            continue
        _mc = _b.get("target_merchants", "")
        if any(_kw in _mc for _kw in _ALL_MC_KEYWORDS) and _b.get("category") != "기타":
            print(f"  [전가맹점 카테고리 보정] group='{_b.get('benefit_group','')}' {_b.get('category')} → 기타")
            _b["category"] = "기타"

    # 배율(배) 기반 중복 가맹점 제거: 같은 benefit_group+pm 내에서
    # 높은 배율 행에 있는 가맹점을 낮은 배율 행의 target_merchants에서 제거
    # 예) 올리브영이 2배 행과 5배 행 모두에 있으면 2배 행에서 올리브영 제거
    def _remove_higher_rate_merchants_from_lower(benefits: list) -> list:
        import re as _re
        def parse_bae(b: dict) -> float:
            bv = str(b.get("benefit_value", "")).strip()
            bu = str(b.get("benefit_unit", "")).strip()
            m = _re.match(r'^(\d+(?:\.\d+)?)배$', bv)
            if m:
                return float(m.group(1))
            if bu in ("배", "배수"):
                m2 = _re.match(r'^(\d+(?:\.\d+)?)$', bv)
                if m2:
                    return float(m2.group(1))
            return 0.0

        # benefit_group+pm별 배율 행 수집
        grp_bae: dict = {}
        for b in benefits:
            if b.get("row_type") != "주요혜택":
                continue
            rate = parse_bae(b)
            if rate <= 0:
                continue
            key = (b.get("benefit_group", ""), str(b.get("performance_min", "") or ""))
            grp_bae.setdefault(key, []).append((rate, b))

        for key, rate_rows in grp_bae.items():
            if len(rate_rows) <= 1:
                continue

            all_distinct = sorted(set(r for r, _ in rate_rows))

            # [1] 중간 배율 보정: min < rate < max인 배율은 파싱 오류 → min배율로 교정
            # 예) 2배~5배 탭에서 CGV 4배로 잘못 파싱 → 2배로 교정
            if len(all_distinct) >= 3:
                min_rate = all_distinct[0]
                max_rate = all_distinct[-1]
                min_int = int(min_rate) if min_rate == int(min_rate) else min_rate
                for rate, b in rate_rows:
                    if min_rate < rate < max_rate:
                        bv_raw = str(b.get("benefit_value", "")).strip()
                        if "배" in bv_raw:
                            b["benefit_value"] = f"{min_int}배"
                        else:
                            b["benefit_value"] = str(min_int)
                        print(f"  [중간배율 보정] group='{key[0]}' mc={b.get('target_merchants','')} {rate}배 → {min_rate}배")

            # [2] 보정 후 배율 재수집
            updated_rows = [(parse_bae(b), b) for _, b in rate_rows]
            valid_rows = [(r, b) for r, b in updated_rows if r > 0]
            if not valid_rows:
                continue
            max_rate_new = max(r for r, _ in valid_rows)

            # [3] 최대 배율 가맹점 집합 수집
            high_merchants: set = set()
            for rate, b in valid_rows:
                if rate == max_rate_new:
                    for m in re.split(r',\s*', b.get("target_merchants", "")):
                        if m.strip():
                            high_merchants.add(m.strip())

            # [4] 낮은 배율 행에서 해당 가맹점 제거
            for rate, b in valid_rows:
                if rate == max_rate_new:
                    continue
                mc = b.get("target_merchants", "")
                parts = [m.strip() for m in re.split(r',\s*', mc) if m.strip()]
                removed = [m for m in parts if m in high_merchants]
                if removed:
                    kept = [m for m in parts if m not in high_merchants]
                    print(f"  [배율중복 가맹점 제거] group='{key[0]}' {rate}배 행에서 {removed} 제거")
                    b["target_merchants"] = ", ".join(kept)
        return benefits

    benefits = _remove_higher_rate_merchants_from_lower(benefits)

    # 추가 적립 합산: 기본 적립률 + 추가 적립률 = 합산 적립률로 표기 (범용 가맹점 중복 행 제거 포함)
    benefits = _merge_extra_earn_totals(benefits)

    # max_limit → group_max_limit 보정:
    # 같은 benefit_group+performance_min에 2개 이상 카테고리가 모두 동일한 max_limit이면
    # 이는 통합 월 한도이므로 group_max_limit으로 전환 (Claude 파싱 오류 보정)
    grp_pm_limits: dict = defaultdict(list)
    for b in benefits:
        if b.get("row_type") == "주요혜택" and b.get("max_limit") and not b.get("group_max_limit"):
            grp = b.get("benefit_group", "")
            # 옵션서비스는 택1이므로 옵션 간 한도 공유 아님 → 보정 제외
            if "옵션서비스" in grp or "옵션 서비스" in grp:
                continue
            key = (grp, b.get("performance_min", ""))
            grp_pm_limits[key].append((b.get("category", ""), b.get("max_limit", ""), b.get("max_limit_unit", "")))
    for key, entries in grp_pm_limits.items():
        cats = {e[0] for e in entries}
        limits = {(e[1], e[2]) for e in entries}
        if len(cats) >= 2 and len(limits) == 1:
            limit_val, limit_unit = next(iter(limits))
            print(f"  [group_max_limit 보정] group='{key[0]}' pm={key[1]} → gml={limit_val}{limit_unit} ({len(cats)}개 카테고리 공유)")
            for b in benefits:
                if (b.get("benefit_group", ""), b.get("performance_min", "")) == key and b.get("max_limit") == limit_val:
                    b["group_max_limit"] = limit_val
                    b["group_max_limit_unit"] = limit_unit
                    b["max_limit"] = ""
                    b["max_limit_unit"] = ""

    # gml → ml 역변환: benefit_group+performance_min 내 주요혜택 행이 1개뿐인데 gml이 설정된 경우
    # 단일 카테고리에 통합 한도는 없으므로 ml로 전환
    grp_pm_rows: dict = defaultdict(list)
    for b in benefits:
        if b.get("row_type") == "주요혜택":
            key = (b.get("benefit_group", ""), b.get("performance_min", ""))
            grp_pm_rows[key].append(b)
    for key, grp_rows in grp_pm_rows.items():
        if len(grp_rows) == 1 and grp_rows[0].get("group_max_limit") and not grp_rows[0].get("max_limit"):
            b = grp_rows[0]
            print(f"  [gml→ml 변환] group='{key[0]}' pm={key[1]} gml={b['group_max_limit']} → ml")
            b["max_limit"] = b["group_max_limit"]
            b["max_limit_unit"] = b.get("group_max_limit_unit", "")
            b["group_max_limit"] = ""
            b["group_max_limit_unit"] = ""

    # gml + ml 동시 세팅 보정: Claude가 ml과 gml을 동시에 출력한 경우 gml 제거 (ml 우선)
    # 예) "연 12회" 횟수 제한을 gml=12로 잘못 출력 → ml은 정상이므로 gml만 제거
    for b in benefits:
        if b.get("group_max_limit") and b.get("max_limit"):
            print(f"  [gml+ml 동시세팅 보정] group='{b.get('benefit_group','')}' cat={b.get('category','')} gml={b['group_max_limit']} ml={b['max_limit']} → gml 제거")
            b["group_max_limit"] = ""
            b["group_max_limit_unit"] = ""

    # gml 실적구간 오탐 보정: gml 값이 해당 카드의 performance_min 값과 일치하는 경우 제거
    # ("N만원 이상"을 gml로 잘못 파싱한 케이스)
    _all_pm_vals: set = set()
    for b in benefits:
        pm_str = str(b.get("performance_min", "") or "").strip()
        try:
            _all_pm_vals.add(int(pm_str))
        except (ValueError, TypeError):
            pass
    for b in benefits:
        gml_val = b.get("group_max_limit", "")
        gml_unit = b.get("group_max_limit_unit", "")
        if not gml_val or gml_unit:
            continue
        try:
            gml_int = int(gml_val)
            if gml_int in _all_pm_vals and gml_int >= 10000:
                print(f"  [gml 실적구간 오탐 보정] group='{b.get('benefit_group','')}' gml={gml_val} → 실적구간값과 일치하여 제거")
                b["group_max_limit"] = ""
                b["group_max_limit_unit"] = ""
        except (ValueError, TypeError):
            pass

    # gml 횟수 오탐 보정: gml이 횟수(N회) 제한인 경우 제거 (max_count에 넣어야 하는 값)
    # - gml_unit이 "회" 포함인 경우
    # - gml_unit이 없고 gml < 100인 정수인 경우
    for b in benefits:
        gml_val = b.get("group_max_limit", "")
        gml_unit = b.get("group_max_limit_unit", "")
        if not gml_val:
            continue
        is_count = False
        if gml_unit and "회" in gml_unit:
            is_count = True
        elif not gml_unit:
            try:
                if int(gml_val) < 100:
                    is_count = True
            except (ValueError, TypeError):
                pass
        if is_count:
            print(f"  [gml 횟수오탐 보정] group='{b.get('benefit_group','')}' cat={b.get('category','')} gml={gml_val}{gml_unit} → 제거")
            b["group_max_limit"] = ""
            b["group_max_limit_unit"] = ""

    # group_max_limit 전파: benefit_group+performance_min 조합에서 하나라도 값이 있으면 전체에 전파
    group_limits = defaultdict(lambda: ("", ""))
    for b in benefits:
        if b.get("group_max_limit"):
            key = (b.get("benefit_group", ""), b.get("performance_min", ""))
            group_limits[key] = (
                b["group_max_limit"],
                b.get("group_max_limit_unit", ""),
            )
    for b in benefits:
        key = (b.get("benefit_group", ""), b.get("performance_min", ""))
        if key in group_limits:
            b["group_max_limit"], b["group_max_limit_unit"] = group_limits[key]
            b["max_limit"] = ""          # group_max_limit과 max_limit 동시 세팅 방지
            b["max_limit_unit"] = ""

    # max_limit 전파: benefit_group+performance_min 내에서 benefit_value가 동일한데
    # max_limit이 일부 행에만 있으면 전체에 전파 (Claude 불일치 보정)
    max_limits: dict = defaultdict(set)
    for b in benefits:
        if b.get("max_limit"):
            key = (b.get("benefit_group", ""), b.get("benefit_value", ""), b.get("performance_min", ""))
            max_limits[key].add((str(b["max_limit"]), b.get("max_limit_unit", "")))
    for b in benefits:
        key = (b.get("benefit_group", ""), b.get("benefit_value", ""), b.get("performance_min", ""))
        if key in max_limits and not b.get("max_limit") and not b.get("group_max_limit"):
            vals = max_limits[key]
            if len(vals) == 1:  # 동일한 한도 값 하나만 존재할 때만 전파
                limit, unit = next(iter(vals))
                b["max_limit"] = limit
                b["max_limit_unit"] = unit

    # 이하/초과 구조 min_amount 보정:
    # 같은 benefit_group+target_merchants+benefit_unit+benefit_type에서
    # 두 행이 동일한 min_amount를 가지면서 benefit_value가 다른 경우
    # → 낮은 bv 행이 "이하" 케이스이므로 min_amount를 제거
    # (예: 8500원 이하 1500원 할인 / 8500원 초과 3000원 할인)
    _ma_grp: dict = {}
    for _b in benefits:
        if _b.get("row_type") != "주요혜택":
            continue
        _ma = str(_b.get("min_amount", "") or "")
        if not _ma:
            continue
        _key = (
            _b.get("benefit_group", ""),
            _b.get("target_merchants", ""),
            _b.get("benefit_unit", ""),
            _b.get("benefit_type", ""),
            _ma,
            str(_b.get("performance_min", "") or ""),  # pm 구간이 다른 행은 이하/초과로 오파악하지 않음
        )
        try:
            _bv_num = float(str(_b.get("benefit_value", "") or 0))
        except (ValueError, TypeError):
            continue
        _ma_grp.setdefault(_key, []).append((_bv_num, _b))
    for _key, _bv_rows in _ma_grp.items():
        if len(_bv_rows) < 2:
            continue
        _bv_rows.sort(key=lambda x: x[0])
        _min_bv, _min_b = _bv_rows[0]
        _max_bv = _bv_rows[-1][0]
        if _min_bv != _max_bv:
            print(f"  [이하/초과 min_amount 보정] group='{_key[0]}' mc={_key[1]} ma={_key[4]} bv={_min_bv}→min_amount 제거 (이하 케이스)")
            _min_b["min_amount"] = ""

    # benefit_id 재부여
    for i, b in enumerate(benefits, 1):
        b["benefit_id"] = f"{b['card_id']}_B{i:04d}"

    return benefits


def parse_notices(card_data: dict) -> list:
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    part_labels = {
        "noticeUrl":     "필수 안내 사항",
        "addServiceUrl": "부가서비스 변경 가능 사유",
        "etcUrl":        "기타 안내 사항",
    }

    all_sections = []

    def extract_li_text(li) -> str:
        parts = []
        for node in li.children:
            if hasattr(node, 'get_text'):
                text = node.get_text(" ", strip=True)
            else:
                text = str(node).strip()
            if text:
                parts.append(text)
        return " ".join(parts).strip()

    for key, section_title in part_labels.items():
        html = card_data["html_parts"].get(key, "")
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        lines = []
        seen = set()

        # notice-wrap 구조 (필수 안내 사항)
        notice_wraps = soup.find_all("div", class_="notice-wrap")
        if notice_wraps:
            for wrap in notice_wraps:
                for li in wrap.find_all("li"):
                    if li.find_parent("li"):
                        continue
                    text = extract_li_text(li)

                    if "카드 출시일자" in text:
                        sell_dt = card_data.get("sell_start_dt", "")
                        if sell_dt:
                            text = f"카드 출시일자 : {sell_dt}"
                        else:
                            continue

                    if text and len(text) > 2 and text not in seen:
                        seen.add(text)
                        lines.append(text)

        # 아코디언 구조 (부가서비스 변경 가능 사유, 기타 안내 사항)
        else:
            for li in soup.find_all("li"):
                if li.find_parent("li"):
                    continue
                text = extract_li_text(li)
                if text and len(text) > 2 and text not in seen:
                    seen.add(text)
                    lines.append(text)

            # FIX 7: li를 포함한 p는 스킵 (중복 방지)
            for p in soup.find_all("p"):
                if p.find("li"):
                    continue
                text = p.get_text(" ", strip=True)
                if text and len(text) > 2 and text not in seen:
                    seen.add(text)
                    lines.append(text)

            # 구조 태그가 없는 순수 텍스트 폴백 (etcUrl 등)
            if not lines:
                raw_text = soup.get_text("\n", strip=True)
                for line in raw_text.splitlines():
                    line = line.strip()
                    if line and len(line) > 2 and line not in seen:
                        seen.add(line)
                        lines.append(line)

        if lines:
            all_sections.append(f"[{section_title}]\n" + "\n".join(lines))

    if not all_sections:
        return []

    return [{
        "notice_id":      f"{card_data['card_id']}_N0001",
        "card_id":        card_data["card_id"],
        "notice_content": "\n\n".join(all_sections),
        "updated_at":     updated_at,
    }]


def parse_events(card_data: dict) -> list:
    updated_at    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event_counter = 0
    all_rows      = []

    def _infer_event_type(text: str) -> str:
        if "캐시백" in text: return "캐시백"
        if "포인트" in text: return "포인트"
        if "마일리지" in text or "마일" in text: return "마일리지"
        if "할인" in text: return "할인"
        if "서비스" in text: return "서비스"
        return "기타"

    for event in card_data.get("events", []):
        event_counter += 1
        event_id = f"{card_data['card_id']}_E{event_counter:04d}"
        html = event.get("html", "")
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        title_elem  = soup.find("span", class_="event_titie")
        event_title = title_elem.get_text(" ", strip=True) if title_elem else event.get("title", "")

        sections        = []
        current_section = ""
        current_lines   = []
        seen            = set()

        for elem in soup.find_all(["p", "li"]):
            if elem.name == "p":
                strong = elem.find("strong")
                if strong:
                    if current_lines:
                        sections.append((current_section, "\n".join(current_lines)))
                        current_lines = []
                        seen = set()
                    section_text    = strong.get_text(" ", strip=True)
                    current_section = "확인사항" if "꼭 확인하세요" in section_text else section_text
                continue

            if elem.find_parent("li"): continue

            strong = elem.find("strong", class_="e_tit")
            if strong:
                if current_lines:
                    sections.append((current_section, "\n".join(current_lines)))
                    current_lines = []
                    seen = set()
                section_text    = strong.get_text(" ", strip=True)
                current_section = "확인사항" if "꼭 확인하세요" in section_text else section_text
                strong.decompose()

            nested_texts = []
            for nested_li in elem.find_all("li"):
                text = nested_li.get_text(" ", strip=True)
                if text:
                    nested_texts.append(text)

            for ul in elem.find_all(["ul", "ol"]):
                ul.extract()
            top_text = elem.get_text(" ", strip=True)
            if top_text and top_text not in seen:
                seen.add(top_text)
                current_lines.append(top_text)

            for text in nested_texts:
                if text not in seen:
                    seen.add(text)
                    current_lines.append(text)

        if current_lines:
            sections.append((current_section, "\n".join(current_lines)))

        if not sections:
            text = "\n".join(
                elem.get_text(" ", strip=True)
                for elem in soup.find_all(["p", "li"])
                if elem.get_text(" ", strip=True) and len(elem.get_text(" ", strip=True)) > 1
            )
            if text:
                sections = [("혜택", text)]

        for section_name, content in sections:
            if not content.strip():
                continue
            all_rows.append({
                "event_id":          event_id,
                "card_id":           card_data["card_id"],
                "company":           "삼성",
                "card_name":         card_data["card_name"],
                "origin_event_code": event["id"],
                "event_title":       event_title,
                "event_link":        event["url"],
                "start_date":        format_date(event["start"]),
                "end_date":          format_date(event["end"]),
                "event_type":        _infer_event_type(content),
                "section":           section_name,
                "event_content":     content,
                "updated_at":        updated_at,
            })

    return all_rows


async def parse_and_save(card_data: dict, session: aiohttp.ClientSession):
    remove_card_from_csv(card_data["card_id"])
    benefits = await parse_benefits(card_data, session)
    save_csv("benefit", benefits)

    # FIX 3: performance_min 타입 안전 변환
    perf_values = [
        _to_int_safe(b.get("performance_min"))
        for b in benefits
        if _to_int_safe(b.get("performance_min")) is not None
    ]
    min_performance = min(perf_values) if perf_values else 0
    has_cashback    = any(b.get("benefit_type") == "캐시백" for b in benefits)

    info = parse_info(card_data, min_performance, has_cashback)
    save_csv("info", [info])

    notices = parse_notices(card_data)
    save_csv("notice", notices)

    events = parse_events(card_data)
    save_csv("event", events)
    save_events(events)

    print(f"  [완료] 혜택:{len(benefits)}행 / 유의사항:{len(notices)}행 / 이벤트:{len(events)}행")

# =============================================
# 메인
# =============================================

async def run(force_all=False, target_id=None):
    print("=" * 50)
    print("삼성카드 자동 크롤링 + AI 파싱 시작")
    print("=" * 50)

    init_csv(reset=force_all)

    async with aiohttp.ClientSession(headers={
        "User-Agent": USER_AGENT,
        "Referer":    SAMSUNG,
    }) as session:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            ctx     = await browser.new_context(user_agent=USER_AGENT, locale="ko-KR")
            page    = await ctx.new_page()

            try:
                all_cards = await get_card_list(page)
            except Exception as e:
                print(f"카드 목록 수집 실패: {e}")
                await browser.close()
                return

            existing = load_cards()
            print(f"기존: {len(existing)}개 / 웹사이트: {len(all_cards)}개")

            if target_id:
                targets = []
                for cid in target_id:
                    if cid in existing:
                        print(f"  [{cid}] 이미 수집된 카드 - 재수집하려면 --all 사용")
                    found = [c for c in all_cards if c["card_id"] == cid]
                    if found:
                        targets.extend(found)
                    else:
                        targets.append({"card_id": cid, "card_name": "", "page_url": f"{DETAIL_URL}?code={cid}"})
            elif force_all:
                targets = all_cards
            else:
                targets = [c for c in all_cards if c["card_id"] not in existing]
                if not targets:
                    print("새 카드 없음. 종료.")
                    save_cards({**existing, **{c["card_id"]: c for c in all_cards}})
                    await browser.close()
                    return
                print(f"🆕 새 카드 {len(targets)}개: {[c['card_id'] for c in targets]}")

            success = fail = 0
            new_infos = {}

            for card in targets:
                card_id = card["card_id"]
                print(f"\n[{card_id}] 크롤링 중...")

                card_data = await crawl_card(page, card, session)
                if not card_data:
                    fail += 1
                    continue

                print(f"  [{card_id}] AI 파싱 중... (bubble {len(card_data['bubbles'])}개)")
                try:
                    await parse_and_save(card_data, session)
                    new_infos[card_id] = {
                        "card_id":   card_id,
                        "card_name": card_data["card_name"],
                        "page_url":  card["page_url"],
                    }
                    print(f"  [OK] {card_data['card_name']}")
                    success += 1
                except Exception as e:
                    print(f"  [실패] 파싱 실패: {e}")
                    fail += 1

                await asyncio.sleep(1.0)

            save_cards({**existing, **{c["card_id"]: c for c in all_cards}, **new_infos})
            await browser.close()

    print(f"\n완료 | 성공: {success} / 실패: {fail}")
    print(f"CSV 위치: {CSV_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all",     action="store_true")
    parser.add_argument("--card_id", nargs="+", default=None)
    args = parser.parse_args()
    asyncio.run(run(force_all=args.all, target_id=args.card_id))