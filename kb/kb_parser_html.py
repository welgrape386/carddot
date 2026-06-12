import re
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from bs4 import BeautifulSoup

from kb_parser_base import (
    SKIP_BOX_PATTERNS, CONTENT_SKIP_PATTERNS, PERF_SKIP_PATTERNS,
    SKIP_LINE_PATTERNS, NOTICE_BOX_PATTERNS,
    CATEGORY_KEYWORD_MAP, CATEGORY_ID_MAP, _KR_AMOUNT_RE,
)


# ─────────────────────────────────────────────
# 스킵 판별
# ─────────────────────────────────────────────
def box_is_skip(text: str) -> bool:
    if len(text.strip()) < 2:
        return True
    return any(re.search(p, text) for p in SKIP_BOX_PATTERNS)

def box_is_notice(text: str) -> bool:
    return any(re.search(p, text) for p in NOTICE_BOX_PATTERNS)

def _key_has_subrows(key: str, full_table_html: str) -> bool:
    if not full_table_html:
        return False
    return bool(re.search(rf'<th[^>]*rowspan[^>]*>{re.escape(key)}</th>', full_table_html))

def _is_popup_box(box) -> bool:
    parent = box.parent
    return bool(parent and "titArea" in (parent.get("class") or []))


# ─────────────────────────────────────────────
# 탭 한도 정보 추출
# ─────────────────────────────────────────────
def _extract_tab_limit_info(tab) -> tuple[str, dict, str]:
    full_text = tab.get_text("\n", strip=True)

    perf_lines = []
    for line in full_text.split("\n"):
        line = line.strip()
        if re.search(r'전월\s*이용실적\s*\d+만원\s*이상', line) and len(line) < 100:
            if not any(pat.search(line) for pat in SKIP_LINE_PATTERNS):
                perf_lines.append(line)
    perf_condition = perf_lines[0] if perf_lines else ""

    provision_conditions = []
    for table in tab.find_all("table"):
        hdr_txt = table.get_text(" ", strip=True)
        if "제공 조건" not in hdr_txt:
            continue
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            texts = [c.get_text(" ", strip=True) for c in cells]
            for t in texts:
                if re.search(r'건당|이용\s*시|이상\s*이용', t) and t not in provision_conditions:
                    provision_conditions.append(t)
    if provision_conditions:
        cond_text = provision_conditions[0]
        if perf_condition:
            perf_condition = f"{perf_condition} / {cond_text}"
        else:
            perf_condition = cond_text

    limit_map = {}
    for table in tab.find_all("table"):
        header_text = table.get_text(" ", strip=True)
        if "월 할인한도" not in header_text and "월 할인 한도" not in header_text and "할인율" not in header_text:
            continue
        if "통합할인한도" in header_text[:60]:
            continue

        all_trs = [tr for tr in table.find_all("tr") if tr.find_all(["th", "td"])]

        header_rows_html = []
        data_trs = []
        for idx, tr in enumerate(all_trs):
            cells = tr.find_all(["th", "td"])
            first_txt = cells[0].get_text(" ", strip=True)
            is_header = (idx == 0 or
                         any(k in first_txt for k in ["구분", "할인율", "전월", "구간", "만원이상", "만원 이상"]) or
                         all(re.search(r'\d+만원|구간|이상', c.get_text(" ", strip=True)) for c in cells))
            if is_header:
                cells_html = []
                for cell in cells:
                    cs = f' colspan="{cell.get("colspan")}"' if cell.get("colspan") else ""
                    rs = f' rowspan="{cell.get("rowspan")}"' if cell.get("rowspan") else ""
                    cells_html.append(f"<th{cs}{rs}>{cell.get_text(' ', strip=True)}</th>")
                header_rows_html.append(f'<tr>{"".join(cells_html)}</tr>')
            else:
                data_trs.append(tr)

        if not data_trs:
            continue

        tier_labels = []
        for th in table.find_all("th"):
            m = re.search(r'(\d+)만원\s*이상', th.get_text(" ", strip=True))
            if m and m.group(1) not in [t[0] for t in tier_labels]:
                tier_labels.append((m.group(1), int(m.group(1)) * 10000))
        tier_labels.sort(key=lambda x: x[1])

        rowspan_carry = {}
        parsed = []

        for tr in data_trs:
            cells = tr.find_all(["th", "td"])
            cell_iter = iter(cells)
            row_values = []
            col = 0
            while col < 10:
                if col in rowspan_carry:
                    val, rem = rowspan_carry[col]
                    row_values.append(("carry", val, 1, 1))
                    rowspan_carry[col] = (val, rem - 1)
                    if rowspan_carry[col][1] <= 0:
                        del rowspan_carry[col]
                    col += 1
                else:
                    cell = next(cell_iter, None)
                    if cell is None:
                        break
                    rs = int(cell.get("rowspan", 1))
                    cs = int(cell.get("colspan", 1))
                    val = re.sub(r'\s*\(건당.*?\)', '', cell.get_text(" ", strip=True)).strip()
                    if rs > 1:
                        rowspan_carry[col] = (val, rs - 1)
                    row_values.append(("cell", val, cs, rs))
                    col += cs

            if not row_values:
                continue

            key = row_values[0][1]
            if not key:
                continue

            rate = ""
            limit_vals = []
            sub_items = []
            is_carry_row = False
            for rv_type, val, cs, rs in row_values[1:]:
                if re.search(r'\d+\s*%|\d+원/[Ll리터]', val):
                    rate = val
                elif val and _KR_AMOUNT_RE.search(re.sub(r'\(건당.*?\)|연\s*\d+[만천]\s*원|\d+원/[Ll리터]', '', val)):
                    limit_vals.append((re.sub(r'\s*\(건당.*?\)', '', val).strip(), cs, rs))
                    if rv_type == "carry":
                        is_carry_row = True
                elif val:
                    sub_items.append(val)

            parsed.append({
                "key": key,
                "rate": rate,
                "limit_vals": limit_vals,
                "sub_items": sub_items,
                "is_carry": is_carry_row,
            })

        if not parsed:
            continue

        rowspan_groups = []
        current_group = None
        for p in parsed:
            if p["is_carry"] and current_group:
                current_group["keys"].append(p["key"])
            else:
                if current_group:
                    rowspan_groups.append(current_group)
                current_group = {
                    "keys": [p["key"]],
                    "limit_vals": p["limit_vals"],
                    "rate": p["rate"],
                }
        if current_group:
            rowspan_groups.append(current_group)

        has_rowspan_group = any(len(g["keys"]) > 1 for g in rowspan_groups)

        if has_rowspan_group:
            for grp in rowspan_groups:
                keys = list(dict.fromkeys(grp["keys"]))
                lvs = grp["limit_vals"]
                if not lvs:
                    continue
                lv = lvs[0][0]
                lcs = lvs[0][1]
                is_same_tiers = (lcs >= 2) or (len(tier_labels) <= 1)

                grp_sub = " ".join(
                    item for p in parsed if p["key"] in grp["keys"]
                    for item in p.get("sub_items", [])
                )
                all_parts = []
                for k in keys:
                    all_parts += [w.strip() for w in re.split(r'[,·]', k) if w.strip()]
                all_parts += [w.strip() for w in re.split(r'[,·]', grp_sub) if w.strip()]
                cat_ids_grp = set()
                for part in all_parts:
                    for cat_name, keywords in CATEGORY_KEYWORD_MAP:
                        if any(kw in part for kw in keywords):
                            cat_ids_grp.add(CATEGORY_ID_MAP.get(cat_name, 22))
                            break
                is_group = len(keys) > 1 or len(cat_ids_grp) > 1
                keys_str = " / ".join(keys)

                if is_same_tiers:
                    lim_hint = "group_max_limit" if is_group else "max_limit"
                    if tier_labels:
                        tier_lines_ai = [
                            f"전월 이용실적 {t[0]}만원 이상\n* {keys_str} : 월 할인한도 {lv} ({lim_hint})"
                            for t in tier_labels
                        ]
                        tier_lines_ui = [
                            f"전월 이용실적 {t[0]}만원 이상\n* {keys_str} : 월 할인한도 {lv}"
                            for t in tier_labels
                        ]
                        summary_ai = "\n".join(tier_lines_ai) + "\n※ 현재 섹션만 행 생성할 것"
                        summary_ui = "\n".join(tier_lines_ui)
                    else:
                        summary_ai = f"* {keys_str} : 월 할인한도 {lv} ({lim_hint})\n※ 현재 섹션만 행 생성할 것"
                        summary_ui = f"* {keys_str} : 월 할인한도 {lv}"
                else:
                    tier_lines_ai, tier_lines_ui = [], []
                    for t_label, _ in tier_labels:
                        lim_hint = "group_max_limit" if is_group else "max_limit"
                        tier_lines_ai.append(f"전월 이용실적 {t_label}만원 이상\n* {keys_str} : 월 할인한도 {lv} ({lim_hint})")
                        tier_lines_ui.append(f"전월 이용실적 {t_label}만원 이상\n* {keys_str} : 월 할인한도 {lv}")
                    summary_ai = "\n".join(tier_lines_ai) + "\n※ 현재 섹션만 행 생성할 것"
                    summary_ui = "\n".join(tier_lines_ui)

                for key in keys:
                    limit_map[key] = {
                        "table_html": "",
                        "summary_ai": summary_ai,
                        "summary_ui": summary_ui,
                        "is_group": is_group,
                        "is_same_all_tiers": is_same_tiers,
                        "limit_value": lv,
                    }
        else:
            for p in parsed:
                key = p["key"]
                key_no_num = re.sub(r'\d,\d', 'X', key)
                sub_items_str = " ".join(p.get("sub_items", []))
                sub_no_num = re.sub(r'\d,\d', 'X', sub_items_str)
                has_comma = ("," in key_no_num or "·" in key) or "," in sub_no_num

                if has_comma:
                    parts = [w.strip() for w in re.split(r'[,·]', key) if w.strip()]
                    cat_ids = set()
                    for part in parts:
                        for cat_name, keywords in CATEGORY_KEYWORD_MAP:
                            if any(kw in part for kw in keywords):
                                cat_ids.add(CATEGORY_ID_MAP.get(cat_name, 22))
                                break
                    is_group = len(cat_ids) > 1
                else:
                    is_group = False

                is_same_tiers = any(cs >= 2 for _, cs, _ in p["limit_vals"]) or len(tier_labels) <= 1
                lv = p["limit_vals"][0][0] if p["limit_vals"] else ""

                if is_group and is_same_tiers and lv:
                    perf_hint = f"전월 이용실적 {tier_labels[0][0]}만원 이상" if tier_labels else ""
                    keys_str = " / ".join(k.strip() for k in re.split(r'[,、]', key) if k.strip())
                    if tier_labels:
                        tier_lines_ai = [
                            f"전월 이용실적 {t[0]}만원 이상\n* {keys_str} : 월 할인한도 {lv} (group_max_limit)"
                            for t in tier_labels
                        ]
                        tier_lines_ui = [
                            f"전월 이용실적 {t[0]}만원 이상\n* {keys_str} : 월 할인한도 {lv}"
                            for t in tier_labels
                        ]
                        summary_ai = "\n".join(tier_lines_ai) + "\n※ 현재 섹션만 행 생성할 것"
                        summary_ui = "\n".join(tier_lines_ui)
                    else:
                        summary_ai = f"* {keys_str} : 월 할인한도 {lv} (group_max_limit)\n※ 현재 섹션만 행 생성할 것"
                    summary_ui = f"{perf_hint}\n* {keys_str} : 월 할인한도 {lv}"
                    limit_map[key] = {
                        "table_html": "",
                        "summary_ai": summary_ai,
                        "summary_ui": summary_ui,
                        "is_group": True,
                        "is_same_all_tiers": True,
                        "limit_value": lv,
                    }
                else:
                    row_cells_html = [f"<td>{key}</td>"]
                    if p["rate"]:
                        row_cells_html.append(f"<td>{p['rate']}</td>")
                    for lv2, lcs, lrs in p["limit_vals"]:
                        cs_attr = f' colspan="{lcs}"' if lcs > 1 else ""
                        rs_attr = f' rowspan="{lrs}"' if lrs > 1 else ""
                        row_cells_html.append(f"<td{cs_attr}{rs_attr}>{lv2}</td>")
                    data_row_html = f'<tr>{"".join(row_cells_html)}</tr>'
                    mini_table = f'<table class="benefit-table">{"".join(header_rows_html)}{data_row_html}</table>'
                    limit_map[key] = {
                        "table_html": mini_table,
                        "summary_ai": "",
                        "summary_ui": "",
                        "is_group": is_group,
                        "is_same_all_tiers": is_same_tiers,
                        "limit_value": lv,
                    }

    if not perf_condition:
        for table in tab.find_all("table"):
            tbl_txt = table.get_text(" ", strip=True)
            if "통합할인한도" in tbl_txt[:60]:
                min_tier = None
                for th in table.find_all("th"):
                    m = re.search(r'(\d+)만원\s*이상', th.get_text(" ", strip=True))
                    if m:
                        v = int(m.group(1))
                        if min_tier is None or v < min_tier:
                            min_tier = v
                if min_tier:
                    perf_condition = f"전월 이용실적 {min_tier}만원 이상"
                break
            tiers = []
            for th in table.find_all("th"):
                m = re.search(r'(\d+)만원\s*이상', th.get_text(" ", strip=True))
                if m and m.group(1) not in [t[0] for t in tiers]:
                    tiers.append((m.group(1), int(m.group(1)) * 10000))
            if tiers:
                tiers.sort(key=lambda x: x[1])
                perf_condition = f"전월 이용실적 {' / '.join(t[0]+'만원이상' for t in tiers)} 구간별 적용"
                break

    full_table_html = ""
    for table in tab.find_all("table"):
        header_text = table.get_text(" ", strip=True)
        if ("월 할인한도" not in header_text and "월 할인 한도" not in header_text and "할인율" not in header_text):
            continue
        if "통합할인한도" in header_text[:60]:
            continue
        rows_html = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            cells_html = []
            for cell in cells:
                cs = f' colspan="{cell.get("colspan")}"' if cell.get("colspan") else ""
                rs = f' rowspan="{cell.get("rowspan")}"' if cell.get("rowspan") else ""
                cell_text = re.sub(r'\s+', ' ', cell.get_text(' ', strip=True)).strip()
                cells_html.append(f"<{cell.name}{cs}{rs}>{cell_text}</{cell.name}>")
            rows_html.append(f'<tr>{"".join(cells_html)}</tr>')
        if rows_html:
            full_table_html = f'<table class="benefit-table">{"".join(rows_html)}</table>'
            break

    return perf_condition, limit_map, full_table_html


