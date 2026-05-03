# parser.py - 신한카드 HTML 파싱
import re
import pandas as pd
from io import StringIO
from datetime import date
from bs4 import BeautifulSoup

from config import CARD_COMPANY
from classifier import (
    get_categories, get_benefit_type, classify_on_offline,
    CATEGORY_MERCHANTS,
)


# ─────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _iter_lines(el) -> list[str]:
    for br in el.find_all("br"):
        br.replace_with("\n")
    return [p.strip() for p in el.get_text().split("\n") if p.strip()]


def _extract_card_id(card: dict, crawl_result: dict) -> str:
    url = crawl_result.get("url", "") or card.get("url", "")
    m = re.search(r"/(\d+_\d+)\.html", url)
    return f"SHC_{m.group(1) if m else 'UNKNOWN'}"


def _korean_to_int(s: str):
    s = s.replace(",", "").replace(" ", "").replace("원", "")
    if re.fullmatch(r"\d+", s):
        return int(s)
    total = 0
    if m := re.search(r"(\d+)만", s):
        total += int(m.group(1)) * 10000
    if m := re.search(r"(\d+)천", s):
        total += int(m.group(1)) * 1000
    return total if total > 0 else None


def _extract_benefit_value(text: str) -> tuple:
    if "수수료" in text:
        return None, None
    patterns = [
        (r"(\d+(?:\.\d+)?)\s*~\s*(\d+(?:\.\d+)?)\s*%",               lambda m: (float(m.group(1)), "%")),
        (r"(\d+(?:\.\d+)?)\s*%",                                       lambda m: (float(m.group(1)), "%")),
        (r"최대\s*(\d+)\s*만\s*(?:마이신한)?포인트",                    lambda m: (int(m.group(1)) * 10000, "포인트")),
        (r"최대\s*(\d+)\s*천\s*(?:마이신한)?포인트",                    lambda m: (int(m.group(1)) * 1000,  "포인트")),
        (r"(\d+)\s*만\s*(\d+)\s*천\s*(?:마이신한)?포인트",             lambda m: (int(m.group(1)) * 10000 + int(m.group(2)) * 1000, "포인트")),
        (r"(\d+)\s*만\s*(?:마이신한)?포인트",                           lambda m: (int(m.group(1)) * 10000, "포인트")),
        (r"(\d+)\s*천\s*(?:마이신한)?포인트",                           lambda m: (int(m.group(1)) * 1000,  "포인트")),
        (r"(\d+)\s*만\s*원",                                            lambda m: (int(m.group(1)) * 10000, "원")),
        (r"(\d+)\s*천\s*원",                                            lambda m: (int(m.group(1)) * 1000,  "원")),
    ]
    for pattern, fn in patterns:
        if m := re.search(pattern, text):
            return fn(m)
    return None, None


def _extract_performance_range(text: str) -> tuple:
    if not text or text == "nan":
        return None, None

    def to_int(s):
        s = s.replace(",", "").replace(" ", "")
        if m := re.search(r"(\d+)만원", s):
            return int(m.group(1)) * 10000
        if m := re.search(r"(\d+)원", s):
            return int(m.group(1))
        return None

    if (m := re.match(r"(.+)\s*이상\s*(.+)\s*미만$", text.strip())):
        return to_int(m.group(1)), to_int(m.group(2))
    if (m := re.match(r"(.+)\s*미만$", text.strip())) and "이상" not in text:
        return 0, to_int(m.group(1))
    if (m := re.match(r"(.+)\s*이상$", text.strip())):
        return to_int(m.group(1)), None
    return None, None


def _remove_condition_text(text: str) -> str:
    for pattern in [
        r"전월\s*이용금액[^.。]*(?:이상|미만)[^.。]*[.。]?",
        r"전월\s*국내\s*이용금액[^.。]*이상[^.。]*[.。]?",
        r"국내\s*이용금액[^.。]*이상[^.。]*[.。]?",
        r"이용금액\s*누적[^.。]*이상[^.。]*[.。]?",
        r"누적금액[^.。]*[.。]?",
        r"월\s*\d+만원\s*이상[^.。]*[.。]?",
        r"예시\)[^.。]*[.。]?",
    ]:
        text = re.sub(pattern, "", text)
    return text.strip()


