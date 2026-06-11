import re

from hd_parser_base import (
    CATEGORY_ID_MAP, CATEGORY_KEYWORD_MAP, USAGE_PLACE_TITLES,
    now_date, format_benefit_content,
)
from hd_parser_html import build_ui_from_html
from hd_parser_llm import (
    call_claude, parse_json_response,
    USAGE_PLACE_SYSTEM, USAGE_PLACE_PROMPT,
    _build_benefit_system, _make_benefit_user,
)


# ─────────────────────────────────────────────
# 공통 헬퍼
# ─────────────────────────────────────────────
def _trim_voucher_content(content: str) -> str:
    m = re.search(r'^(the\s+\S.*?바우처)\s*$', content, re.MULTILINE)
    if m:
        return content[m.start():].strip()
    return content


def _determine_on_offline(content: str, category: str, merchants: str) -> str:
    text = (content + " " + merchants).lower()

    ONLINE_CATS  = {"온라인쇼핑", "구독/스트리밍", "배달"}
    OFFLINE_CATS = {"편의점", "대중교통/택시", "자동차/주유", "슈퍼마켓/생활잡화",
                    "백화점/아울렛/면세점", "외식"}

    cats = [c.strip() for c in category.split(",") if c.strip()]
    for cat in cats:
        if cat in ONLINE_CATS:  return "Online"
        if cat in OFFLINE_CATS: return "Offline"

    online_kws  = ["온라인", "홈페이지", "앱결제", "공식 앱", "인터넷", "정기 결제",
                   "자동납부", "모바일 앱", "앱스토어", "구글플레이"]
    offline_kws = ["오프라인 매장", "오프라인", "매장 방문", "현장 결제"]

    if any(kw in text for kw in online_kws):  return "Online"
    if any(kw in text for kw in offline_kws): return "Offline"

    return "Both"


def _make_base_row(card_id: str, group: str, title: str, row_type: str,
                   forced_benefit_type: str, content: str, seq_ref: list) -> dict:
    return {
        "benefit_id":           f"{card_id}_B{seq_ref[0]:04d}",
        "card_id":              card_id,
        "row_type":             row_type,
        "benefit_group":        group,
        "benefit_title":        title,
        "category":             "기타",
        "category_id":          "22",
        "on_offline":           "",
        "benefit_value":        "",
        "benefit_unit":         "",
        "target_merchants":     "",
        "performance_level":    "",
        "performance_min":      "",
        "performance_max":      "",
        "min_amount":           "",
        "max_count":            "",
        "max_limit":            "",
        "max_limit_unit":       "",
        "group_max_limit":      "",
        "group_max_limit_unit": "",
        "unit_amount":          "",
        "benefit_content":      content,
        "ui_title":             "",
        "ui_content":           content,
        "ui_table":             "",
        "updated_at":           now_date(),
    }


def _fill_base_numerics(row: dict, benefit_only: str, forced_benefit_type: str) -> None:
    lines = [l.strip() for l in benefit_only.split('\n') if l.strip()]
    first = lines[0] if lines else ""

    if forced_benefit_type:
        row["benefit_type"] = forced_benefit_type
    else:
        search_text = " ".join(lines[:5])
        for kw, bt in [("할인", "할인"), ("캐시백", "캐시백"), ("적립", "포인트"),
                       ("포인트", "포인트"), ("마일리지", "마일리지"), ("서비스", "서비스")]:
            if kw in search_text:
                row["benefit_type"] = bt
                break

    for line in lines[:5]:
        m = re.search(r'(\d+(?:\.\d+)?)\s*(%|원|포인트|마일리지)', line)
        if m:
            row["benefit_value"] = m.group(1)
            row["benefit_unit"]  = m.group(2)
            break

    pm = re.search(r'전월\s*이용\s*금액\s*(\d+)\s*만원\s*이상', benefit_only)
    if pm:
        row["performance_min"]   = str(int(pm.group(1)) * 10000)
        row["performance_level"] = f"전월 실적 {pm.group(1)}만원 이상"


def _apply_category_keyword(row: dict, benefit_only: str) -> None:
    merged = " ".join([
        str(row.get("target_merchants", "")),
        benefit_only,
        str(row.get("benefit_title", "")),
    ])
    for cat_name, keywords in CATEGORY_KEYWORD_MAP:
        if any(kw in merged for kw in keywords):
            row["category"]    = cat_name
            row["category_id"] = str(CATEGORY_ID_MAP.get(cat_name, 22))
            return