# ─────────────────────────────────────────────
# 섹션 분리 헬퍼
# ─────────────────────────────────────────────
def _split_by_pack_labels(text: str) -> list[dict]:
    SPLIT_PATTERNS = [
        r'([가-힣a-zA-Z]+팩)(?:\(선택\))?',
        r'(\[[^\]]+\])\s*(?=\S)',
        r'(1st선택\s*서비스|2nd선택\s*서비스)',
    ]

    splits = []
    for pat in SPLIT_PATTERNS:
        for m in re.finditer(pat, text):
            splits.append((m.start(), m.group(1)))

    if len(splits) < 2:
        return []

    splits.sort(key=lambda x: x[0])
    raw = []
    for i, (start, label) in enumerate(splits):
        end = splits[i+1][0] if i+1 < len(splits) else len(text)
        content = text[start:end].strip()
        if len(content) > 10:
            raw.append({"group": label.strip("()[]"), "content": content})

    merged: dict = {}
    order = []
    for r in raw:
        g = r["group"]
        if g not in merged:
            merged[g] = r["content"]
            order.append(g)
        else:
            merged[g] += "\n" + r["content"]

    sections = []
    for g in order:
        sections.append({
            "group": g, "title": g,
            "content": merged[g], "is_notice": False,
        })
    return sections