def _extract_min_amount(text: str):
    if m := re.search(r"전월\s*이용\s*금액\s*(\d+)만원\s*이상", text):
        return int(m.group(1)) * 10000
    if m := re.search(r"건당\s*(\d+)만원\s*이상", text):
        return int(m.group(1)) * 10000
    if m := re.search(r"건당\s*(\d+)천원\s*이상", text):
        return int(m.group(1)) * 1000
    return None


def _extract_max_count(text: str):
    if m := re.search(r"월\s*횟수\s*:\s*(\d+)회", text):
        return int(m.group(1))
    if m := re.search(r"월\s*(\d+)회", text):
        return int(m.group(1))
    return None


def _extract_max_limit(text: str) -> tuple:
    patterns = [
        (r"월\s*한도\s*[^:]*:\s*(\d+)\s*만\s*포인트",   10000, "포인트"),
        (r"월\s*한도\s*[^:]*:\s*(\d+)\s*천\s*포인트",   1000,  "포인트"),
        (r"월\s*한도\s*[:\s]*(\d+)\s*천\s*포인트",      1000,  "포인트"),
        (r"최대\s*(\d+)\s*만\s*(?:마이신한)?포인트",     10000, "포인트"),
        (r"최대\s*(\d+)\s*천\s*(?:마이신한)?포인트",     1000,  "포인트"),
        (r"적립\s*한도\s*(\d+)\s*만\s*포인트",           10000, "포인트"),
        (r"월\s*최대\s*(\d+)\s*만\s*원까지?",            10000, "원"),
        (r"월\s*최대\s*(\d+)\s*천\s*원까지?",            1000,  "원"),
        (r"캐시백한도\s*:\s*(\d+)\s*만\s*원",            10000, "원"),
        (r"캐시백한도\s*:\s*(\d+)\s*천\s*원",            1000,  "원"),
        (r"월\s*(\d+)\s*만\s*원\s*한도",                 10000, "원"),
        (r"월\s*(\d+)\s*천\s*원\s*한도",                 1000,  "원"),
        (r"월\s*(\d+)\s*만\s*원까지",                    10000, "원"),
        (r"월\s*(\d+)\s*천\s*원까지",                    1000,  "원"),
        (r"최대\s*(\d+)\s*만\s*원\s*캐시백",             10000, "원"),
        (r"최대\s*(\d+)\s*천\s*원\s*캐시백",             1000,  "원"),
    ]
    for pattern, mult, unit in patterns:
        if m := re.search(pattern, text):
            return int(m.group(1)) * mult, unit
    return None, None


# ─────────────────────────────────────────────────────────
# 가맹점 추출
# ─────────────────────────────────────────────────────────

KNOWN_MERCHANTS = [
    "배달의민족", "배달의 민족", "요기요", "쿠팡이츠", "땡겨요",
    "넷플릭스", "유튜브 프리미엄", "티빙", "디즈니플러스", "웨이브", "왓챠",
    "SKT", "KT", "LG U+",
    "스타벅스", "투썸플레이스", "이디야", "메가커피", "빽다방", "폴바셋",
    "커피빈", "엔제리너스", "메가MGC커피",
    "GS25", "CU", "세븐일레븐", "이마트24", "미니스톱",
    "맥도날드", "롯데리아", "버거킹", "KFC", "서브웨이",
    "크리스피크림도넛", "배스킨라빈스",
    "쿠팡", "무신사", "지그재그", "에이블리", "크림",
    "올리브영", "다이소", "CGV",
]

GENRE_TO_MERCHANTS = {
    "커피 업종":  CATEGORY_MERCHANTS.get("커피제과/카페/베이커리", []),
    "카페":       CATEGORY_MERCHANTS.get("커피제과/카페/베이커리", []),
    "편의점":     CATEGORY_MERCHANTS.get("편의점", []),
    "배달앱":     CATEGORY_MERCHANTS.get("배달", []),
    "음식점":     CATEGORY_MERCHANTS.get("외식", []),
    "패스트푸드": CATEGORY_MERCHANTS.get("외식", []),
    "백화점":     CATEGORY_MERCHANTS.get("백화점/아울렛/면세점", []),
    "면세점":     CATEGORY_MERCHANTS.get("백화점/아울렛/면세점", []),
    "주유소":     CATEGORY_MERCHANTS.get("자동차/주유", []),
}


def _extract_include_merchants(text: str) -> str:
    found = [kw for kw in KNOWN_MERCHANTS if re.search(rf'(?<![가-힣]){re.escape(kw)}(?![가-힣])', text)]
    return ", ".join(found)


