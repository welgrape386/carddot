import re
import copy

from bs4 import BeautifulSoup

from hd_parser_base import (
    SKIP_MODAL_PATTERNS, NOTICE_ROW_MODAL_PATTERNS,
    MERGE_AS_ONE_PATTERNS, NOTICE_MODAL_GROUPS,
    GROUP_BENEFIT_TYPE_MAP,
)


# ─────────────────────────────────────────────
# HTML 표 → 텍스트
# ─────────────────────────────────────────────
def build_table_text(table_elem) -> str:
    rows_txt = []
    for tr in table_elem.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        row_txt = " | ".join(c.get_text(" ", strip=True) for c in cells)
        rows_txt.append(row_txt)
    return "\n".join(rows_txt)


# ─────────────────────────────────────────────
# HTML → 텍스트 변환
# ─────────────────────────────────────────────
def elem_to_text(elem) -> str:
    parts = []
    for child in elem.descendants:
        if not hasattr(child, "name"):
            continue
        if child.name == "table":
            tbl_txt = build_table_text(child)
            if tbl_txt:
                parts.append(f"[표]\n{tbl_txt}")
            child.decompose()
    remaining = elem.get_text("\n", strip=True)
    if remaining:
        parts.insert(0, remaining)
    return "\n".join(parts)


def html_to_text(elem) -> str:
    elem = copy.copy(elem)

    for gray in elem.find_all("div", class_="box_bg_gray"):
        for bt in gray.find_all("div", class_="box_title"):
            bt["data-notice"] = "1"

    bundles = elem.find_all("div", class_="card_bundle")
    if bundles:
        block_texts = []
        for bundle in bundles:
            block_texts.append(_bundle_to_text(copy.copy(bundle)))
        return "\n\n".join(t for t in block_texts if t.strip())

    return _bundle_to_text(elem)


def _bundle_to_text(elem) -> str:
    for svg in elem.find_all("svg"):
        svg.decompose()

    for ul in elem.find_all("ul", class_="list_line"):
        lines = []
        for li in ul.find_all("li", class_="img_item01"):
            box_tit = li.find("div", class_="box_tit")
            box_txt = li.find("div", class_="box_txt")
            if box_tit:
                lines.append(box_tit.get_text(" ", strip=True))
            if box_txt:
                for p in box_txt.find_all("p", recursive=False):
                    pt = p.get_text(" ", strip=True)
                    if pt:
                        lines.append(f"-{pt}")
                for sub_li in box_txt.find_all("li"):
                    st = sub_li.get_text(" ", strip=True)
                    if st:
                        lines.append(f"  ({st})")
        if lines:
            ul.replace_with("\n".join(lines) + "\n")

    for bul in elem.find_all("ul", class_="bul_list"):
        lines = []
        for li in bul.find_all("li", recursive=False):
            fw = li.find("span", class_="fw_bold")
            if fw:
                header = fw.get_text(strip=True)
                if header:
                    lines.append(f"[{header}]")
                fw.decompose()
            else:
                direct = li.find_all(string=True, recursive=False)
                header = " ".join(t.strip() for t in direct if t.strip())
                if header:
                    lines.append(header)
            box_tit = li.find("div", class_="box_tit")
            if box_tit:
                tit_txt = box_tit.get_text(" ", strip=True)
                if tit_txt:
                    lines.append(tit_txt)
                box_tit.decompose()
            box_txt = li.find("div", class_="box_txt")
            if box_txt:
                for p in box_txt.find_all("p"):
                    pt = p.get_text(" ", strip=True)
                    if pt:
                        lines.append(f"-{pt}")
                for sub_li in box_txt.find_all("li"):
                    st = sub_li.get_text(" ", strip=True)
                    if st:
                        lines.append(f"  ({st})")
                box_txt.decompose()
            for dash in li.find_all("ul", class_="dash_list"):
                for dli in dash.find_all("li"):
                    dt = dli.get_text(" ", strip=True)
                    if dt:
                        lines.append(f"-{dt}")
                dash.decompose()
        if lines:
            bul.replace_with("\n".join(lines) + "\n")

    for box_title in elem.find_all("div", class_="box_title"):
        p = box_title.find("p", class_="p1_b_lt_1ln")
        if p:
            txt = p.get_text(" ", strip=True)
            if txt:
                is_notice = box_title.get("data-notice") == "1"
                prefix = f"[{txt}]" if is_notice else txt
                box_title.replace_with(prefix + "\n")
        else:
            box_title.replace_with(box_title.get_text(" ", strip=True) + "\n")

    for span in elem.find_all("span", class_="fw_bold"):
        parent = span.parent
        if parent and parent.name == "li":
            txt = span.get_text(strip=True)
            if txt:
                span.replace_with(f"[{txt}]\n")

    for table in elem.find_all("table"):
        if table.find_parent("table"):
            continue
        for caption in table.find_all("caption"):
            caption.decompose()
        rows_html = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            cells_html = []
            for cell in cells:
                colspan = f' colspan="{cell.get("colspan")}"' if cell.get("colspan") else ""
                rowspan = f' rowspan="{cell.get("rowspan")}"' if cell.get("rowspan") else ""
                tag  = cell.name
                text = cell.get_text(" ", strip=True)
                cells_html.append(f"<{tag}{colspan}{rowspan}>{text}</{tag}>")
            rows_html.append(f'<tr>{"".join(cells_html)}</tr>')
        table_html = f'<table class="benefit-table">{"".join(rows_html)}</table>'
        table.replace_with(f"\n{table_html}\n")

    for br in elem.find_all("br"):
        br.replace_with("\n")

    for tag in elem.find_all(["li", "p", "div", "h3", "h4", "h5", "dt", "dd"]):
        if tag.get_text(strip=True):
            tag.append("\n")

    text = elem.get_text("")
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines).strip()