def _extract_group_label(first_line: str, full_text: str) -> str:
    m = re.match(r'\[([^\]]+)\]', first_line)
    if m:
        return m.group(1).strip()

    m = re.search(r'([가-힣a-zA-Z]+팩)(?:\(선택\))?', first_line)
    if m:
        return m.group(1)

    m = re.search(r'(\d+(?:st|nd|rd|th)?선택|선택\s*\d+)', first_line, re.IGNORECASE)
    if m:
        return m.group(1)

    for kw in ["기본", "추가", "공통", "해외", "국내"]:
        if first_line.startswith(kw):
            return f"{kw} 혜택"

    return "기본 혜택"


# ─────────────────────────────────────────────
# ui_content 빌더
# ─────────────────────────────────────────────
def build_ui_content(box_html: str, title: str = "", filter_limit_tables: bool = True) -> str:
    soup = BeautifulSoup(box_html, "html.parser")
    lines = []
    seen_tables = set()
    seen_subtitles = set()
    seen_texts = set()

    BENEFIT_PATTERN = re.compile(r'\d+\s*%|\d[\d,]*\s*원\s*(할인|캐시백|적립)')
    SKIP_PATTERNS = re.compile(r'할인한도\s*안내|이용\s*조건|유의사항|확인사항|상세혜택\s*[>＞]')

    if title:
        lines.append(f"[{title}]")

    has_list = any(
        "listType1" in (ul.get("class") or [])
        for ul in soup.find_all("ul")
        if not ul.find_parent("table")
    )

    def _clean_text(t: str) -> str:
        t = re.sub(r'https?://\S+', '', t)
        t = re.sub(r'www\.\S+', '', t)
        t = re.sub(r'\(1회\s*최대\s*할인금액[^)]*\)', '', t)
        t = re.sub(r'\(\s*\)', '', t)
        t = re.sub(r'\(\s*[·,]\s*', '(', t)
        t = re.sub(r'\s{2,}', ' ', t)
        t = re.sub(r'\s+([·,)])', r'', t)
        t = re.sub(r'[\(（]\s*$', '', t)
        return t.strip()

    def _table_to_html(tbl) -> str:
        rows_html = []
        for tr in tbl.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            cells_html = []
            for cell in cells:
                cs = f' colspan="{cell.get("colspan")}"' if cell.get("colspan") else ""
                rs = f' rowspan="{cell.get("rowspan")}"' if cell.get("rowspan") else ""
                cell_text = re.sub(r'\s+', ' ', cell.get_text(' ', strip=True)).strip()
                cells_html.append(f"<{cell.name}{cs}{rs}>{cell_text}</{cell.name}>")
            rows_html.append(f'<tr>{"".join(cells_html)}</tr>')
        return f'<table class="benefit-table">{"".join(rows_html)}</table>' if rows_html else ""

    def _li_to_lines(li) -> list:
        result = []
        for br in li.find_all("br"):
            br.replace_with("\n")
        table_htmls = []
        for tbl in li.find_all("table"):
            tbl_t = tbl.get_text(" ", strip=True)
            if "요약" in tbl_t[:60] and any(k in tbl_t for k in ["월 할인 한도", "월 할인한도"]):
                tbl.decompose()
                continue
            tbl_html = _table_to_html(tbl)
            if tbl_html:
                key = tbl_t[:50]
                if key not in seen_tables:
                    seen_tables.add(key)
                    table_htmls.append(tbl_html)
            tbl.decompose()
        raw = li.get_text("\n", strip=False)
        raw = re.sub(r'\n[ \t]+', ' ', raw)
        for part in raw.split("\n"):
            part = _clean_text(part)
            if not part or len(part) <= 2 or re.match(r'^[·,)\s)）]+$', part):
                continue
            if re.match(r'^[)）]', part):
                continue
            if any(p.search(part) for p in CONTENT_SKIP_PATTERNS):
                continue
            if part.startswith(("※", "*", "＊")):
                result.append(part)
            elif result:
                result.append(f"  {part}")
            else:
                result.append(f"- {part}")
        result.extend(table_htmls)
        return result

    def _try_subtitle(elem) -> bool:
        tag_classes = ' '.join(elem.get("class", []))
        is_subtitle = (
            elem.name in ["h2", "h3", "h4"] or
            bool(re.search(r'^(sTit|txt)$', tag_classes)) or
            'titDep' in tag_classes
        )
        if not is_subtitle:
            return False
        if elem.find_parent("table"):
            return True
        t = elem.get_text(" ", strip=True)
        if not t or t == title or len(t) < 3 or len(t) > 80:
            return True
        if SKIP_PATTERNS.search(t):
            return True
        is_trusted = bool(re.search(r'^(sTit|txt)$', tag_classes) or 'titDep' in tag_classes)
        if not is_trusted and not BENEFIT_PATTERN.search(t):
            return True
        t_key = re.sub(r'\s+', '', t)[:30]
        if t_key not in seen_subtitles:
            seen_subtitles.add(t_key)
            lines.append(f"[{t}]")
        return True

    def _try_table(elem) -> bool:
        if elem.name != "table":
            return False
        if elem.find_parent("table"):
            return True
        tbl_text = elem.get_text(" ", strip=True)
        key = tbl_text[:50]
        if key in seen_tables:
            return True
        if filter_limit_tables and re.search(r'서비스\s*요약', tbl_text[:80]):
            return True
        if re.search(r'통합할인한도', tbl_text[:80]):
            return True
        if filter_limit_tables and any(k in tbl_text[:120] for k in ["월 할인한도", "월 할인 한도", "할인율", "전월 이용실적별", "전월 실적별", "서비스요약"]):
            return True
        seen_tables.add(key)
        tbl_html = _table_to_html(elem)
        if tbl_html:
            lines.append(tbl_html)
        return True

    def _try_text(elem) -> bool:
        if elem.name not in ["p", "li", "strong"]:
            return False
        if elem.name == "li" and has_list:
            return False
        if elem.find_parent("table") or elem.find_parent("ul", class_="listType1"):
            return False
        t = _clean_text(re.sub(r'\s+', ' ', elem.get_text(" ", strip=True)))
        if not t or len(t) <= 5 or t == (title or ""):
            return False
        if re.match(r'^[-*·,\s()·]*$', t):
            return False
        t_norm = re.sub(r'\s+', '', t)
        is_prefix_dup = any(
            re.sub(r'\s+', '', ex).startswith(t_norm) or t_norm.startswith(re.sub(r'\s+', '', ex))
            for ex in seen_texts
        )
        if is_prefix_dup and len(t_norm) < 15:
            return False
        t_key = t_norm[:50]
        if t_key in seen_texts:
            return False
        if any(pat.search(t) for pat in CONTENT_SKIP_PATTERNS):
            return False
        seen_texts.add(t_key)
        if t.startswith(("※", "*", "＊")):
            lines.append(t)
        else:
            lines.append(f"- {t}")
        return True

    def _traverse(elem):
        from bs4 import Tag
        for child in elem.children:
            if not isinstance(child, Tag):
                continue
            if _try_subtitle(child):
                continue
            if child.name == "ul" and "listType1" in (child.get("class") or []):
                for li in child.find_all("li", recursive=False):
                    lines.extend(_li_to_lines(li))
                continue
            if _try_table(child):
                continue
            if _try_text(child):
                continue
            _traverse(child)

    _traverse(soup)
    lines = [l for l in lines if not any(pat.search(l) for pat in CONTENT_SKIP_PATTERNS)]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# benefitBox1 → section dict