def _extract_exclude_merchants(text: str) -> str:
    result = []
    for genre, merchants in GENRE_TO_MERCHANTS.items():
        if re.search(rf"{genre}\s*(?:업종)?\s*제외", text):
            result.extend(m for m in merchants if m not in result)
    return ", ".join(result)


def _classify_on_offline(섹션: str, 제목: str, 내용: str) -> str:
    combined = f"{섹션} {제목} {내용}"
    if "해외 결제금액" in combined or "해외가맹점" in combined:
        return "Both"
    if any(k in combined for k in ["배달의민족", "배달의 민족", "요기요", "쿠팡이츠", "땡겨요", "배달앱"]):
        return "Online"
    if "오프라인 가맹점" in combined or "오프라인 매장" in combined:
        return "Offline"
    if any(k in combined for k in ["넷플릭스", "유튜브 프리미엄", "티빙", "OTT"]):
        return "Online"
    if any(k in combined for k in ["SKT", "KT", "LG U+", "LGU+", "도시가스", "전기요금", "자동납부"]):
        return "Online"
    return classify_on_offline(섹션, 제목, 내용)


# ─────────────────────────────────────────────────────────
# category_id 매핑
# ─────────────────────────────────────────────────────────

CATEGORY_ID_MAP = {
    "온라인쇼핑":            "1",
    "패션/뷰티":             "2",
    "슈퍼마켓/생활잡화":     "3",
    "백화점/아울렛/면세점":  "4",
    "대중교통/택시":         "5",
    "자동차/주유":           "6",
    "반려동물":              "7",
    "구독/스트리밍":         "8",
    "레저/스포츠":           "9",
    "문화/엔터":             "11",
    "생활비":                "12",
    "편의점":                "13",
    "커피제과/카페/베이커리": "14",
    "배달":                  "15",
    "외식":                  "16",
    "여행/숙박":             "17",
    "항공":                  "18",
    "해외":                  "19",
    "교육/육아":             "20",
    "의료":                  "21",
}

_benefit_counter = 0
_notice_counter  = 0


def _next_benefit_id(card_id: str) -> str:
    global _benefit_counter
    _benefit_counter += 1
    return f"{card_id}_B{_benefit_counter:04d}"


def _next_notice_id(card_id: str) -> str:
    global _notice_counter
    _notice_counter += 1
    return f"{card_id}_N{_notice_counter:04d}"


# ─────────────────────────────────────────────────────────
# 혜택 행(row) 생성
# ─────────────────────────────────────────────────────────

def _make_row(
    card_id: str,
    섹션: str,
    제목: str,
    소제목: str,
    기간: str,
    상세내용: str,
    혜택조건: str = "",
    row_type: str = "benefit",
    benefit_summary: str = "",
    benefit_main_title: str = "",
) -> dict:

    카테고리_list = get_categories(섹션, 제목, 상세내용)
    benefit_type  = get_benefit_type(제목, 상세내용)
    on_offline    = _classify_on_offline(섹션, 제목, 상세내용)
    max_count     = _extract_max_count(상세내용)
    min_amount    = _extract_min_amount(상세내용)
    target        = _extract_include_merchants(상세내용)
    excluded      = _extract_exclude_merchants(상세내용)

    value, unit = _extract_benefit_value(제목)
    if value is None:
        value, unit = _extract_benefit_value(_remove_condition_text(상세내용))

    max_limit, max_limit_unit = _extract_max_limit(상세내용)
    perf_min, perf_max = _extract_performance_range(혜택조건)

    # performance 미추출 시 benefit_content에서 보조 추출
    if not perf_min and not perf_max and 상세내용:
        for pattern in [
            r"전월\s*(?:\([^)]+\)\s*)?(?:국내\s*)?이용금액\s*(\d+만원\s*이상(?:\s*\d+만원\s*미만)?)",
            r"국내\s*이용금액\s*(\d+만원\s*이상(?:\s*\d+만원\s*미만)?)",
            r"지난달\s*이용\s*금액\s*(\d+만원\s*이상(?:\s*\d+만원\s*미만)?)",
        ]:
            if m := re.search(pattern, 상세내용):
                perf_level = _clean(m.group(1))
                perf_min_new, perf_max_new = _extract_performance_range(perf_level)
                if perf_min_new is not None or perf_max_new is not None:
                    혜택조건 = perf_level
                    perf_min, perf_max = perf_min_new, perf_max_new
                    break

    if row_type in ("유의사항", "연회비"):
        카테고리_list = []
        benefit_type = on_offline = ""
        value = unit = target = excluded = max_limit = max_limit_unit = max_count = min_amount = None
        if row_type == "연회비":
            perf_min = perf_max = None
            혜택조건 = ""

    category    = ", ".join(카테고리_list)
    category_id = ", ".join(CATEGORY_ID_MAP.get(c, "") for c in 카테고리_list if CATEGORY_ID_MAP.get(c))

    if not benefit_summary:
        benefit_summary = f"{소제목} - {제목}" if 소제목 and 소제목 != 제목 else 제목
    if not 제목:
        제목 = 섹션

    return {
        "benefit_id":         _next_benefit_id(card_id),
        "card_id":            card_id,
        "row_type":           row_type,
        "benefit_group":      섹션,
        "benefit_title":      제목,
        "benefit_summary":            benefit_summary,
        "benefit_content":    상세내용,
        "category":           category,
        "category_id":        category_id,
        "on_offline":         on_offline,
        "benefit_type":       benefit_type,
        "benefit_value":      value,
        "benefit_unit":       unit,
        "target_merchants":   target,
        "excluded_merchants": excluded,
        "performance_level":  혜택조건,
        "performance_min":    perf_min,
        "performance_max":    perf_max,
        "min_amount":         min_amount,
        "max_count":          max_count,
        "max_limit":          max_limit,
        "max_limit_unit":     max_limit_unit,
        "updated_at":         date.today().isoformat(),
        "benefit_main_title": benefit_main_title,
    }


