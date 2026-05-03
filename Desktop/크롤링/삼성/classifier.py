"""
classifier.py - 삼성카드 혜택 텍스트 분류 유틸
  - 카테고리 / 혜택유형 / 지역 / 금액 추출
"""

import re
from config import CATEGORY_DATA


# ── 카테고리 분류 ─────────────────────────────────────────────

def get_category_info(text: str) -> tuple[str, str, str]:
    target_merchants = []
    category_ids     = []
    categories       = []

    for item in CATEGORY_DATA:
        matched = [m for m in item.get("category_list", []) if m and m in text]
        if matched:
            for m in matched:
                if m not in target_merchants:
                    target_merchants.append(m)
            cat_id = str(item.get("category_id", ""))
            cat    = item.get("category_name", "")
            if cat_id and cat_id not in category_ids:
                category_ids.append(cat_id)
                categories.append(cat)

    return ",".join(target_merchants), ", ".join(category_ids), ", ".join(categories)


# ── 금액/비율 추출 ────────────────────────────────────────────

def find_amounts(text: str) -> list[dict]:
    """텍스트에서 금액·퍼센트·포인트 파싱"""
    if not text:
        return []
    items = []
    for m in re.finditer(r"(\d[\d,]*)\s*(만원|원|%|포인트|마일리지)", text):
        raw      = int(m.group(1).replace(",", ""))
        src_unit = m.group(2)
        items.append({
            "start": m.start(),
            "text":  m.group(0),
            "unit":  "원" if src_unit in ["만원", "원"] else src_unit,
            "value": raw * 10000 if src_unit == "만원" else raw,
        })
    return items


def get_unit_value(text: str) -> tuple[str, str]:
    """첫 번째 금액의 (unit, value) 반환"""
    amounts = find_amounts(text)
    if not amounts:
        return "", ""
    return amounts[0]["unit"], amounts[0]["value"]


def get_max_limit(text: str) -> str:
    """월 할인/적립 최대값 추출"""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ("월" in line and "할인" in line) or "적립" in line:
            amounts = find_amounts(line)
            if amounts:
                return amounts[-1]["value"]
    return ""


# ── 지역 분류 ─────────────────────────────────────────────────

def get_region(text: str) -> str:
    has_domestic = "국내" in text
    has_global   = "해외" in text
    if has_domestic and has_global:
        return "둘다"
    if has_global:
        return "해외"
    return "국내"


# ── 혜택 유형 분류 ────────────────────────────────────────────

def get_benefit_type(text: str) -> str:
    items = [
        ("할인",       "할인"),
        ("포인트적립", "포인트적립"),
        ("포인트 적립","포인트적립"),
        ("마일리지적립","마일리지적립"),
        ("마일리지 적립","마일리지적립"),
        ("캐시백",     "캐시백"),
        ("서비스",     "서비스"),
    ]
    found = [(text.find(kw), val) for kw, val in items if text.find(kw) >= 0]
    if not found:
        return ""
    found.sort(key=lambda x: x[0])
    return found[0][1]


# ── 혜택 요약 생성 ────────────────────────────────────────────

def _clean_summary_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'^\s*[①-⑳]\s*', '', text)
    text = re.sub(r'^\s*[A-Z]\.\s*', '', text)
    text = re.sub(r'^\s*\d+\.\s*', '', text)
    text = re.sub(r'\b[A-Z]\.\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _is_bad_summary_line(text: str) -> bool:
    if not text:
        return True
    if "|" in text or ":" in text:
        return True
    if "전월" in text and "이용금액" in text:
        return True
    return False


def get_benefit_summary(text: str) -> str:
    for line in text.splitlines():
        line = _clean_summary_text(line)
        if not line:
            continue
        if len(line) <= 60 and find_amounts(line) and "할인" in line and not _is_bad_summary_line(line):
            return line[:120]
    return _clean_summary_text(text)[:120]


# ── 이벤트 분류 ───────────────────────────────────────────────

def classify_evt_type(text: str) -> str:
    text = (text or "").lower()
    if "캐시백" in text or "cashback" in text:
        return "캐시백"
    if "포인트" in text or "point" in text or "마일리지" in text:
        return "포인트"
    if "할인" in text:
        return "할인"
    if "무료" in text or "면제" in text or "제공" in text or "혜택" in text:
        return "서비스"
    return "기타"


def format_event_date(value: str) -> str:
    value = (value or "").split("-")[0]
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}" if len(value) == 8 else ""


def extract_min_amount(text: str):
    if m := re.search(r"건당\s*(\d+)만원\s*이상", text):
        return int(m.group(1)) * 10000
    if m := re.search(r"건당\s*(\d+)천원\s*이상", text):
        return int(m.group(1)) * 1000
    if m := re.search(r"건당\s*(\d+,?\d*)\s*원\s*이상", text):
        return int(m.group(1).replace(",", ""))
    return None