def _finalize(rows: list, full_content: str) -> list:
    formatted = format_benefit_content(full_content)
    for r in rows:
        r["benefit_content"] = formatted
        r["ui_content"]      = formatted
        r.pop("_ui_built", None)
        r["ui_table"] = ""

        if not r.get("on_offline"):
            r["on_offline"] = _determine_on_offline(
                full_content,
                r.get("category", ""),
                r.get("target_merchants", "")
            )
        if not r.get("benefit_type"):
            r["benefit_type"] = "할인"
        if not r.get("ui_title"):
            cat  = r.get("category", "")
            bv   = r.get("benefit_value", "")
            bu   = r.get("benefit_unit", "")
            bt   = r.get("benefit_type", "")
            r["ui_title"] = f"{cat} {bv}{bu} {bt}".strip() if bv else f"{cat} {bt}".strip()
        if not r.get("updated_at"):
            r["updated_at"] = now_date()

        for f in ["benefit_value", "performance_min", "performance_max",
                  "min_amount", "max_count", "max_limit", "group_max_limit", "unit_amount"]:
            if r.get(f) in (None, "null", "None"):
                r[f] = ""

    if len(rows) > 1:
        ref_value = next((r["benefit_value"] for r in rows if r.get("benefit_value")), "")
        ref_unit  = next((r["benefit_unit"]  for r in rows if r.get("benefit_unit")),  "")
        ref_type  = next((r["benefit_type"]  for r in rows if r.get("benefit_type")),  "")
        for r in rows:
            if not r.get("benefit_value") and ref_value:
                r["benefit_value"] = ref_value
            if not r.get("benefit_unit") and ref_unit:
                r["benefit_unit"]  = ref_unit
            if not r.get("benefit_type") and ref_type:
                r["benefit_type"]  = ref_type
            if r.get("ui_title", "").endswith(r.get("benefit_type","").strip()):
                cat = r.get("category","")
                bv  = r.get("benefit_value","")
                bu  = r.get("benefit_unit","")
                bt  = r.get("benefit_type","")
                if bv:
                    r["ui_title"] = f"{cat} {bv}{bu} {bt}".strip()

    return rows


# ─────────────────────────────────────────────
# [대상 영역] Python 처리
# ─────────────────────────────────────────────
def _append_row(result: list, base_row: dict, card_id: str, seq_ref: list,
                cat_name: str, cat_id: str, tm: str,
                gml: str, gml_unit: str, bv: str, bu: str, bt: str):
    ui_title = f"{cat_name} {bv}{bu} {bt}".strip() if bv else f"{cat_name} {bt}".strip()
    new_row = base_row.copy()
    new_row.update({
        "benefit_id":           f"{card_id}_B{seq_ref[0]:04d}",
        "category":             cat_name,
        "category_id":          cat_id,
        "target_merchants":     tm[:50] if len(tm) > 50 else tm,
        "ui_title":             ui_title,
        "group_max_limit":      gml,
        "group_max_limit_unit": gml_unit,
        "max_limit":            "",
        "max_limit_unit":       "",
    })
    seq_ref[0] += 1
    result.append(new_row)