# ─────────────────────────────────────────────────────────
# 메인 요약 파싱
# ─────────────────────────────────────────────────────────

def _extract_tab_lines(btn) -> list:
    outer_ul = btn.find("ul", class_="marker_dot")
    if not outer_ul:
        return []
    inner_ul = outer_ul.find("ul", class_="marker_dot")
    target_ul = inner_ul if inner_ul else outer_ul

    lines = []
    for li in target_ul.find_all("li", recursive=False):
        li_copy = BeautifulSoup(str(li), "html.parser")
        for sub_ul in li_copy.find_all("ul"):
            sub_ul.decompose()
        if txt := _clean(li_copy.get_text()):
            lines.append(txt)
        for sub_li in li.find_all("li"):
            if txt := _clean(sub_li.get_text()):
                lines.append(txt)

    if not lines:
        lines = [_clean(p.get_text()) for p in target_ul.find_all("p") if _clean(p.get_text())]

    return lines


def _parse_main_summary(soup) -> dict:
    result = {}
    items = sorted(
        [i for i in soup.find_all("div", class_="item") if i.get("data-num") is not None],
        key=lambda x: int(x.get("data-num", 0)),
    )
    for item in items:
        btn = item.find("button")
        if not btn:
            continue
        title_el = btn.find("strong", class_="title")
        if title_el and (tab_title := _clean(title_el.get_text())):
            result[tab_title] = _extract_tab_lines(btn)
    return result


# ─────────────────────────────────────────────────────────
# 표 파싱
# ─────────────────────────────────────────────────────────

def _parse_table(table_el, card_id, 섹션, 제목, 소제목, summary="", row_type="상세혜택") -> list:
    rows = []
    df = pd.read_html(StringIO(str(table_el)))[0]
    headers = list(df.columns)

    CONDITION_HEADERS = ["전월 이용금액", "건당 결제금액", "이용금액", "적용구간", "월 이용금액", "지난달 이용 금액"]
    is_condition_col = any(kw in str(headers[0]) for kw in CONDITION_HEADERS) if headers else False
    is_transposed    = not is_condition_col and any(re.search(r"\d+만원", str(h)) for h in headers[1:])

    if is_transposed:
        for col_header in headers[1:]:
            for _, row in df.iterrows():
                r = _make_row(card_id, 섹션, 제목, 소제목, "", f"{row.iloc[0]}: {row[col_header]}", str(col_header), row_type, summary)
                rows.append(r)
    else:
        # rowspan 공통값 추출
        common_parts = {
            h: vals[0]
            for col_idx, h in enumerate(headers[1:], 1)
            if len(set(vals := [str(v) for v in df.iloc[:, col_idx] if str(v) not in ("nan", "-", "")])) == 1
            and len(vals) == len(df)
        }
        for _, row in df.iterrows():
            if is_condition_col and all(str(v) in ("nan", "-", "") for v in row.iloc[1:]):
                continue
            parts = [f"{h}: {v}" for h, v in zip(headers, row) if str(v) not in ("nan", "-", "")]
            r = _make_row(card_id, 섹션, 제목, 소제목, "", " | ".join(parts), str(row.iloc[0]) if is_condition_col else "", row_type, summary)
            value, unit = _extract_benefit_value(str(row.iloc[1]) if len(row) > 1 else "")
            if value is not None:
                r["benefit_value"], r["benefit_unit"] = value, unit
            rows.append(r)
        if common_parts:
            content = " | ".join(f"{h}: {v}" for h, v in common_parts.items())
            rows.append(_make_row(card_id, 섹션, 제목, 소제목, "", content, "", row_type, summary))

    return rows