# ─────────────────────────────────────────────
def _box_to_section(box, filter_limit_tables: bool = True) -> dict | None:
    text = box.get_text("\n", strip=True)
    if len(text.strip()) < 8 or box_is_skip(text):
        return None
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    first = lines[0] if lines else ""
    raw_html = str(box)
    has_sibling_table = False

    if not box.find(class_="listType1") and not box.find("table"):
        pre_table_html = ""
        for pre_sib in list(box.find_previous_siblings()):
            if pre_sib.name == "div" and "benefitBox1" in (pre_sib.get("class") or []):
                prev_box_text = pre_sib.get_text(" ", strip=True)
                if len(prev_box_text) < 8:
                    for pp in list(pre_sib.find_previous_siblings()):
                        if pp.name == "div" and "benefitBox1" in (pp.get("class") or []):
                            break
                        if pp.name in ("h2", "h3", "h4", "h5"):
                            break
                        if pp.name == "table":
                            pre_table_html = str(pp) + pre_table_html
                            has_sibling_table = True
                            break
                break
            if pre_sib.name in ("h2", "h3", "h4", "h5"):
                break
            if pre_sib.name == "table":
                pre_table_html = str(pre_sib) + pre_table_html
                has_sibling_table = True
                break
        if pre_table_html:
            raw_html = pre_table_html + raw_html

        for sib in box.find_next_siblings():
            if sib.name == "div" and "benefitBox1" in (sib.get("class") or []):
                break
            if sib.name in ("h3", "h4", "h5"):
                break
            if sib.name == "ul" and "listType1" in (sib.get("class") or []):
                raw_html += str(sib)
            if sib.name == "table":
                raw_html += str(sib)
                has_sibling_table = True
                for p_sib in sib.find_next_siblings():
                    if p_sib.name in ("p", "strong"):
                        raw_html += str(p_sib)
                    elif p_sib.name in ("br",):
                        continue
                    else:
                        break
            elif sib.name in ("p", "strong") and not has_sibling_table:
                raw_html += str(sib)

    has_any_table = has_sibling_table or bool(box.find("table"))
    effective_filter = filter_limit_tables and not has_any_table

    ui_content = build_ui_content(raw_html, first, filter_limit_tables=effective_filter)

    return {
        "group":               _extract_group_label(first, text),
        "title":               first[:60],
        "content":             ui_content,
        "raw_html":            raw_html,
        "filter_limit_tables": effective_filter,
        "is_notice":           box_is_notice(text),
    }