def extract_performance_range(text: str) -> tuple:
    # 변환된 표 패턴: "전월 이용금액: 30만원 이상"
    m = re.search(r"전월\s*이용금액:\s*(\d+)만원\s*이상(?:\s*~\s*(\d+)만원\s*미만)?", text)
    if m:
        perf_min = int(m.group(1)) * 10000
        perf_max = int(m.group(2)) * 10000 if m.group(2) else None
        level    = f"{m.group(1)}만원 이상" + (f" ~ {m.group(2)}만원 미만" if m.group(2) else "")
        return level, perf_min, perf_max

    # 변환된 표 패턴: "전월 이용금액: 30만원 미만"
    m = re.search(r"전월\s*이용금액:\s*(\d+)만원\s*미만", text)
    if m:
        return f"{m.group(1)}만원 미만", 0, int(m.group(1)) * 10000
        
    # "전월 이용금액 : 30만원 미만 | 30만원 이상 | 60만원 이상" — 다단계 표기
    m = re.search(r"전월\s*이용금액\s*:\s*([^\n]+)", text)
    if m:
        return m.group(1).strip(), None, None

    # "30만원 이상~60만원 미만" 범위 패턴
    m = re.search(r"(\d+)만원\s*이상\s*[~～]\s*(\d+)만원\s*미만", text)
    if m:
        perf_min = int(m.group(1)) * 10000
        perf_max = int(m.group(2)) * 10000
        level    = f"{m.group(1)}만원 이상 ~ {m.group(2)}만원 미만"
        return level, perf_min, perf_max

    # "전월 이용금액30만원 이상" 단순 패턴
    m = re.search(r"전월\s*이용금액\s*(\d+)만원\s*이상", text)
    if m:
        perf_min = int(m.group(1)) * 10000
        level    = f"{m.group(1)}만원 이상"
        return level, perf_min, None

    return "", None, None


def extract_max_limit(text: str) -> tuple:
    # 퍼센트, 원당, 마일리지 단독 숫자 제외
    text = re.sub(r"\d+(?:\.\d+)?\s*%", "", text)
    text = re.sub(r"\d+\s*원당", "", text)
    text = re.sub(r"당\s*\d+\s*마일리지", "", text)

    patterns = [
        (r"월\s*최대\s*(\d+)[,\s]*(000)?\s*원",       1,     "원"),
        (r"월\s*할인한도\s*:\s*(\d+)[,\s]*(000)?\s*원", 1,    "원"),
        (r"통합\s*월\s*(\d+)[,\s]*(000)?\s*원",        1,     "원"),
        (r"월\s*(\d+)\s*만\s*원\s*한도",               10000, "원"),
        (r"월\s*최대\s*(\d+)\s*만\s*원",               10000, "원"),
        (r"월\s*(\d+)\s*만\s*포인트",                  10000, "포인트"),
    ]
    for pattern, mult, unit in patterns:
        if m := re.search(pattern, text.replace(",", "")):
            val = int(m.group(1)) * mult
            return val, unit
    return None, None


def classify_on_offline(benefit_group: str, text: str) -> str:
    # benefit_group 기준 우선 분류
    group_both    = ["교통·이동통신", "이동통신·스트리밍", "온라인간편결제·해외"]
    group_online  = ["온라인", "간편결제", "직구"]
    group_offline = ["국내가맹점", "대중교통", "택시", "주유", "편의점",
                     "놀이공원", "CGV", "롯데시네마", "백화점", "아울렛"]
    group_overseas = ["해외"]

    has_both    = any(k in benefit_group for k in group_both)
    has_online  = any(k in benefit_group for k in group_online)
    has_offline = any(k in benefit_group for k in group_offline)
    has_overseas = any(k in benefit_group for k in group_overseas)

    if has_both or (has_online and has_offline):
        return "Both"
    if has_online:
        return "Online"
    if has_offline:
        return "Offline"
    if has_overseas:
        return "Both"

    # benefit_content 기준 보완
    has_online  = any(k in text for k in [
        "온라인", "인터넷", "직구", "간편결제",
        "배달앱", "배달의민족", "요기요", "쿠팡이츠",
        "넷플릭스", "유튜브", "티빙", "스트리밍",
    ])
    has_offline = any(k in text for k in [
        "커피전문점", "편의점", "백화점", "아울렛",
        "할인점", "마트", "주유소", "음식점", "영화관",
        "병원", "약국", "스타벅스", "이디야",
        "GS25", "CU", "세븐일레븐", "이마트", "홈플러스",
    ])

    if has_online and has_offline:
        return "Both"
    if has_online:
        return "Online"
    if has_offline:
        return "Offline"
    return ""


def extract_max_count(text: str):
    """월 이용 횟수 한도 추출"""
    if m := re.search(r"월\s*(\d+)회", text):
        return int(m.group(1))
    if m := re.search(r"연\s*(\d+)회", text):
        return int(m.group(1))
    return None