# ─────────────────────────────────────────────────────────
# 슬라이드 파싱
# ─────────────────────────────────────────────────────────

def _parse_heading(slide_el):
    for tag in ["h3", "h4"]:
        if el := slide_el.find(tag, class_=re.compile(r"tit_dep\d+")):
            return tag, _clean(el.get_text())
    return None, None


def _parse_slide_element(el, card_id, benefit_group, current_h4, heading_text) -> list:
    rows = []
    cls_str = " ".join(el.get("class", []))
    제목 = current_h4 if current_h4 else heading_text

    if "guidebook" in cls_str:
        for a in el.find_all("a"):
            if txt := _clean(a.get_text()):
                rows.append(_make_row(card_id, benefit_group, 제목, current_h4, "", f"{txt} ({a.get('href', '')})", "", "상세혜택"))
        return rows

    for tbl in (el.find_all("table") if el.name != "table" else [el]):
        rows.extend(_parse_table(tbl, card_id, benefit_group, 제목, current_h4, row_type="상세혜택"))

    el_copy = BeautifulSoup(str(el), "html.parser")
    for tbl in el_copy.find_all("table"):
        tbl.decompose()

    row_type = "유의사항" if "marker_refer" in cls_str else "상세혜택"
    if el.name == "p":
        if line := _clean(el.get_text()):
            rows.append(_make_row(card_id, benefit_group, 제목, current_h4, "", line, "", row_type))
        return rows

    for line in _iter_lines(el_copy):
        rows.append(_make_row(card_id, benefit_group, 제목, current_h4, "", line, "", row_type))

    return rows


def _parse_slide(slide_el, card_id: str, tab_title: str = "") -> list:
    heading_tag, heading_text = _parse_heading(slide_el)
    if not heading_text:
        return []

    benefit_group = tab_title if tab_title else heading_text
    print(f"  [슬라이드] 탭={benefit_group} | {heading_tag}={heading_text}")

    heading_el = slide_el.find(heading_tag, class_="tit_dep2")
    siblings   = list(heading_el.find_next_siblings()) if heading_tag == "h3" else list(slide_el.children)

    rows, current_h3, current_h4 = [], heading_text, ""

    for el in siblings:
        if not hasattr(el, "name") or el.name in (None, "script"):
            continue
        if el.name == "h3":
            current_h3, current_h4 = _clean(el.get_text()), ""
            continue
        if el.name == "h4":
            current_h4 = _clean(el.get_text())
            continue
        if el.name == "div" and (inner_h4s := el.find_all("h4")):
            el_copy = BeautifulSoup(str(el), "html.parser")
            for h4 in el_copy.find_all("h4"):
                h4.decompose()
            cls_str = " ".join(el.get("class", []))

            if "border_boxing" in cls_str and len(inner_h4s) > 1:
                for i, h4 in enumerate(inner_h4s):
                    current_h4 = _clean(h4.get_text())
                    next_h4    = inner_h4s[i + 1] if i + 1 < len(inner_h4s) else None
                    sibs       = [s for s in h4.find_next_siblings() if not (next_h4 and s == next_h4)]
                    for sib in sibs:
                        for r in _parse_slide_element(sib, card_id, benefit_group, current_h4, current_h3):
                            r["benefit_main_title"] = tab_title
                            rows.append(r)
            else:
                current_h4 = _clean(inner_h4s[0].get_text())
                for r in _parse_slide_element(el_copy, card_id, benefit_group, current_h4, current_h3):
                    r["benefit_main_title"] = tab_title
                    rows.append(r)
            continue

        제목 = current_h4 if current_h4 else current_h3
        for r in _parse_slide_element(el, card_id, benefit_group, 제목, current_h3):
            r["benefit_main_title"] = tab_title
            rows.append(r)

    return rows