def _box_has_multiple_categories(box) -> bool:
    for table in box.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            first = cells[0].get_text(" ", strip=True)
            if any(k in first for k in ["구분", "할인율", "전월"]):
                continue
            sub_text = " ".join(c.get_text(" ", strip=True) for c in cells[1:])
            if "," in sub_text:
                return True
            if "," in first:
                parts = [p.strip() for p in first.split(",")]
                cat_ids = set()
                for part in parts:
                    for cat_name, keywords in CATEGORY_KEYWORD_MAP:
                        if any(kw in part for kw in keywords):
                            cat_ids.add(CATEGORY_ID_MAP.get(cat_name, 22))
                            break
                if len(cat_ids) > 1:
                    return True
    return False


# ─────────────────────────────────────────────
# HTML → 섹션 목록
# ─────────────────────────────────────────────
def extract_sections_from_kb_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    if soup.find(id="tabCon011"):
        return _extract_pattern_a(soup)
    else:
        return _extract_pattern_b(soup)


def _extract_pattern_a(soup) -> list[dict]:
    sections = []
    fallback_perf_condition = ""
    fallback_limit_map: dict = {}
    fallback_full_table: str = ""

    all_tab_ids = sorted(
        {t.get("id") for t in soup.find_all(id=re.compile(r"^tabCon0\d{2}$"))},
        key=lambda x: int(x.replace("tabCon0", ""))
    )
    all_tab_ids = [tid for tid in all_tab_ids if int(tid.replace("tabCon0", "")) >= 10]

    for tab_id in all_tab_ids:
        tab = soup.find(id=tab_id)
        if not tab:
            continue

        full_text = tab.get_text("\n", strip=True)

        if len(full_text.strip()) < 10:
            continue
        if re.search(r"통합할인한도", full_text.strip()[:50]):
            continue

        _pre_perf, _pre_lm, _pre_ftbl = _extract_tab_limit_info(tab)
        if _pre_lm:
            fallback_limit_map = _pre_lm
            fallback_perf_condition = _pre_perf
            fallback_full_table = _pre_ftbl
        else:
            fallback_full_table = ""

        boxes = [b for b in tab.find_all(class_="benefitBox1") if not _is_popup_box(b)]
        meaningful_boxes = [b for b in boxes if len(b.get_text(" ", strip=True)) > 5]

        def box_has_content(box) -> bool:
            return bool(box.find(class_="listType1") or box.find("table"))

        rich_boxes = [b for b in meaningful_boxes if box_has_content(b)]

        if rich_boxes:
            perf_condition, limit_map, full_table_html = _extract_tab_limit_info(tab)
            if not limit_map and fallback_limit_map:
                limit_map = fallback_limit_map
                perf_condition = perf_condition or fallback_perf_condition
                full_table_html = full_table_html or fallback_full_table
            elif limit_map:
                fallback_limit_map = limit_map
                fallback_perf_condition = perf_condition
                fallback_full_table = full_table_html

            prev_title = ""
            for box in rich_boxes:
                sec = _box_to_section(box)
                if not sec:
                    continue

                cur_title = sec["title"]
                if prev_title and (
                    cur_title == prev_title or
                    (prev_title in cur_title and "업종" in cur_title)
                ):
                    if sections:
                        prev_content = sections[-1]["content"]
                        new_content = sec["content"]
                        new_body = re.sub(r'^\[.*?\]\n?', '', new_content, count=1).strip()
                        new_key = re.sub(r'\s+', '', new_body)[:80]
                        prev_key = re.sub(r'\s+', '', prev_content)
                        if new_key and new_key not in prev_key:
                            sections[-1]["content"] += "\n" + new_content
                            sections[-1]["raw_html"] += sec["raw_html"]
                    continue

                content_has_limit_table = "<table" in sec["content"]
                condition_parts = []
                content_has_perf = bool(re.search(r'\d+만원\s*이상', sec["content"]))
                if perf_condition and not content_has_perf:
                    condition_parts.append(perf_condition)

                matched_info = None
                matched_keys = []
                if limit_map:
                    search_text = cur_title + " " + sec.get("group", "") + " " + sec["content"][:200]
                    for key, info in limit_map.items():
                        key_norm = re.sub(r'\s', '', key)
                        key_words = [w.strip() for w in re.split(r'[,、·]', key) if w.strip()]
                        match = (
                            any(w in search_text for w in key_words) or
                            re.sub(r'\s', '', search_text).find(key_norm) >= 0
                        )
                        if match:
                            matched_keys.append((key, info))

                    if full_table_html and (len(limit_map) >= 2 or (matched_keys and _key_has_subrows(matched_keys[0][0], full_table_html))):
                        condition_parts.append(full_table_html)
                        sec["_ui_condition"] = full_table_html
                    elif matched_keys:
                        matched_info = matched_keys[0][1]

                if matched_info:
                    if matched_info.get("summary_ai"):
                        condition_parts.append(matched_info["summary_ai"])
                        sec["_ui_condition"] = matched_info.get("summary_ui", "")
                    else:
                        condition_parts.append(matched_info["table_html"])
                        if matched_info["is_group"]:
                            condition_parts.append("※ 위 표의 한도는 여러 카테고리 합산 그룹 한도입니다 (group_max_limit)")
                        else:
                            condition_parts.append("※ 위 표의 한도는 이 카테고리 단독 한도입니다 (max_limit)")

                if condition_parts and not content_has_limit_table:
                    sec["content"] += "\n[이용 조건]\n" + "\n".join(condition_parts)

                    ui_parts = []
                    if perf_condition and not content_has_perf:
                        ui_parts.append(perf_condition)
                    if matched_info:
                        ui_cond = sec.pop("_ui_condition", "")
                        if ui_cond:
                            ui_parts.append(ui_cond)
                        elif matched_info.get("table_html"):
                            ui_parts.append(matched_info["table_html"])
                    sec["ui_condition_text"] = "\n".join(ui_parts) if ui_parts else ""

                prev_title = cur_title
                sections.append(sec)
        else:
            # [패턴 C] title-only benefitBox1 + sibling ul.listType1
            paired_boxes = []
            for box in meaningful_boxes:
                btitle = box.get_text(" ", strip=True).strip()
                if not btitle or len(btitle) < 3:
                    continue
                for sib in box.find_next_siblings():
                    if sib.name == "div" and "benefitBox1" in (sib.get("class") or []):
                        break
                    if sib.name in ("h3", "h4", "h5"):
                        break
                    if sib.name == "ul" and "listType1" in (sib.get("class") or []):
                        paired_boxes.append(box)
                        break

            if paired_boxes:
                perf_condition_p, limit_map_p, full_table_html_p = _extract_tab_limit_info(tab)
                if not limit_map_p and fallback_limit_map:
                    limit_map_p = fallback_limit_map
                    perf_condition_p = perf_condition_p or fallback_perf_condition
                    full_table_html_p = full_table_html_p or fallback_full_table
                elif limit_map_p:
                    fallback_limit_map = limit_map_p
                    fallback_perf_condition = perf_condition_p
                    fallback_full_table = full_table_html_p

                prev_title_p = ""
                for box in paired_boxes:
                    sec = _box_to_section(box)
                    if not sec:
                        continue
                    cur_title_p = sec["title"]
                    if prev_title_p and cur_title_p == prev_title_p:
                        continue

                    if "<table" in sec["content"]:
                        prev_title_p = cur_title_p
                        sections.append(sec)
                        continue
                    cond_parts_p = []
                    content_has_perf_p = bool(re.search(r'\d+만원\s*이상', sec["content"]))
                    if perf_condition_p and not content_has_perf_p:
                        cond_parts_p.append(perf_condition_p)
                    matched_p = None
                    matched_keys_p = []
                    if limit_map_p:
                        search_p = cur_title_p + " " + sec.get("group","") + " " + sec["content"][:200]
                        for key, info in limit_map_p.items():
                            key_norm = re.sub(r'\s', '', key)
                            key_words = [w.strip() for w in re.split(r'[,、·]', key) if w.strip()]
                            key_clean = re.sub(r'[#()\s]', '', key)
                            search_clean = re.sub(r'[#()\s]', '', search_p)
                            if (any(w in search_p for w in key_words)
                                    or re.sub(r'\s','',search_p).find(key_norm) >= 0
                                    or (key_clean and key_clean in search_clean)):
                                matched_keys_p.append((key, info))

                        if full_table_html_p and (len(limit_map_p) >= 2 or (matched_keys_p and _key_has_subrows(matched_keys_p[0][0], full_table_html_p))):
                            cond_parts_p.append(full_table_html_p)
                            sec["_ui_condition"] = full_table_html_p
                        elif matched_keys_p:
                            matched_p = matched_keys_p[0][1]

                    if matched_p:
                        if matched_p.get("summary_ai"):
                            cond_parts_p.append(matched_p["summary_ai"])
                            sec["_ui_condition"] = matched_p.get("summary_ui", "")
                        else:
                            cond_parts_p.append(matched_p["table_html"])
                            hint = "그룹 한도입니다 (group_max_limit)" if matched_p["is_group"] else "단독 한도입니다 (max_limit)"
                            cond_parts_p.append(f"※ 위 표의 한도는 이 카테고리 {hint}")
                    if cond_parts_p:
                        sec["content"] += "\n[이용 조건]\n" + "\n".join(cond_parts_p)
                        ui_p = []
                        if perf_condition_p and not content_has_perf_p:
                            ui_p.append(perf_condition_p)
                        if matched_p:
                            ui_cond_p = sec.pop("_ui_condition", "")
                            if ui_cond_p:
                                ui_p.append(ui_cond_p)
                            elif matched_p.get("table_html"):
                                ui_p.append(matched_p["table_html"])
                        sec["ui_condition_text"] = "\n".join(ui_p) if ui_p else ""

                    prev_title_p = cur_title_p
                    sections.append(sec)

            else:
                # [09298 방식] 탭 전체가 하나의 섹션
                title = ""
                h2_blind = tab.find("h2", class_="blind")
                if h2_blind:
                    title = h2_blind.get_text(" ", strip=True)
                if not title and meaningful_boxes:
                    txt_tag = meaningful_boxes[0].find(class_="txt") or meaningful_boxes[0].find(class_="sTit")
                    if txt_tag:
                        title = txt_tag.get_text(" ", strip=True)
                if not title:
                    title_tag = tab.find(class_="txt") or tab.find(class_="sTit") or tab.find("h3") or tab.find("h4")
                    title = title_tag.get_text(" ", strip=True) if title_tag else ""
                if not title:
                    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
                    title = lines[1] if len(lines) > 1 else lines[0] if lines else ""

                title = re.sub(r"^상세혜택\s*[>＞]\s*", "", title).strip()

                if title and not box_is_skip(title):
                    raw_html = str(tab)
                    ui_content = build_ui_content(raw_html, title, filter_limit_tables=False)

                    sec = {
                        "group":    _extract_group_label(title, full_text),
                        "title":    title[:60],
                        "filter_limit_tables": False,
                        "content":  ui_content,
                        "raw_html": raw_html,
                        "is_notice": box_is_notice(full_text),
                    }

                    perf_condition, limit_map, full_table_html = _extract_tab_limit_info(tab)
                    if not limit_map and fallback_limit_map:
                        limit_map = fallback_limit_map
                        perf_condition = perf_condition or fallback_perf_condition
                        full_table_html = full_table_html or fallback_full_table
                    elif limit_map:
                        fallback_limit_map = limit_map
                        fallback_perf_condition = perf_condition
                        fallback_full_table = full_table_html

                    matched_info = None
                    matched_keys = []
                    if limit_map:
                        for key, info in limit_map.items():
                            key_words = [w.strip() for w in re.split(r'[,、·]', key) if w.strip()]
                            if any(w in title or w in ui_content[:200] for w in key_words):
                                matched_keys.append((key, info))

                    condition_parts = []
                    content_has_perf = bool(re.search(r'\d+만원\s*이상', ui_content))
                    content_has_limit_table_09298 = "<table" in ui_content
                    if perf_condition and not content_has_perf:
                        condition_parts.append(perf_condition)
                    if full_table_html and (len(limit_map) >= 2 or (matched_keys and _key_has_subrows(matched_keys[0][0], full_table_html))):
                        condition_parts.append(full_table_html)
                        sec["_ui_condition"] = full_table_html
                    elif matched_keys:
                        matched_info = matched_keys[0][1]
                    if matched_info:
                        if matched_info.get("summary_ai"):
                            condition_parts.append(matched_info["summary_ai"])
                            sec["_ui_condition"] = matched_info.get("summary_ui", "")
                        else:
                            condition_parts.append(matched_info["table_html"])
                            hint = "그룹 한도입니다 (group_max_limit)" if matched_info["is_group"] else "단독 한도입니다 (max_limit)"
                            condition_parts.append(f"※ 위 표의 한도는 이 카테고리 {hint}")

                    if condition_parts and not content_has_limit_table_09298:
                        sec["content"] += "\n[이용 조건]\n" + "\n".join(condition_parts)

                        ui_parts = []
                        if perf_condition and not content_has_perf:
                            ui_parts.append(perf_condition)
                        if matched_info:
                            ui_cond = sec.pop("_ui_condition", "")
                            if ui_cond:
                                ui_parts.append(ui_cond)
                            elif matched_info.get("table_html"):
                                ui_parts.append(matched_info["table_html"])
                        sec["ui_condition_text"] = "\n".join(ui_parts) if ui_parts else ""

                    sections.append(sec)

    return sections