def _split_by_daesangyeok(base_row: dict, content: str, seq_ref: list, card_id: str) -> list:
    block_match = re.search(r'\[?대상\s*영역\]?\n(.*?)(?:\n\n|\n\[|$)', content, re.DOTALL)
    if not block_match:
        return []

    block_text = block_match.group(1).strip()
    lines = [l.strip() for l in block_text.split("\n") if l.strip()]

    AREA_HEADER_RE = re.compile(r'^[가-힣a-zA-Z/·\s\(\)]{1,30}$')
    AREA_DEFAULT_CAT = [
        ("온라인몰",      "온라인쇼핑",         "1"),
        ("대형마트",      "슈퍼마켓/생활잡화",   "3"),
        ("슈퍼마켓",      "슈퍼마켓/생활잡화",   "3"),
        ("백화점",        "백화점/아울렛/면세점", "4"),
        ("프리미엄 아울렛","백화점/아울렛/면세점", "4"),
        ("아울렛",        "백화점/아울렛/면세점", "4"),
        ("커피전문점",    "카페/베이커리",        "14"),
        ("편의점",        "편의점",              "13"),
        ("다이닝",        "외식",               "16"),
        ("일반음식점",    "외식",               "16"),
        ("배달 앱",       "배달",               "15"),
        ("배달앱",        "배달",               "15"),
        ("웰니스",        "레저/스포츠",         "9"),
        ("골프",          "레저/스포츠",         "9"),
        ("테크",          "구독/스트리밍",        "8"),
        ("쇼핑",          "온라인쇼핑",          "1"),
        ("호텔",          "여행/숙박",           "17"),
        ("여행",          "여행/숙박",           "17"),
        ("항공",          "항공",               "18"),
        ("교통",          "대중교통/택시",        "5"),
        ("교육",          "교육/육아",           "20"),
        ("병원",          "의료",               "21"),
        ("주유소",        "자동차/주유",          "6"),
        ("충전소",        "자동차/주유",          "6"),
        ("정비소",        "자동차/주유",          "6"),
        ("세차장",        "자동차/주유",          "6"),
        ("이동통신",      "생활비",              "12"),
        ("아파트 관리비",  "생활비",              "12"),
        ("도시가스",      "생활비",              "12"),
    ]

    EXCLUDE_KW = ["한도(", "합산 기준", "적립률 적용", "이상 시 기본", "미만도 혜택",
                  "에 한해", "이용 건은", "결제 건은", "지침에 따름", "운영 시간"]

    area_groups = []
    current_area = None
    current_items = []
    for line in lines:
        if any(kw in line for kw in EXCLUDE_KW):
            continue

        bare = line.strip("[]").strip()

        if ':' in bare:
            colon_pos = bare.index(':')
            area_candidate = bare[:colon_pos].strip()
            merchants_part = bare[colon_pos+1:].strip()
            if any(kw in area_candidate for kw, _, _ in AREA_DEFAULT_CAT) and len(area_candidate) <= 15:
                if current_area is not None:
                    area_groups.append((current_area, current_items))
                current_area = area_candidate
                current_items = [merchants_part] if merchants_part else []
                continue

        is_header = any(kw in bare for kw, _, _ in AREA_DEFAULT_CAT) and (AREA_HEADER_RE.match(bare) or AREA_HEADER_RE.match(line))
        if is_header:
            if current_area is not None:
                area_groups.append((current_area, current_items))
            current_area = bare
            current_items = []
        else:
            if current_area is not None:
                clean = line.lstrip("-").strip()
                if clean:
                    current_items.append(clean)
    if current_area is not None:
        area_groups.append((current_area, current_items))

    if len(area_groups) < 2:
        return []

    gml, gml_unit = "", ""
    gml_match = re.search(
        r'영역(?:별|당)?\s*월\s*([\d]+)\s*(만|천)?\s*(M포인트|포인트|원)',
        content
    )
    if gml_match:
        num      = int(gml_match.group(1))
        unit_kr  = gml_match.group(2) or ""
        gml_unit = "포인트" if "포인트" in gml_match.group(3) else "원"
        gml = str(num * 10000 if unit_kr == "만" else num * 1000 if unit_kr == "천" else num)

    def _detect_cat(text: str) -> tuple:
        for cn, keywords in CATEGORY_KEYWORD_MAP:
            if any(kw in text for kw in keywords):
                return cn, str(CATEGORY_ID_MAP.get(cn, 22))
        return "기타", "22"

    def _area_default_cat(area_name: str) -> tuple:
        for kw, cn, cid in AREA_DEFAULT_CAT:
            if kw in area_name:
                return cn, cid
        return "기타", "22"

    result = []
    bv = base_row.get("benefit_value", "")
    bu = base_row.get("benefit_unit", "")
    bt = base_row.get("benefit_type", "")

    for area_name, items in area_groups:
        if not items:
            cat_name, cat_id = _area_default_cat(area_name)
            _append_row(result, base_row, card_id, seq_ref,
                        cat_name, cat_id, area_name, gml, gml_unit, bv, bu, bt)
            continue

        area_cat, area_cid = _area_default_cat(area_name)

        cat_buckets: dict = {}
        cat_order = []
        for item in items:
            if area_cat != "기타":
                cat_name, cat_id = area_cat, area_cid
            else:
                cat_name, cat_id = _detect_cat(item)
                if cat_name == "기타":
                    cat_name, cat_id = "기타", "22"
            key = (cat_name, cat_id)
            if key not in cat_buckets:
                cat_buckets[key] = []
                cat_order.append(key)
            cat_buckets[key].append(item)

        for (cat_name, cat_id) in cat_order:
            merchants_list = cat_buckets[(cat_name, cat_id)]
            tm = ", ".join(merchants_list)[:100]
            _append_row(result, base_row, card_id, seq_ref,
                        cat_name, cat_id, tm, gml, gml_unit, bv, bu, bt)

    merged: dict = {}
    merged_order = []
    for r in result:
        key = r["category"]
        if key not in merged:
            merged[key] = r.copy()
            merged_order.append(key)
        else:
            tm_ex  = merged[key].get("target_merchants", "")
            tm_new = r.get("target_merchants", "")
            combined = (tm_ex + ", " + tm_new).strip(", ")
            merged[key]["target_merchants"] = combined[:100]
    result = [merged[k] for k in merged_order]

    tier_pattern = re.compile(
        r'(\d+)\s*만원\s*이상\s*(?:(\d+)\s*만원\s*미만\s*)?:\s*(?:대상\s*영역\s*통합해\s*)?월\s*([\d]+)\s*(만\s*\d+\s*천|만|천)?원'
    )
    tiers = []
    for m in tier_pattern.finditer(content):
        p_min = int(m.group(1)) * 10000
        p_max = int(m.group(2)) * 10000 if m.group(2) else ""
        raw_limit = m.group(3)
        unit_kr   = (m.group(4) or "").replace(" ", "")
        if "만" in unit_kr and "천" in unit_kr:
            extra = int(re.search(r'만(\d+)천', unit_kr).group(1)) * 1000 if re.search(r'만(\d+)천', unit_kr) else 0
            ml = int(raw_limit) * 10000 + extra
        elif unit_kr.startswith("만"):
            ml = int(raw_limit) * 10000
        elif unit_kr.startswith("천"):
            ml = int(raw_limit) * 1000
        else:
            ml = int(raw_limit)
        level_txt = f"전월 실적 {m.group(1)}만원 이상" + (f" {m.group(2)}만원 미만" if m.group(2) else "")
        tiers.append((p_min, p_max, ml, level_txt))

    if len(tiers) >= 2:
        expanded = []
        for tier_min, tier_max, tier_ml, tier_level in tiers:
            for r in result:
                new_r = r.copy()
                new_r["performance_min"]      = str(tier_min)
                new_r["performance_max"]      = str(tier_max) if tier_max != "" else ""
                new_r["performance_level"]    = tier_level
                new_r["group_max_limit"]      = str(tier_ml)
                new_r["group_max_limit_unit"] = "원"
                new_r["max_limit"]      = ""
                new_r["max_limit_unit"] = ""
                expanded.append(new_r)
        result = expanded

    base_id = int(result[0]["benefit_id"].split("_B")[1]) if result else seq_ref[0]
    for i, r in enumerate(result):
        r["benefit_id"] = f"{card_id}_B{base_id + i:04d}"
    seq_ref[0] = base_id + len(result)

    return result