# ─────────────────────────────────────────────────────────
# 연회비 파싱
# ─────────────────────────────────────────────────────────

def _parse_annual_fee(fee_text: str) -> dict:
    result = {"국내일반연회비": 0, "국내프리미엄연회비": 0, "해외일반연회비": 0, "해외프리미엄연회비": 0}
    if not fee_text:
        return result
    for line in [l.strip() for l in fee_text.replace("/", "\n").split("\n") if l.strip()]:
        val = _korean_to_int(line)
        if val is None:
            continue
        if any(k in line for k in ["VISA", "Master", "AMEX", "해외"]):
            result["해외일반연회비"] = result["해외일반연회비"] or val
        elif any(k in line for k in ["Platinum", "플래티넘", "프리미엄"]):
            result["국내프리미엄연회비"] = result["국내프리미엄연회비"] or val
        else:
            result["국내일반연회비"] = result["국내일반연회비"] or val
    return result


def _parse_annual_fee_table(crawl_result: dict) -> tuple:
    """(lines, dom_basic, dom_premium, notes) 반환"""
    html = crawl_result.get("annual_fee_html", "")
    if not html:
        return [], None, None, None
    soup  = BeautifulSoup(html, "html.parser")
    wrap  = soup.find("div", class_="annual-fee")
    table = wrap.find("table") if wrap else None
    if not table:
        return [], None, None, None

    lines, notes_parts, dom_basic, dom_premium = [], [], None, None

    for tr in table.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        row = [td.find("img")["alt"] if td.find("img") else td.get_text(strip=True) for td in tds]
        브랜드, 옵션, 기본, 서비스, 총연회비 = row[:5]

        lines.append(f"브랜드: {브랜드} | 옵션: {옵션} | 기본: {기본} | 서비스: {서비스} | 총연회비: {총연회비}")

        기본_int, 서비스_int, 총_int = _korean_to_int(기본) or 0, _korean_to_int(서비스) or 0, _korean_to_int(총연회비) or 0
        notes_parts.append(f"{브랜드} {옵션}: 기본 {기본_int:,}원 + 서비스 {서비스_int:,}원 = {총_int:,}원")

        if 총_int:
            if any(k in 옵션 for k in ["Platinum", "플래티넘", "프리미엄"]):
                dom_premium = dom_premium or 총_int
            else:
                dom_basic = dom_basic or 총_int

    return lines, dom_basic, dom_premium, (" / ".join(notes_parts) or None)


# ─────────────────────────────────────────────────────────
# 1. 기본정보
# ─────────────────────────────────────────────────────────

def parse_card_info(card: dict, crawl_result: dict) -> dict:
    html      = crawl_result["html"]
    soup      = BeautifulSoup(html, "html.parser")
    body_text = soup.get_text()
    card_id   = _extract_card_id(card, crawl_result)

    fee_info = _parse_annual_fee(crawl_result.get("annual_fee_text", ""))
    _, dom_basic, dom_premium, annual_fee_notes = _parse_annual_fee_table(crawl_result)
    if dom_basic:
        fee_info["국내일반연회비"] = dom_basic
    if dom_premium:
        fee_info["국내프리미엄연회비"] = dom_premium

    # 대표혜택
    rep_benefits = []
    if benefit_ul := soup.find("ul", class_="info-benefit"):
        for li in benefit_ul.find_all("li"):
            span, b = li.find("span"), li.find("b")
            if b:
                rep_benefits.append(
                    f"{_clean(span.get_text())} {_clean(b.get_text())}" if span else _clean(b.get_text())
                )
    대표혜택 = " / ".join(rep_benefits) or "국내외 전가맹점 포인트 적립"

    # 네트워크
    network = ", ".join(
        n for n, kws in {"VISA": ["VISA"], "Master": ["Master"], "AMEX": ["AMEX"]}.items()
        if any(k in body_text for k in kws)
    ) or "Local"

    # 후불교통카드
    transport_texts = re.findall(r"후불교통카드[^\n]{0,20}", body_text)
    has_transport   = any("불가" not in t for t in transport_texts)

    # 이미지/링크
    img       = soup.select_one("span.front img")
    image_url = "https://www.shinhancard.com" + img["src"] if img else None
    canonical = soup.find("link", rel="canonical")
    link_url  = canonical["href"] if canonical else crawl_result.get("url", "")

    # 전월실적
    m = re.search(r"전월\s*이용\s*금액\s*(\d+)만원\s*이상", body_text)

    # 캐시백 API
    card_api      = None
    cardinfo_list = crawl_result.get("api_data", {}).get("cardinfo_data", {}).get("cardInfo", [])
    for c in cardinfo_list:
        if c.get("hpgCrdPdUrlAr", "") in card.get("url", ""):
            card_api = c
            break

    return {
        "card_id":                card_id,
        "company":                CARD_COMPANY,
        "card_name":              card["카드명"],
        "card_type":              card.get("카드종류", "신용"),
        "network":                network,
        "is_domestic_foreign":    "해외겸용" in body_text,
        "has_transport":          has_transport,
        "annual_fee_dom_basic":   fee_info["국내일반연회비"] or 0,
        "annual_fee_dom_premium": fee_info["국내프리미엄연회비"] or 0,
        "annual_fee_for_basic":   fee_info["해외일반연회비"] or 0,
        "annual_fee_for_premium": fee_info["해외프리미엄연회비"] or 0,
        "annual_fee_notes":       annual_fee_notes,
        "min_performance":        int(m.group(1)) * 10000 if m else None,
        "summary":                대표혜택,
        "image_url":              image_url,
        "link_url":               link_url,
        "has_cashback":           (card_api.get("hpgCrdPdCsbF") == "Y" if card_api else False) or "캐시백" in 대표혜택,
        "updated_at":             date.today().isoformat(),
    }