def build_ui_from_html(section_title: str, raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    lines, seen = [], set()

    for elem in soup.find_all(["div", "table", "p", "li"]):
        if elem.name == "div" and "box_title" in (elem.get("class") or []):
            p = elem.find("p", class_="p1_b_lt_1ln")
            if p:
                text = p.get_text(" ", strip=True)
                if text and text not in seen:
                    seen.add(text)
                    if lines and lines[-1] != "":
                        lines.append("")
                    lines.append(f"[{text}]")
            continue

        if elem.name == "table":
            if elem.find_parent("table"):
                continue
            for caption in elem.find_all("caption"):
                caption.decompose()
            rows_html = []
            for tr in elem.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if not cells:
                    continue
                cells_html = []
                for cell in cells:
                    colspan = f' colspan="{cell.get("colspan")}"' if cell.get("colspan") else ""
                    rowspan = f' rowspan="{cell.get("rowspan")}"' if cell.get("rowspan") else ""
                    tag  = cell.name
                    text = cell.get_text(" ", strip=True)
                    cells_html.append(f"<{tag}{colspan}{rowspan}>{text}</{tag}>")
                rows_html.append(f'<tr>{"".join(cells_html)}</tr>')
            table_html = f'<table class="benefit-table">{"".join(rows_html)}</table>'
            if table_html not in seen:
                seen.add(table_html)
                lines.append(table_html)
            continue

        if elem.name in ["p", "li"]:
            if elem.find_parent("table"):
                continue
            if elem.find_parent("div", class_="box_title"):
                continue
            text = elem.get_text(" ", strip=True)
            if text and len(text) > 2 and text not in seen:
                seen.add(text)
                lines.append(text)

    return "\n".join(lines)


def section_to_text(bc_elem) -> str:
    lines = []

    for aw in bc_elem.find_all(class_="accodWrap"):
        if "infocontWrap" in aw.get("class", []):
            continue

        title_a = aw.find("a", class_="accodBtn")
        title   = title_a.get_text(strip=True) if title_a else ""
        slide   = aw.find(class_="accodSlide")
        content = html_to_text(slide) if slide else ""

        if title:
            lines.append(f"[{title}]")
        if content:
            lines.append(content)
        lines.append("")

    for aw in bc_elem.find_all(class_="accodWrap"):
        aw.decompose()
    for tit in bc_elem.find_all(class_="box_top_tit"):
        tit.decompose()

    remaining = html_to_text(bc_elem)
    if remaining.strip():
        lines.append(remaining)

    return "\n".join(lines).strip()


def extract_accod_sections(bc_elem) -> list[dict]:
    sections = []

    accods = [aw for aw in bc_elem.find_all(class_="accodWrap")
              if "infocontWrap" not in aw.get("class", [])]

    if accods:
        for aw in accods:
            title_a  = aw.find("a", class_="accodBtn")
            title    = title_a.get_text(strip=True) if title_a else ""
            slide    = aw.find(class_="accodSlide")
            slide_html = str(slide) if slide else ""
            text     = html_to_text(copy.copy(slide)) if slide else ""
            if title or text.strip():
                sections.append({
                    "title":      title,
                    "text":       text,
                    "slide_html": slide_html,
                })
    else:
        bc_copy = copy.copy(bc_elem)
        for tit in bc_copy.find_all(class_="box_top_tit"):
            tit.decompose()
        for aw in bc_copy.find_all(class_="accodWrap"):
            aw.decompose()
        text = html_to_text(bc_copy)
        if text.strip():
            sections.append({
                "title":      "",
                "text":       text,
                "slide_html": str(bc_elem),
            })

    return sections


# ─────────────────────────────────────────────
# 섹션 추출 (modal_pop 기반)
# ─────────────────────────────────────────────
def extract_sections_from_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    sections = []

    for mp in soup.find_all(class_="modal_pop"):
        h = mp.find(["h1", "h2", "h3"])
        group_name = h.get_text(strip=True) if h else ""
        if not group_name:
            continue

        if any(re.search(p, group_name) for p in SKIP_MODAL_PATTERNS):
            continue

        is_notice_row_group = any(re.search(p, group_name) for p in NOTICE_ROW_MODAL_PATTERNS)
        is_merge_as_one     = any(re.search(p, group_name) for p in MERGE_AS_ONE_PATTERNS)
        is_안내_group       = is_notice_row_group or any(re.search(p, group_name) for p in NOTICE_MODAL_GROUPS)

        forced_benefit_type = ""
        for pattern, btype in GROUP_BENEFIT_TYPE_MAP.items():
            if re.search(pattern, group_name):
                forced_benefit_type = btype
                break

        info_text = ""
        info_wrap = mp.find(class_="infocontWrap")
        if info_wrap:
            info_btn   = info_wrap.find("a", class_="accodBtn")
            info_title = info_btn.get_text(strip=True) if info_btn else "유의사항"
            info_slide = info_wrap.find(class_="accodSlide")
            info_root  = info_slide if info_slide else info_wrap
            list_items = info_root.find_all(class_="list_item")
            if list_items:
                info_lines = [f"[{info_title}]"]
                for item in list_items:
                    box_title = item.find(class_="box_title")
                    if box_title:
                        info_lines.append(f"[{box_title.get_text(strip=True)}]")
                        box_title.decompose()
                    for cont in item.find_all(["p", "li"], recursive=True):
                        txt = cont.get_text(strip=True)
                        if txt and len(txt) > 2:
                            info_lines.append(txt)
                info_text = "\n\n" + "\n".join(info_lines) if len(info_lines) > 1 else ""
            elif info_slide:
                raw = html_to_text(copy.copy(info_slide))
                if raw:
                    info_text = f"\n\n[{info_title}]\n{raw}"

        bg_gray_text = ""
        bc_for_gray = mp.find(class_="box_content")
        if bc_for_gray:
            for gray in bc_for_gray.find_all(class_="box_bg_gray", recursive=False):
                gray_txt = html_to_text(copy.copy(gray)).strip()
                if gray_txt:
                    bg_gray_text += "\n\n" + gray_txt

        accods = [aw for aw in mp.find_all(class_="accodWrap")
                  if "infocontWrap" not in aw.get("class", [])]

        if accods:
            if is_merge_as_one:
                bc = mp.find(class_="box_content")
                if bc:
                    bc2 = copy.copy(bc)
                    for aw in bc2.find_all(class_="infocontWrap"):
                        aw.decompose()
                    all_texts = []
                    for child in bc2.children:
                        if not hasattr(child, 'get'):
                            continue
                        cls = child.get('class', [])
                        if 'infocontWrap' in cls:
                            continue
                        if 'accodWrap' in cls:
                            btn = child.find("a", class_="accodBtn")
                            btn_txt = btn.get_text(strip=True) if btn else ""
                            slide = child.find(class_="accodSlide")
                            slide_txt = html_to_text(copy.copy(slide)) if slide else ""
                            combined = (f"[{btn_txt}]\n" if btn_txt else "") + slide_txt
                            if combined.strip():
                                all_texts.append(combined.strip())
                            continue
                        txt = html_to_text(copy.copy(child))
                        if txt.strip():
                            all_texts.append(txt.strip())
                    merged_text = "\n\n".join(all_texts)
                    if re.search(r'^바우처$', group_name):
                        merged_text = _trim_voucher_content(merged_text)
                    if merged_text.strip():
                        sections.append({
                            "group":               group_name,
                            "title":               group_name,
                            "content":             merged_text + bg_gray_text + info_text,
                            "slide_html":          str(bc2),
                            "is_notice":           False,
                            "is_안내":             False,
                            "forced_benefit_type": "서비스",
                        })
                continue

            for aw in accods:
                btn   = aw.find("a", class_="accodBtn")
                title = btn.get_text(strip=True) if btn else group_name
                slide = aw.find(class_="accodSlide")
                slide_html = str(slide) if slide else ""
                text  = html_to_text(copy.copy(slide)) if slide else ""

                if not text.strip():
                    continue

                full_content = text + bg_gray_text + info_text

                sections.append({
                    "group":               group_name,
                    "title":               title,
                    "content":             full_content,
                    "slide_html":          slide_html,
                    "is_notice":           False,
                    "is_안내":             is_안내_group,
                    "forced_benefit_type": forced_benefit_type,
                })
        else:
            bc = mp.find(class_="box_content")
            if not bc:
                continue

            if is_merge_as_one:
                bc2 = copy.copy(bc)
                for aw in bc2.find_all(class_="infocontWrap"):
                    aw.decompose()
                all_texts = []
                for child in bc2.children:
                    if not hasattr(child, 'get'):
                        continue
                    cls = child.get('class', [])
                    if 'infocontWrap' in cls:
                        continue
                    txt = html_to_text(copy.copy(child))
                    if txt.strip():
                        all_texts.append(txt.strip())
                merged_text = "\n\n".join(all_texts)
                if re.search(r'^바우처$', group_name):
                    merged_text = _trim_voucher_content(merged_text)
                if merged_text.strip():
                    sections.append({
                        "group":               group_name,
                        "title":               group_name,
                        "content":             merged_text + bg_gray_text + info_text,
                        "slide_html":          str(bc2),
                        "is_notice":           False,
                        "is_안내":             False,
                        "forced_benefit_type": "서비스",
                    })
                continue

            top_tits = bc.find_all(class_="box_top_tit", recursive=False)

            if top_tits:
                children = [c for c in bc.children if hasattr(c, 'get') and c.get('class')]
                current_title = group_name
                current_nodes = []

                for child in children:
                    cls = child.get('class', [])
                    if 'box_top_tit' in cls:
                        if current_nodes:
                            text = "\n".join(
                                html_to_text(copy.copy(n)) for n in current_nodes
                            ).strip()
                            if text:
                                full_text = current_title + "\n" + text if current_title and current_title != group_name else text
                                sections.append({
                                    "group":               group_name,
                                    "title":               current_title,
                                    "content":             full_text + bg_gray_text + info_text,
                                    "slide_html":          "".join(str(n) for n in current_nodes),
                                    "is_notice":           False,
                                    "is_안내":             is_안내_group,
                                    "forced_benefit_type": forced_benefit_type,
                                })
                        current_title = child.get_text(strip=True)
                        current_nodes = []
                    elif 'infocontWrap' not in cls and 'accodWrap' not in cls:
                        current_nodes.append(child)

                if current_nodes:
                    text = "\n".join(
                        html_to_text(copy.copy(n)) for n in current_nodes
                    ).strip()
                    if text:
                        full_text = current_title + "\n" + text if current_title and current_title != group_name else text
                        sections.append({
                            "group":               group_name,
                            "title":               current_title,
                            "content":             full_text + bg_gray_text + info_text,
                            "slide_html":          "".join(str(n) for n in current_nodes),
                            "is_notice":           False,
                            "is_안내":             is_안내_group,
                            "forced_benefit_type": forced_benefit_type,
                        })
            else:
                bc_copy = copy.copy(bc)
                for aw in bc_copy.find_all(class_="accodWrap"):
                    aw.decompose()
                text = html_to_text(bc_copy).strip()
                if not text:
                    continue
                sections.append({
                    "group":               group_name,
                    "title":               "",
                    "content":             text + info_text,
                    "slide_html":          str(bc),
                    "is_notice":           False,
                    "is_안내":             is_안내_group,
                    "forced_benefit_type": forced_benefit_type,
                })

    return sections


def extract_notice_from_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    notices = []

    for mp in soup.find_all(class_="modal_pop"):
        h = mp.find(["h1", "h2", "h3"])
        if not h:
            continue
        title = h.get_text(strip=True)
        if "유의사항" not in title:
            continue

        parts = []
        accods = mp.find_all(class_="accodWrap")
        if accods:
            for aw in accods:
                btn = aw.find("a", class_="accodBtn")
                sub_title = btn.get_text(strip=True) if btn else ""
                slide = aw.find(class_="accodSlide")
                content = slide.get_text("\n", strip=True) if slide else ""
                if not content:
                    if btn:
                        btn.decompose()
                    content = aw.get_text("\n", strip=True)
                if content.strip():
                    if sub_title:
                        parts.append(f"[{sub_title}]\n{content.strip()}")
                    else:
                        parts.append(content.strip())
        else:
            h.decompose()
            content = mp.get_text("\n", strip=True)
            if content.strip():
                parts.append(content.strip())

        if parts:
            full_content = f"[{title}]\n\n" + "\n\n".join(parts)
            notices.append({"label": title, "content": full_content})

    useinfo = soup.find("div", class_="useinfo")
    if useinfo:
        lines = ["[이용 안내]"]
        for li in useinfo.find_all("li"):
            if "dash_list" in (li.parent.get("class") or []):
                txt = li.get_text(" ", strip=True)
                if txt:
                    lines.append(f"  - {txt}")
            else:
                txt = li.get_text(" ", strip=True)
                if txt:
                    lines.append(txt)
        content = "\n".join(lines)
        notices.append({"label": "이용 안내", "content": content})

    return notices


def _trim_voucher_content(content: str) -> str:
    m = re.search(r'^(the\s+\S.*?바우처)\s*$', content, re.MULTILINE)
    if m:
        return content[m.start():].strip()
    return content