# ─────────────────────────────────────────────
# 서비스 타입 카테고리 분리 (바우처 등)
# ─────────────────────────────────────────────
def _split_service_by_category(base_row: dict, content: str, seq_ref: list, card_id: str) -> list:
    voucher_title_match = re.search(
        r'^(the\s+\S+(?:\s+\S+)?\s*[바우처크레딧]|the\s+\S+\s+\S+\s+[바우처크레딧]'
        r'|현대카드\s+\S+.*?[바우처크레딧])\s*$',
        content, re.MULTILINE
    )
    if voucher_title_match:
        target_content = content[voucher_title_match.start():]
    else:
        target_content = content

    AREA_HEADER_RE = re.compile(
        r'^(쇼핑|호텔|여행|항공|백화점|면세점|패션\s*전문몰|골프|다이닝|문화|레저'
        r'|M포인트\s*교환?|M포인트|Luxury|Gourmet)$',
        re.MULTILINE
    )
    headers = AREA_HEADER_RE.findall(target_content)
    if len(set(h.strip() for h in headers)) < 2:
        return []

    CAT_MAP = {
        "쇼핑":        ("백화점/아울렛/면세점", "4"),
        "백화점":      ("백화점/아울렛/면세점", "4"),
        "면세점":      ("백화점/아울렛/면세점", "4"),
        "호텔":        ("백화점/아울렛/면세점", "4"),
        "패션 전문몰": ("패션/뷰티",            "2"),
        "여행":        ("여행/숙박",            "17"),
        "항공":        ("항공",                 "18"),
        "골프":        ("레저/스포츠",          "9"),
        "레저":        ("레저/스포츠",          "9"),
        "다이닝":      ("외식",                 "16"),
        "문화":        ("문화/엔터",            "11"),
        "Luxury":      ("백화점/아울렛/면세점", "4"),
        "Gourmet":     ("외식",                 "16"),
        "M포인트 교환":("기타",                 "22"),
        "M포인트":     ("기타",                 "22"),
    }

    def _norm(s): return re.sub(r'\s+', ' ', s).strip()

    result = []
    blocks = re.split(
        r'\n(?=' + AREA_HEADER_RE.pattern.strip('^()$') + r'\n)',
        target_content, flags=re.MULTILINE
    )
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        first_line = _norm(block.split("\n")[0])
        if first_line not in CAT_MAP:
            continue
        cat_name, cat_id = CAT_MAP[first_line]

        merchant_lines = []
        for l in block.split("\n")[1:]:
            l2 = l.strip().lstrip("-*").strip()
            if not l2:
                continue
            if any(kw in l2 for kw in ["선택 시", "마일리지형", "교환 불가",
                                        "바우처 사용 방법", "제공 및 사용", "[",
                                        "발급 첫해", "2차년도", "유효 기간"]):
                break
            merchant_lines.append(l2)
        tm = ", ".join(merchant_lines)
        tm = tm[:100] if len(tm) > 100 else tm

        bt = base_row.get("benefit_type", "서비스")
        ui_title = f"{cat_name} {bt}".strip()

        new_row = base_row.copy()
        new_row.update({
            "benefit_id":   f"{card_id}_B{seq_ref[0]:04d}",
            "category":     cat_name,
            "category_id":  cat_id,
            "target_merchants": tm,
            "ui_title":     ui_title,
        })
        seq_ref[0] += 1
        result.append(new_row)

    if len(result) < 2:
        return []

    merged: dict = {}
    merged_order = []
    for r in result:
        key = r["category"]
        if key not in merged:
            merged[key] = r.copy()
            merged_order.append(key)
        else:
            existing_tm = merged[key].get("target_merchants", "")
            new_tm = r.get("target_merchants", "")
            combined = (existing_tm + ", " + new_tm).strip(", ")
            merged[key]["target_merchants"] = combined[:100]
    result = [merged[k] for k in merged_order]

    return result if len(result) >= 1 else []