def _extract_pattern_b(soup) -> list[dict]:
    tab = soup.find(id="tabCon010")
    if not tab:
        card_view = soup.find(class_="cardView") or soup
        tab = card_view

    sections = []

    headings = tab.find_all(["h3", "h4"])

    ATTACH_TO_PREV_PATTERNS = [
        r"할인\s*서비스\s*대상\s*가맹점",
        r"서비스\s*대상\s*가맹점",
        r"이용\s*가맹점",
    ]

    if len(headings) >= 2:
        raw_sections = []
        for idx, heading in enumerate(headings):
            title = heading.get_text(" ", strip=True).lstrip("■▶●·- ").strip()
            if not title or len(title) < 2:
                continue

            content_tags = []
            for sib in heading.find_next_siblings():
                if sib.name in ["h3", "h4"]:
                    break
                content_tags.append(sib)

            content_html = heading.prettify() + "".join(str(t) for t in content_tags)
            content_text = BeautifulSoup(content_html, "html.parser").get_text("\n", strip=True)

            if len(content_text) < 10 or box_is_skip(content_text):
                continue

            ui_content = build_ui_content(content_html, title, filter_limit_tables=False)
            raw_sections.append({
                "group":    "기본 혜택",
                "title":    title[:60],
                "filter_limit_tables": False,
                "content":  ui_content if ui_content.strip() else content_text,
                "raw_html": content_html,
                "is_notice": box_is_notice(content_text),
            })

        for sec in raw_sections:
            if any(re.search(p, sec["title"]) for p in ATTACH_TO_PREV_PATTERNS):
                if sections:
                    sections[-1]["content"] += "\n" + sec["content"]
                    sections[-1]["raw_html"] += sec["raw_html"]
            else:
                sections.append(sec)

        if not sections:
            for box in tab.find_all(class_="benefitBox1"):
                btitle = box.get_text(" ", strip=True).strip()
                if not btitle or len(btitle) < 3:
                    continue
                raw_html = str(box)
                for sib in box.find_next_siblings():
                    if sib.name == "div" and "benefitBox1" in (sib.get("class") or []):
                        break
                    if sib.name == "table":
                        raw_html += str(sib)
                        for p_sib in sib.find_next_siblings():
                            if p_sib.name == "p":
                                raw_html += str(p_sib)
                            else:
                                break
                        break
                    if sib.name == "ul" and "listType1" in (sib.get("class") or []):
                        raw_html += str(sib)
                        break
                full_t = BeautifulSoup(raw_html, "html.parser").get_text("\n", strip=True)
                if len(full_t) < 10 or box_is_skip(full_t):
                    continue
                ui_content = build_ui_content(raw_html, btitle, filter_limit_tables=False)
                sections.append({
                    "group":    "기본 혜택",
                    "title":    btitle[:60],
                    "filter_limit_tables": False,
                    "content":  ui_content if ui_content.strip() else full_t,
                    "raw_html": raw_html,
                    "is_notice": box_is_notice(full_t),
                })
    else:
        text = tab.get_text("\n", strip=True)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        first = lines[0] if lines else "기본 혜택"
        if len(text) > 20:
            raw_html = str(tab)
            ui_content = build_ui_content(raw_html, first, filter_limit_tables=False)
            sections.append({
                "group":    "기본 혜택",
                "title":    first[:60],
                "filter_limit_tables": False,
                "content":  ui_content if ui_content.strip() else text,
                "raw_html": raw_html,
                "is_notice": False,
            })

    return sections