# ─────────────────────────────────────────────────────────
# 2. 혜택목록
# ─────────────────────────────────────────────────────────

def parse_benefits(card: dict, crawl_result: dict) -> list:
    global _benefit_counter
    _benefit_counter = 0

    html    = crawl_result["html"]
    soup    = BeautifulSoup(html, "html.parser")
    card_id = _extract_card_id(card, crawl_result)
    rows    = []

    # 주요혜택 (탭 요약)
    for tab_title, lines in _parse_main_summary(soup).items():
        for line in (lines or [""]):
            rows.append(_make_row(card_id, tab_title, tab_title, "", "", line, "", "주요혜택", "", tab_title))

    # 탭 타이틀 순서
    tab_titles_sorted = [
        _clean(item.find("strong", class_="title").get_text())
        for item in sorted(
            [i for i in soup.find_all("div", class_="item") if i.get("data-num") is not None],
            key=lambda x: int(x.get("data-num", 0)),
        )
        if item.find("strong", class_="title")
    ]

    for i, slide in enumerate(soup.find_all("div", class_="benefit_cont_wrap")):
        tab_title = tab_titles_sorted[i] if i < len(tab_titles_sorted) else ""
        rows.extend(_parse_slide(slide, card_id, tab_title))

    # 연회비
    lines, *_ = _parse_annual_fee_table(crawl_result)
    for line in lines:
        rows.append(_make_row(card_id, "연회비", "연회비", "연회비", "", line, "", "연회비", line, "연회비"))

    return rows


# ─────────────────────────────────────────────────────────
# 3. 유의사항
# ─────────────────────────────────────────────────────────

def parse_notices(card: dict, crawl_result: dict) -> list:
    global _notice_counter
    _notice_counter = 0

    soup    = BeautifulSoup(crawl_result["html"], "html.parser")
    card_id = _extract_card_id(card, crawl_result)
    rows    = []

    def add(sub_category, txt):
        if txt and len(txt) > 3:
            rows.append({
                "notice_id":       _next_notice_id(card_id),
                "card_id":         card_id,
                "notice_category": sub_category,
                "sub_category":    sub_category,
                "notice_content":  txt,
                "updated_at":      date.today().isoformat(),
            })

    # 아코디언
    for dl in soup.select("div.sect.precautions dl, div.accordion-dx dl"):
        if dl.find_parent("div", class_="mtr-notice"):
            continue
        dt, dd = dl.find("dt"), dl.find("dd")
        if not dt or not dd:
            continue
        sub = _clean(dt.get_text())
        if len(sub) < 3:
            continue
        for tag in dd.find_all("div", class_=["carddetail_qr_box", "mtr-notice"]):
            tag.decompose()
        for line in _iter_lines(dd):
            add(sub, line)

    # 여신문구
    if jun := soup.find("div", class_="card_jun_info"):
        for line in _iter_lines(jun):
            add("금융소비자보호", line)

    # 여신금융협회 심의필
    if p := soup.find("p", class_="j-para"):
        add("금융소비자보호", _clean(p.get_text()))

    print(f"  [유의사항] {len(rows)}행")
    return rows