# ─────────────────────────────────────────────
# [대상점] Python 처리
# ─────────────────────────────────────────────
def _split_by_daesangjeom(base_row: dict, content: str, seq_ref: list, card_id: str) -> list:
    block_match = re.search(r'\[?대상점\]?\n(.*?)(?:\n\n|\n\[|$)', content, re.DOTALL)
    if not block_match:
        return []

    block_text = block_match.group(1).strip()
    lines = [l.strip().lstrip("-").strip() for l in block_text.split("\n") if l.strip()]

    EXCLUDE_KW = ["가맹점은", "한도", "미만", "이상", "이용 건", "앱 이용",
                  "신규 발급", "별도 가맹점", "온라인 선물",
                  "혜택 제외", "적용 제외", "제외됩니다", "키오스크",
                  "에 한해", "홈페이지 및 앱", "도메인으로", "지침에 따름",
                  "운영 시간", "실물 카드", "가상 카드", "본인 탑승", "별도 정산",
                  "앱에서 결제한 경우", "결제한 경우", "구분되어 기본 혜택"]
    entries = []
    for line in lines:
        if any(kw in line for kw in EXCLUDE_KW):
            continue
        if re.match(r'^[가-힣a-zA-Z0-9/·\s,\.\(\)&+\-]+(\s*:\s*.+)?$', line):
            entries.append(line)

    if len(entries) < 2:
        return []

    gml, gml_unit = "", ""
    gml_match = re.search(
        r'대상점\s*통합해\s*(?:최대\s*)?월\s*([\d,]+(?:천|만)?)\s*(원|M?포인트)',
        content
    )
    if gml_match:
        raw_num      = gml_match.group(1)
        gml_unit_raw = gml_match.group(2)
        gml_unit = "포인트" if "포인트" in gml_unit_raw else "원"
        if "만" in raw_num:
            gml = str(int(raw_num.replace("만", "").replace(",", "")) * 10000)
        elif "천" in raw_num:
            gml = str(int(raw_num.replace("천", "").replace(",", "")) * 1000)
        else:
            gml = raw_num.replace(",", "")

    max_count_val = ""
    mc_match = re.search(r'(?:이용\s*한도|통합|합산).*?월\s*(\d+)\s*회', content)
    if mc_match:
        max_count_val = mc_match.group(1)

    GENRE_CAT_MAP = [
        ("편의점",       "편의점",             "13"),
        ("커피전문점",   "카페/베이커리",       "14"),
        ("카페",         "카페/베이커리",       "14"),
        ("베이커리",     "카페/베이커리",       "14"),
        ("패스트푸드",   "외식",               "16"),
        ("일반음식점",   "외식",               "16"),
        ("음식점",       "외식",               "16"),
        ("이동통신 요금", "생활비",             "12"),
        ("이동통신",     "생활비",             "12"),
        ("대중교통",     "대중교통/택시",       "5"),
        ("택시",         "대중교통/택시",       "5"),
        ("주유",         "자동차/주유",         "6"),
        ("마트",         "슈퍼마켓/생활잡화",   "3"),
        ("슈퍼마켓",     "슈퍼마켓/생활잡화",   "3"),
        ("백화점",       "백화점/아울렛/면세점", "4"),
        ("아울렛",       "백화점/아울렛/면세점", "4"),
        ("면세점",       "백화점/아울렛/면세점", "4"),
        ("배달",         "배달",               "15"),
        ("항공",         "항공",               "18"),
        ("인천국제공항", "항공",               "18"),
        ("워커힐",       "여행/숙박",           "17"),
        ("더 플라자",    "여행/숙박",           "17"),
        ("그랜드 워커힐","여행/숙박",           "17"),
        ("비스타 워커힐","여행/숙박",           "17"),
        ("호텔",         "여행/숙박",           "17"),
        ("쇼핑",         "온라인쇼핑",          "1"),
    ]

    result = []
    for entry in entries:
        if ":" in entry:
            업종, merchants = entry.split(":", 1)
            업종 = 업종.strip()
            merchants = merchants.strip()
        else:
            업종 = entry.strip()
            merchants = entry.strip()

        cat_name, cat_id = "기타", "22"
        for genre_kw, cn, cid in GENRE_CAT_MAP:
            if genre_kw in 업종:
                cat_name, cat_id = cn, cid
                break
        if cat_name == "기타":
            search_text = f"{업종} {merchants}"
            for cn, keywords in CATEGORY_KEYWORD_MAP:
                if any(kw in search_text for kw in keywords):
                    cat_name = cn
                    cat_id   = str(CATEGORY_ID_MAP.get(cn, 22))
                    break

        tm = entry if len(entry) <= 50 else entry[:50]

        bv = base_row.get("benefit_value", "")
        bu = base_row.get("benefit_unit", "")
        bt = base_row.get("benefit_type", "")
        ui_title = f"{cat_name} {bv}{bu} {bt}".strip()

        new_row = base_row.copy()
        new_row.update({
            "benefit_id":           f"{card_id}_B{seq_ref[0]:04d}",
            "category":             cat_name,
            "category_id":          cat_id,
            "target_merchants":     tm,
            "ui_title":             ui_title,
            "group_max_limit":      gml,
            "group_max_limit_unit": gml_unit,
            "max_limit":            "",
            "max_limit_unit":       "",
            "max_count":            max_count_val,
        })
        seq_ref[0] += 1
        result.append(new_row)

    merged: dict = {}
    merged_order = []
    for r in result:
        key = r["category"]
        if key not in merged:
            merged[key] = r.copy()
            merged_order.append(key)
        else:
            tm_ex = merged[key].get("target_merchants", "")
            tm_new = r.get("target_merchants", "")
            combined = (tm_ex + ", " + tm_new).strip(", ")
            merged[key]["target_merchants"] = combined[:100]

    merged_list = [merged[k] for k in merged_order]
    base_id = int(merged_list[0]["benefit_id"].split("_B")[1]) if merged_list else seq_ref[0]
    for i, r in enumerate(merged_list):
        r["benefit_id"] = f"{card_id}_B{base_id + i:04d}"
    seq_ref[0] = base_id + len(merged_list)

    return merged_list