# ─────────────────────────────────────────────
# 유의사항 추출
# ─────────────────────────────────────────────
def extract_notice_from_kb_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    NOTICE_TAB_KEYWORDS = ["카드이용", "해외이용", "확인사항", "이용안내", "이용 전 확인사항"]

    target_tabs = []
    tab_menu = soup.find(class_="tabType1")
    if tab_menu:
        for idx, li in enumerate(tab_menu.find_all("li")):
            tab_name = li.get_text(strip=True)
            if any(kw in tab_name for kw in NOTICE_TAB_KEYWORDS):
                tab_con = soup.find(id=f"tabCon0{idx}")
                if tab_con:
                    target_tabs.append((tab_name, tab_con))

    if not target_tabs:
        return []

    def _tab_to_text(tab_name: str, tab) -> str:
        lines = [f"[{tab_name}]"]
        seen = set()

        for elem in tab.find_all(["h2", "h3", "h4", "ul", "p"]):
            if elem.find_parent("table"):
                continue

            if elem.name in ["h2", "h3", "h4"]:
                txt = elem.get_text(" ", strip=True).strip()
                if not txt or txt == tab_name or "blind" in (elem.get("class") or []):
                    continue
                if txt in seen:
                    continue
                seen.add(txt)
                lines.append(f"[{txt}]")

            elif elem.name == "ul":
                for li in elem.find_all("li", recursive=False):
                    txt = li.get_text(" ", strip=True)
                    if txt and len(txt) > 3:
                        lines.append(f"- {txt}")

            elif elem.name == "p":
                txt = elem.get_text(" ", strip=True)
                if txt and len(txt) > 5:
                    lines.append(txt)

        return "\n".join(lines)

    all_sections = []
    for tab_name, tab_con in target_tabs:
        section_text = _tab_to_text(tab_name, tab_con)
        if section_text:
            all_sections.append(section_text)

    if not all_sections:
        return []

    combined = "\n\n".join(all_sections)
    return [{"label": "확인사항", "content": combined}]


# ─────────────────────────────────────────────
# 카드 기본정보 규칙 기반 추출
# ─────────────────────────────────────────────
NETWORK_ALT_MAP = {
    "visa": "VISA", "비자": "VISA",
    "master": "Mastercard", "마스터": "Mastercard",
    "amex": "AMEX", "아멕스": "AMEX",
    "jcb": "JCB", "k-world": "Local",
    "unionpay": "UnionPay", "upi": "UnionPay", "은련": "UnionPay",
    "local": "Local", "국내전용": "Local",
}