# ─────────────────────────────────────────────────────────
# 4. 이벤트
# ─────────────────────────────────────────────────────────

def parse_events(card: dict, crawl_result: dict, event_details: dict = None) -> list:
    rows          = []
    card_name     = card["카드명"]
    card_id       = _extract_card_id(card, crawl_result)
    event_details = event_details or {}
    soup          = BeautifulSoup(crawl_result["html"], "html.parser")

    def _event_row(ev_title, ev_link, start_date, end_date, section, content):
        if content and len(content) > 2:
            rows.append({
                "card_id":           card_id,
                "company":           CARD_COMPANY,
                "card_name":         card_name,
                "origin_event_code": "",
                "event_title":       ev_title,
                "event_link":        ev_link,
                "start_date":        start_date,
                "end_date":          end_date,
                "event_type":        get_benefit_type(ev_title, ""),
                "section":           section,
                "event_content":     content,
                "updated_at":        date.today().isoformat(),
            })

    # mtrPopup
    end_date = ev_link = ""
    for p in soup.find_all("p", class_="marker_refer"):
        if m := re.search(r"마스터 트래블 리워드는 (\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일까지", _clean(p.get_text())):
            end_date = f"{m.group(1)}.{m.group(2).zfill(2)}.{m.group(3).zfill(2)}"
            break

    if mtr_pop := soup.find("div", id="mtrPopup"):
        if a := mtr_pop.find("a", href=re.compile(r"mastercardservices")):
            ev_link = a.get("href", "")
        for tag in mtr_pop.find_all(["style", "script"]):
            tag.decompose()
        title_el = mtr_pop.find("h3")
        ev_title = _clean(title_el.get_text()) if title_el else "마스터 가맹점 혜택 안내"

        if mtr_useway := mtr_pop.find("div", class_="mtr-useway"):
            current_section = "이용방법"
            for el in mtr_useway.children:
                if not hasattr(el, "name") or not el.name:
                    continue
                if "useway-tit" in " ".join(el.get("class", [])):
                    current_section = _clean(el.get_text())
                elif el.name == "ol":
                    for li in el.find_all("li", recursive=False):
                        if tit_el := li.find("div", class_="useway-list-tit"):
                            _event_row(ev_title, ev_link, "", end_date, current_section, _clean(tit_el.get_text()))
                        for txt_el in li.find_all("div", class_="txt"):
                            _event_row(ev_title, ev_link, "", end_date, current_section, _clean(txt_el.get_text()))
                else:
                    for line in _iter_lines(el):
                        _event_row(ev_title, ev_link, "", end_date, current_section, line)

        if mtr_notice := mtr_pop.find("div", class_="mtr-notice"):
            dt      = mtr_notice.find("dt")
            section = _clean(dt.get_text()) if dt else "꼭! 알아두세요"
            if dd := mtr_notice.find("dd"):
                for line in _iter_lines(dd):
                    _event_row(ev_title, ev_link, "", end_date, section, line)

    # 이벤트 링크
    for ev in crawl_result.get("event_links", []):
        url         = ev.get("url", "")
        detail_data = event_details.get(url, {})
        ev_title    = detail_data.get("title") or ev.get("text", "")
        ev_period   = detail_data.get("period", "")
        parts       = ev_period.replace(" ", "").split("~") if ev_period else ["", ""]
        start_date  = parts[0]
        end_date    = parts[1] if len(parts) > 1 else ""
        혜택종류    = get_benefit_type(ev_title, ev.get("sub", ""))

        sections = detail_data.get("sections", [])
        if sections:
            for sec in sections:
                for line in sec.get("lines", []):
                    if line:
                        rows.append({
                            "card_id": card_id, "company": CARD_COMPANY, "card_name": card_name,
                            "origin_event_code": "", "event_title": ev_title, "event_link": url,
                            "start_date": start_date, "end_date": end_date,
                            "event_type": 혜택종류, "section": sec["section"],
                            "event_content": line, "updated_at": date.today().isoformat(),
                        })
        else:
            rows.append({
                "card_id": card_id, "company": CARD_COMPANY, "card_name": card_name,
                "origin_event_code": "", "event_title": ev_title, "event_link": url,
                "start_date": start_date, "end_date": end_date,
                "event_type": 혜택종류, "section": "이벤트내용",
                "event_content": ev.get("sub", ""), "updated_at": date.today().isoformat(),
            })

    return rows