# ─────────────────────────────────────────────
# 카테고리 나열형 섹션 (일상 사용처)
# ─────────────────────────────────────────────
def _parse_usage_place_section(section: dict, card_id: str, seq_ref: list,
                                group: str, row_type: str, forced_benefit_type: str) -> list:
    content      = section["content"]
    benefit_type = forced_benefit_type or "포인트"
    updated_at   = now_date()

    _up_parts = USAGE_PLACE_PROMPT.split("# 입력\n", 1)
    _up_static = _up_parts[0] if len(_up_parts) > 1 else ""
    _up_system_cached = USAGE_PLACE_SYSTEM + "\n\n" + _up_static
    _up_user = f"# 입력\n{content}"
    resp = call_claude(_up_system_cached, _up_user, max_tokens=2000)

    try:
        claude_rows = parse_json_response(resp)
    except Exception as e:
        print(f"    ! [일상 사용처] JSON 파싱 실패: {e}")
        print(f"    ! Claude 응답: {resp[:300]}")
        return []

    _CAT_ALIAS = {
        "커피/베이커리": "카페/베이커리", "베이커리/커피": "카페/베이커리",
        "배달/간편식": "배달", "간편식": "배달",
        "편의점/마트": "편의점", "마트/편의점": "슈퍼마켓/생활잡화",
        "편의/쇼핑": "슈퍼마켓/생활잡화",
        "주유/정비": "자동차/주유",
        "영화": "문화/엔터",
        "여행/레저": "여행/숙박",
        "쇼핑": "온라인쇼핑", "패션": "패션/뷰티", "뷰티": "패션/뷰티",
        "여행/면세점": "여행/숙박", "면세점": "백화점/아울렛/면세점",
        "레저/테마파크": "레저/스포츠", "영화/음악": "문화/엔터",
        "교육/도서": "교육/육아", "보험/금융": "생활비",
        "자동차": "자동차/주유", "대중교통": "대중교통/택시",
    }

    result = []
    for row in claude_rows:
        raw_cat  = row.get("category", "")
        cat_name = _CAT_ALIAS.get(raw_cat, raw_cat) or "기타"
        tm = row.get("target_merchants", "") or raw_cat or cat_name
        result.append({
            "benefit_id":           f"{card_id}_B{seq_ref[0]:04d}",
            "card_id":              card_id,
            "row_type":             row_type,
            "benefit_group":        group,
            "benefit_title":        section["title"] or group,
            "category":             cat_name,
            "category_id":          str(row.get("category_id", CATEGORY_ID_MAP.get(cat_name, 22))),
            "on_offline":           _determine_on_offline(section["content"], cat_name, tm),
            "benefit_type":         benefit_type,
            "benefit_value":        "",
            "benefit_unit":         "",
            "target_merchants":     tm,
            "performance_level":    "",
            "performance_min":      "",
            "performance_max":      "",
            "min_amount":           "",
            "max_count":            "",
            "max_limit":            "",
            "max_limit_unit":       "",
            "group_max_limit":      "",
            "group_max_limit_unit": "",
            "unit_amount":          "",
            "benefit_content":      format_benefit_content(content),
            "ui_title":             f"{cat_name} M포인트 사용",
            "ui_content":           format_benefit_content(content),
            "ui_table":             "",
            "updated_at":           updated_at,
        })
        seq_ref[0] += 1

    return result