def extract_card_image(soup, card_id: str) -> str:
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if f"/{card_id}_img" in src:
            return src
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "upload/img/product/" in src and "_img.png" in src:
            return src
    return ""

def extract_network(soup) -> tuple[str, bool]:
    networks = []
    seen = set()

    def _scan_imgs(imgs):
        for img in imgs:
            alt = img.get("alt", "").lower()
            src = img.get("src", "").lower()
            combined = alt + " " + src
            for key, name in NETWORK_ALT_MAP.items():
                if key == "jcb" and "kworld" in combined:
                    continue
                if key in combined and name not in seen:
                    seen.add(name)
                    networks.append(name)

    fee_div = soup.find(class_="cardAnnualFee")
    if fee_div:
        _scan_imgs(fee_div.find_all("img"))

    if not networks:
        for cls in ["cardBox", "cardCont", "cardInfo", "cardView"]:
            area = soup.find(class_=cls)
            if area:
                targets = [img for img in area.find_all("img")
                           if any(x in img.get("src","").lower()
                                  for x in ["brand_","img_only","img_master","img_visa","img_local"])]
                _scan_imgs(targets)
                if networks:
                    break

    if not networks:
        targets = [img for img in soup.find_all("img")
                   if any(x in img.get("src","").lower()
                          for x in ["brand_","img_only","img_master","img_visa","img_local","brand_upi"])]
        _scan_imgs(targets)

    network_str = ",".join(networks) if networks else "Local"
    is_foreign = any(n in networks for n in ["VISA", "Mastercard", "AMEX", "JCB", "UnionPay"])
    return network_str, is_foreign

def extract_annual_fee_notes(soup) -> str:
    fee_div = soup.find(class_="cardAnnualFee")
    if not fee_div:
        return ""
    parts = []
    for li in fee_div.find_all("li"):
        img = li.find("img")
        brand = img.get("alt", "").strip() if img else ""
        span = li.find(class_="card-fee")
        amount = span.get_text(" ", strip=True) if span else li.get_text(" ", strip=True)
        if amount:
            parts.append(f"{brand}: {amount}" if brand else amount)

    mobile_prices = []
    for p in parts:
        m = re.search(r'\(모바일\s*단독\s*:\s*([^)]+)\)', p)
        mobile_prices.append(m.group(1).strip() if m else None)

    if parts and all(mp is not None for mp in mobile_prices):
        unique = set(mobile_prices)
        if len(unique) == 1:
            return f"(모바일단독: {unique.pop()})"

    return " / ".join(parts)


def _parse_korean_amount(text: str) -> int:
    text = text.replace(",", "").replace(" ", "")
    m = re.search(r'(\d+)만(\d+)천원?', text)
    if m:
        return int(m.group(1)) * 10000 + int(m.group(2)) * 1000
    m = re.search(r'(\d+)만원?', text)
    if m:
        return int(m.group(1)) * 10000
    m = re.search(r'(\d+)천원?', text)
    if m:
        return int(m.group(1)) * 1000
    m = re.search(r'(\d+)', text)
    if m:
        return int(m.group(1))
    return 0


def extract_annual_fees_rule(soup) -> tuple[int, int]:
    fee_div = soup.find(class_="cardAnnualFee")
    if not fee_div:
        return 0, 0

    dom_fee, for_fee = 0, 0
    LOCAL_KEYWORDS = {"국내전용", "local", "로컬", "kworld", "k_world"}

    for li in fee_div.find_all("li"):
        img = li.find("img")
        alt = (img.get("alt", "") if img else "").lower()
        src = (img.get("src", "") if img else "").lower()
        span = li.find(class_="card-fee")
        amount_text = span.get_text(" ", strip=True) if span else ""
        if not amount_text:
            continue

        base_text = re.sub(r'\(.*?\)', '', amount_text).strip()
        amount = _parse_korean_amount(base_text)

        is_local = any(k in alt or k in src for k in LOCAL_KEYWORDS) or "onlylocal" in src
        if is_local:
            dom_fee = amount
        else:
            if for_fee == 0:
                for_fee = amount

    return dom_fee, for_fee


def extract_fee_content(soup) -> str:
    tab = None
    tab_menu = soup.find(class_="tabType1")
    if tab_menu:
        for idx, li in enumerate(tab_menu.find_all("li")):
            if "연회비" in li.get_text():
                fee_tab = soup.find(id=f"tabCon0{idx}")
                if fee_tab:
                    sub = soup.find(id=f"tabCon0{idx}0")
                    tab = sub if sub else fee_tab
                break

    if not tab:
        tab = soup.find(class_=re.compile(r"cardFee|annualFee", re.I))

    if not tab:
        return ""

    lines = []
    seen_tables = set()

    for elem in tab.find_all(["h2", "h3", "ul", "table", "p"]):
        if elem.find_parent("table"):
            continue

        if elem.name in ["h2", "h3"]:
            pass  # 헤딩 제목 제외

        elif elem.name == "ul":
            for li in elem.find_all("li", recursive=False):
                txt = li.get_text(" ", strip=True)
                if txt:
                    lines.append(f"- {txt}")

        elif elem.name == "table":
            key = elem.get_text(" ", strip=True)[:50]
            if key in seen_tables:
                continue
            seen_tables.add(key)
            rows_html = []
            for tr in elem.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if not cells:
                    continue
                cells_html = []
                for cell in cells:
                    colspan = f' colspan="{cell.get("colspan")}"' if cell.get("colspan") else ""
                    rowspan = f' rowspan="{cell.get("rowspan")}"' if cell.get("rowspan") else ""
                    tag = cell.name
                    text = cell.get_text(" ", strip=True)
                    cells_html.append(f"<{tag}{colspan}{rowspan}>{text}</{tag}>")
                rows_html.append(f'<tr>{"".join(cells_html)}</tr>')
            if rows_html:
                lines.append(f'<table class="benefit-table">{"".join(rows_html)}</table>')

        elif elem.name == "p":
            txt = elem.get_text(" ", strip=True)
            if txt:
                lines.append(txt)

    return "\n".join(lines)


def _extract_card_summary(soup) -> str:
    ul = soup.find("ul", class_="cardList1")
    if not ul:
        return ""
    items = []
    for li in ul.find_all("li", recursive=False):
        txt = re.sub(r'\s+', ' ', li.get_text(" ", strip=True)).strip()
        txt = re.sub(r'(\d)\s*%', r'\1%', txt)
        if txt:
            items.append(txt)
    return " / ".join(items[:4]) if items else ""