# ─────────────────────────────────────────────
# 메인 파싱 함수
# ─────────────────────────────────────────────
def parse_benefit_section(section: dict, card_id: str, seq_ref: list) -> list:
    group               = section.get("group", "")
    title               = section["title"] or group
    content             = section["content"]
    slide_html          = section.get("slide_html", "")
    forced_benefit_type = section.get("forced_benefit_type", "")
    ui_content_built    = build_ui_from_html(title, slide_html)

    _NOTICE_SEP = re.compile(
        r'\n\s*\[혜택\s*제공\s*기준\]|\n\s*\[공통\s*유의사항\]'
        r'|\n\s*\[이용\s*금액\s*산정|\n\s*유의사항\s*\n'
        r'|\n\s*\[.*?공통\s*유의사항.*?\]'
        r'|\n\s*\[혜택\s*유의사항\]'
    )
    _sep_match   = _NOTICE_SEP.search(content)
    benefit_only = content[:_sep_match.start()].strip() if _sep_match else content

    if section.get("is_안내"):
        row_type = "안내"
    elif section["is_notice"]:
        row_type = "유의사항"
    else:
        row_type = "주요혜택"

    if row_type == "안내":
        row = {
            "benefit_id":           f"{card_id}_B{seq_ref[0]:04d}",
            "card_id":              card_id,
            "row_type":             "안내",
            "benefit_group":        group,
            "benefit_title":        title,
            "category":             "기타",
            "category_id":          "22",
            "on_offline":           "Both",
            "benefit_type":         "서비스",
            "benefit_value":        "",
            "benefit_unit":         "",
            "target_merchants":     "",
            "performance_level":    "",
            "performance_min":      "",
            "performance_max":      "",
            "min_amount":           "",
            "max_count":            "",
            "max_limit":            "",
            "max_limit_unit":       "",
            "group_max_limit":      "",
            "group_max_limit_unit": "",
            "unit_amount":          "",
            "benefit_content":      format_benefit_content(content),
            "ui_title":             title,
            "ui_content":           format_benefit_content(content),
            "ui_table":             "",
            "updated_at":           now_date(),
        }
        seq_ref[0] += 1
        return [row]

    _has_tier = bool(re.search(r'할인\s*한도|이상\s*시\s*월\s*\d', benefit_only))
    if re.search(r'\[?대상점\]?\n', benefit_only) and not _has_tier:
        base_row = _make_base_row(card_id, group, title, row_type,
                                  forced_benefit_type, content, seq_ref)
        base_row["_ui_built"] = ui_content_built
        _fill_base_numerics(base_row, benefit_only, forced_benefit_type)
        seq_ref[0] += 1
        split_rows = _split_by_daesangjeom(base_row, benefit_only, seq_ref, card_id)
        if split_rows:
            for r in split_rows:
                r["_ui_built"] = ui_content_built
            print(f"         -> [대상점] Python 처리: {len(split_rows)}행")
            return _finalize(split_rows, content)
        _apply_category_keyword(base_row, benefit_only)
        return _finalize([base_row], content)

    if re.search(r'\[?대상\s*영역\]?\n', benefit_only):
        base_row = _make_base_row(card_id, group, title, row_type,
                                  forced_benefit_type, content, seq_ref)
        _fill_base_numerics(base_row, benefit_only, forced_benefit_type)
        seq_ref[0] += 1
        split_rows = _split_by_daesangyeok(base_row, benefit_only, seq_ref, card_id)
        if split_rows:
            print(f"         -> [대상 영역] Python 처리: {len(split_rows)}행")
            return _finalize(split_rows, content)
        _apply_category_keyword(base_row, benefit_only)
        return _finalize([base_row], content)

    if title in USAGE_PLACE_TITLES:
        return _parse_usage_place_section(section, card_id, seq_ref,
                                          group, row_type, forced_benefit_type)

    _benefit_system_cached = _build_benefit_system()
    user_msg = _make_benefit_user(
        card_id=card_id,
        section_title=title,
        row_type=row_type,
        forced_benefit_type=forced_benefit_type if forced_benefit_type else "내용 기반으로 판단",
        section_content=benefit_only[:5000],
        updated_at=now_date(),
    )
    resp = call_claude(_benefit_system_cached, user_msg)

    try:
        rows = parse_json_response(resp)
    except Exception as e:
        print(f"    ! [{title}] JSON 파싱 실패: {e}")
        print(f"    ! Claude 응답 앞부분: {resp[:500]}")
        return []

    if not rows:
        print(f"    ! [{title}] Claude가 빈 배열 반환: {resp[:300]}")
        return []

    KO_TO_EN = {
        "카테고리": "category", "카테고리ID": "category_id", "카테고리_id": "category_id",
        "혜택타입": "benefit_type", "혜택유형": "benefit_type",
        "혜택수치": "benefit_value", "수치": "benefit_value",
        "단위": "benefit_unit", "혜택단위": "benefit_unit",
        "전월실적": "performance_min", "전월실적최솟값": "performance_min",
        "월한도": "max_limit", "통합한도": "group_max_limit",
        "대상가맹점": "target_merchants", "가맹점": "target_merchants",
        "온오프라인": "on_offline",
        "혜택내용": "benefit_content", "내용": "benefit_content",
        "표시제목": "ui_title", "제목": "ui_title",
    }
    rows = [
        {KO_TO_EN.get(k, k): v for k, v in row.items()}
        if any(k in KO_TO_EN for k in row)
        else row
        for row in rows
    ]

    result = []
    for row in rows:
        row["card_id"]       = card_id
        row["row_type"]      = row_type
        row["benefit_group"] = group
        row["benefit_title"] = title
        row["benefit_id"]    = f"{card_id}_B{seq_ref[0]:04d}"
        seq_ref[0] += 1

        if forced_benefit_type:
            row["benefit_type"] = forced_benefit_type

        if row.get("benefit_type") == "서비스":
            for f in ["benefit_value", "benefit_unit",
                      "min_amount", "max_count",
                      "max_limit", "max_limit_unit",
                      "group_max_limit", "group_max_limit_unit", "unit_amount"]:
                row[f] = ""
            pm = row.get("performance_min", "")
            if str(pm) in ("0", "", "null", "None"):
                row["performance_min"]   = ""
                row["performance_max"]   = ""
                row["performance_level"] = ""

        _fmt = format_benefit_content(content)
        row["benefit_content"] = _fmt
        row["ui_content"]      = _fmt
        row["ui_table"]        = ""

        cats = [c.strip() for c in str(row.get("category", "")).split(",") if c.strip()]
        if len(cats) > 1:
            cats = [cats[0]]
        _ID_TO_CAT = {str(v): k for k, v in CATEGORY_ID_MAP.items()}
        if cats and cats[0].isdigit():
            cats = [_ID_TO_CAT.get(cats[0], "기타")]
        if not cats or not cats[0] or cats[0] == "기타":
            _apply_category_keyword(row, benefit_only)
            cats = [row.get("category", "기타")]

        _CAT_NORMALIZE = {
            '대중교통': '대중교통/택시',
            '자동차':   '자동차/주유',
            '슈퍼마켓': '슈퍼마켓/생활잡화',
            '카페':     '카페/베이커리',
        }
        if cats and cats[0] in _CAT_NORMALIZE:
            cats = [_CAT_NORMALIZE[cats[0]]]

        cat_final = cats[0] if cats and cats[0] else "기타"
        row["category"]    = cat_final
        row["category_id"] = str(CATEGORY_ID_MAP.get(cat_final, 22))

        for f in ["benefit_value", "performance_min", "performance_max",
                  "min_amount", "max_count", "max_limit", "group_max_limit", "unit_amount"]:
            if row.get(f) in (None, "null", "None"):
                row[f] = ""

        pm = row.get("performance_min", "")
        if str(pm).isdigit() and int(pm) > 2000000:
            actual = re.findall(r'전월\s*이용\s*금액\s*(\d+)\s*만원\s*이상', content)
            if actual:
                row["performance_min"] = str(min(int(x) * 10000 for x in actual))
            else:
                row["performance_min"] = str(int(pm) // 10)
        pmax = row.get("performance_max", "")
        if str(pmax).isdigit() and int(pmax) > 2000000:
            actual_max = re.findall(r'(\d+)\s*만원\s*미만', content)
            if actual_max:
                row["performance_max"] = str(int(actual_max[0]) * 10000)
            else:
                row["performance_max"] = str(int(pmax) // 10)

        if row.get("benefit_group") in ("연간 보너스",) and row.get("benefit_type") == "서비스":
            row["performance_min"] = ""
            row["performance_level"] = ""

        if not row.get("on_offline"):
            row["on_offline"] = _determine_on_offline(
                content,
                row.get("category", ""),
                row.get("target_merchants", "")
            )
        if not row.get("ui_title"):
            cat = row.get("category", "")
            bv  = row.get("benefit_value", "")
            bu  = row.get("benefit_unit", "")
            bt  = row.get("benefit_type", "")
            row["ui_title"] = f"{cat} {bv}{bu} {bt}".strip() if bv else f"{cat} {bt}".strip()

        tm = str(row.get("target_merchants", "")).split("\n")[0].strip()
        row["target_merchants"] = tm if len(tm) <= 50 else ""

        row.setdefault("updated_at", now_date())
        result.append(row)

    if len(result) > 1:
        ml_values = [r.get("max_limit", "") for r in result]
        if all(v == ml_values[0] and v != "" for v in ml_values):
            for r in result:
                r["group_max_limit"]      = r["max_limit"]
                r["group_max_limit_unit"] = r.get("max_limit_unit", "")
                r["max_limit"]      = ""
                r["max_limit_unit"] = ""

    if len(result) == 1 and result[0].get("benefit_type") == "서비스":
        seq_ref[0] -= 1
        split_rows = _split_service_by_category(result[0], benefit_only, seq_ref, card_id)
        if split_rows:
            print(f"         -> 서비스 카테고리 분리: {len(split_rows)}행")
            result = split_rows
        else:
            seq_ref[0] += 1

    if forced_benefit_type == "서비스" or (result and result[0].get("benefit_type") == "서비스"):
        if len(result) > 1:
            all_same_content = len({r.get("benefit_content", "") for r in result}) == 1
            if not all_same_content:
                result = result[:1]

    _benefit_first = content.split('\n')[0].strip()
    for r in result:
        ui = r.get("ui_title", "")
        if r.get("category") == "기타" and ui.startswith("기타 "):
            bv = r.get("benefit_value", "")
            bu = r.get("benefit_unit", "")
            bt = r.get("benefit_type", "")
            if "국내외 가맹점" in _benefit_first and "Apple Pay" in _benefit_first:
                subject = "Apple Pay 이용 금액"
            elif "국내외 가맹점" in _benefit_first:
                subject = "국내외 가맹점"
            else:
                subject = _benefit_first.split(' 이용 금액')[0].split('시 ')[-1].strip()[:20]
            r["ui_title"] = f"{subject} {bv}{bu} {bt}".strip() if bv and bu else f"{subject} {bt}".strip()

    if len(result) > 1:
        ref_value = next((r["benefit_value"] for r in result if r.get("benefit_value")), "")
        ref_unit  = next((r["benefit_unit"]  for r in result if r.get("benefit_unit")),  "")
        ref_type  = next((r["benefit_type"]  for r in result if r.get("benefit_type")),  "")
        for r in result:
            if not r.get("benefit_value") and ref_value:
                r["benefit_value"] = ref_value
            if not r.get("benefit_unit") and ref_unit:
                r["benefit_unit"]  = ref_unit
            if not r.get("benefit_type") and ref_type:
                r["benefit_type"]  = ref_type

    return result
