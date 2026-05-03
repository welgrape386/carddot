"""
parser.py - 삼성카드 HTML → 구조화 데이터 파싱
  - 혜택 / 연회비 / 이벤트 / 공지 / 카드정보 row 생성
"""

import re
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

from config import CDN_BASE, CARD_COMPANY, BENEFIT_SEQ, NOTICE_ID_SEQ, BASE_URL
from crawler import fetch_html, log
from classifier import (
    get_region, get_benefit_type, get_unit_value, get_max_limit,
    get_benefit_summary, get_category_info,
    classify_evt_type, format_event_date, find_amounts,
    extract_min_amount, extract_performance_range,
    extract_max_limit, classify_on_offline, extract_max_count,
)


# ── HTML 텍스트 추출 헬퍼 ─────────────────────────────────────

def _get_text(el) -> str:
    soup = BeautifulSoup(str(el), "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    return soup.get_text("", strip=True)


def _has_class(tag, keyword: str) -> bool:
    return any(keyword in c for c in (tag.get("class") or []))


def _get_text_lines(elements) -> str:
    return "\n".join(txt for txt in [_get_text(el) for el in elements] if txt)


# ── benefit_content 추출 전략별 함수 ─────────────────────────

def _get_dt_dd_content(title_el) -> str:
    dds = []
    for sib in title_el.next_siblings:
        name = getattr(sib, "name", None)
        if name == "dt":
            break
        if name == "dd":
            dds.append(sib)
    return _get_text_lines(dds)


def _get_next_ul_content(title_el, ul_class_name: str) -> str:
    import pandas as pd
    from io import StringIO

    lines = []
    for sib in title_el.next_siblings:
        if not getattr(sib, "name", None):
            continue
        if sib.name in ["h5", "dt"]:
            break

        if sib.name == "ul" and ul_class_name in (sib.get("class") or []):
            table_box = sib.find(
                lambda tag: getattr(tag, "name", None) == "div"
                            and "table_col" in (tag.get("class") or [])
            )
            if table_box:
                table = table_box.find("table")
                if table:
                    # ── pd.read_html()로 파싱 (신한 방식)
                    try:
                        df = pd.read_html(StringIO(str(table)))[0]
                        headers = list(df.columns)
                        for _, row in df.iterrows():
                            parts = [f"{h}: {v}" for h, v in zip(headers, row)
                                     if str(v) not in ("nan", "-", "")]
                            if parts:
                                lines.append(" | ".join(parts))
                    except Exception:
                        # 파싱 실패 시 기존 방식 폴백
                        for tr in table_box.find_all("tr"):
                            row_parts = []
                            for cell in tr.find_all(["th", "td"], recursive=False):
                                txt = _get_text(cell)
                                if not txt:
                                    continue
                                row_parts.append(f"{txt} :" if "first" in (cell.get("class") or []) else txt)
                            if row_parts:
                                lines.append(
                                    row_parts[0] + " " + " | ".join(row_parts[1:])
                                    if len(row_parts) >= 2 and row_parts[0].endswith(" :")
                                    else " | ".join(row_parts)
                                )
                else:
                    # table 태그 없는 경우 기존 방식
                    for tr in table_box.find_all("tr"):
                        row_parts = []
                        for cell in tr.find_all(["th", "td"], recursive=False):
                            txt = _get_text(cell)
                            if not txt:
                                continue
                            row_parts.append(f"{txt} :" if "first" in (cell.get("class") or []) else txt)
                        if row_parts:
                            lines.append(
                                row_parts[0] + " " + " | ".join(row_parts[1:])
                                if len(row_parts) >= 2 and row_parts[0].endswith(" :")
                                else " | ".join(row_parts)
                            )

                for li in sib.find_all("li", recursive=False):
                    if li.find(lambda tag: getattr(tag, "name", None) == "div"
                               and "table_col" in (tag.get("class") or [])):
                        continue
                    if txt := _get_text(li):
                        lines.append(txt)
                break

            for li in sib.find_all("li", recursive=False):
                if txt := _get_text(li):
                    lines.append(txt)
            break

        if "table_col" in (sib.get("class") or []):
            table = sib.find("table")
            if table:
                try:
                    df = pd.read_html(StringIO(str(table)))[0]
                    headers = list(df.columns)
                    for _, row in df.iterrows():
                        parts = [f"{h}: {v}" for h, v in zip(headers, row)
                                 if str(v) not in ("nan", "-", "")]
                        if parts:
                            lines.append(" | ".join(parts))
                except Exception:
                    for tr in sib.find_all("tr"):
                        row_parts = []
                        for cell in tr.find_all(["th", "td"], recursive=False):
                            txt = _get_text(cell)
                            if not txt:
                                continue
                            row_parts.append(f"{txt} :" if "first" in (cell.get("class") or []) else txt)
                        if row_parts:
                            lines.append(
                                row_parts[0] + " " + " | ".join(row_parts[1:])
                                if len(row_parts) >= 2 and row_parts[0].endswith(" :")
                                else " | ".join(row_parts)
                            )
            break

    return "\n".join(lines)


def _get_wcms_txt_content(title_el) -> str:
    section = title_el.find_parent("section", class_="section-container")
    if not section:
        return ""
    lines, started = [], False
    for el in section.find_all(True):
        if el == title_el:
            started = True
            continue
        if not started:
            continue
        if _has_class(el, "wcms-tit"):
            break
        if _has_class(el, "wcms-txt"):
            if txt := _get_text(el):
                lines.append(txt)
    return "\n".join(lines)


def _get_only_wcms_txt_content(soup) -> str:
    lines = []
    for p in soup.find_all("p", class_=lambda x: x and "wcms-txt" in x):
        if txt := _get_text(p):
            lines.append(txt)
    return "\n".join(lines)


def _transpose_table_content(lines: list[str]) -> list[str]:
    # 패턴 1: "레이블 : 값1 | 값2 | 값3" — 기존 | 구분 패턴
    if any(" : " in l and " | " in l for l in lines):
        parsed = []
        non_table_lines = []
        for line in lines:
            if " : " in line and " | " in line:
                label, _, rest = line.partition(" : ")
                values = [v.strip() for v in rest.split(" | ")]
                parsed.append((label.strip(), values))
            else:
                non_table_lines.append(line)

        if not parsed:
            return lines

        max_cols = max(len(v) for _, v in parsed)
        result = []
        for col_idx in range(max_cols):
            parts = []
            for label, values in parsed:
                val = values[col_idx] if col_idx < len(values) else ""
                if val and val != "-":
                    parts.append(f"{label}: {val}")
            if parts:
                result.append(" | ".join(parts))
        return result + non_table_lines

    # 패턴 2: "헤더1 : 헤더2" / "값1 : 값2" — : 구분 표 패턴
    parsed = []
    non_table_lines = []
    for line in lines:
        if " : " in line:
            label, _, rest = line.partition(" : ")
            values = [v.strip() for v in rest.split(" : ")]
            is_table = len(values) > 1 and all(
                re.search(r"\d", v) for v in values if v and v != "-"
            )
            if is_table:
                parsed.append((label.strip(), values))
            else:
                non_table_lines.append(line)
        else:
            non_table_lines.append(line)

    if not parsed or len(parsed) < 2:
        return lines

    max_cols = max(len(v) for _, v in parsed)
    if max_cols <= 1:
        return lines

    # 첫 행이 헤더인지 확인 (숫자 없으면 헤더)
    headers = None
    if not re.search(r"\d", parsed[0][0]) and all(
        not re.search(r"\d", v) for v in parsed[0][1]
    ):
        headers = [parsed[0][0]] + parsed[0][1]
        parsed  = parsed[1:]

    if not parsed:
        return lines

    result = []
    for col_idx in range(max_cols):
        parts = []
        for label, values in parsed:
            val = values[col_idx] if col_idx < len(values) else ""
            if val and val not in ("-", "없음"):
                col_name = headers[col_idx] if headers and col_idx < len(headers) else label
                parts.append(f"{col_name}: {val}")
        if parts:
            result.append(" | ".join(parts))

    return result + non_table_lines



# ── 혜택 row 빌더 ─────────────────────────────────────────────

def _build_benefit_row(card_id, tab_name, serviceName, benefit_title, benefit_content, row_type, updated_at):
    
    # 공통 추출 (유의사항/일반혜택 모두 사용)
    perf_level, perf_min, perf_max = extract_performance_range(benefit_content)
    min_amount                     = extract_min_amount(benefit_content)
    max_limit, max_limit_unit      = extract_max_limit(benefit_content)
    on_offline                     = classify_on_offline(tab_name, benefit_content)
    max_count                      = extract_max_count(benefit_content)

    if row_type == "유의사항":
        return {
            "benefit_id":         next(BENEFIT_SEQ),
            "card_id":            card_id,
            "row_type":           "유의사항",
            "benefit_group":      tab_name,
            "benefit_title":      benefit_title,
            "benefit_summary":    benefit_content[:120],
            "benefit_content":    benefit_content,
            "category":           "",
            "category_id":        "",
            "on_offline":         "",
            "benefit_type":       "",
            "benefit_value":      "",
            "benefit_unit":       "",
            "target_merchants":   "",
            "excluded_merchants": "",
            "performance_level":  "",
            "performance_min":    "",
            "performance_max":    "",
            "min_amount":         "",
            "max_count":          "",
            "max_limit":          "",
            "max_limit_unit":     "",
            "updated_at":         updated_at,
            "benefit_main_title": serviceName,
        }

    clean_text = re.sub(r"전월\s*이용금액:\s*\d+만원\s*(?:이상|미만)(?:\s*~\s*\d+만원\s*미만)?\s*\|?\s*", "", benefit_content)
    clean_text = re.sub(r"소득\s*\d+%", "", clean_text)
    b_type  = get_benefit_type(benefit_content)
    unit, v = get_unit_value(clean_text)       # ← clean_text로만 추출
    summary = get_benefit_summary(benefit_content)
    merchants, cat_id, cat = get_category_info(benefit_content)

    return {
        "benefit_id":         next(BENEFIT_SEQ),
        "card_id":            card_id,
        "row_type":           row_type,
        "benefit_group":      tab_name,
        "benefit_title":      benefit_title,
        "benefit_summary":    summary,
        "benefit_content":    benefit_content,
        "category":           cat,
        "category_id":        cat_id,
        "on_offline":         on_offline,
        "benefit_type":       b_type,
        "benefit_value":      v,
        "benefit_unit":       unit,
        "target_merchants":   merchants,
        "excluded_merchants": "",
        "performance_level":  perf_level,
        "performance_min":    perf_min,
        "performance_max":    perf_max,
        "min_amount":         min_amount,
        "max_count":          max_count,
        "max_limit":          max_limit,
        "max_limit_unit":     max_limit_unit,
        "updated_at":         updated_at,
        "benefit_main_title": serviceName,
    }


# ── 혜택 파싱 ─────────────────────────────────────────────────

async def parse_benefits(card_id: str, nuxt_data: dict, session: aiohttp.ClientSession) -> list[dict]:
    rows       = []
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bubbles    = nuxt_data.get("wcms", {}).get("detail", {}).get("bubble", [])

    for b in bubbles:
        tab_name    = b.get("tabName") or b.get("title") or ""
        serviceName = b.get("serviceName") or ""

        if tab_name:
            rows.append(_build_benefit_row(card_id, tab_name, serviceName, tab_name, tab_name, "주요혜택", updated_at))

        svc_url = b.get("serviceUrl", "")
        if not svc_url:
            continue

        benefit_html = await fetch_html(session, svc_url)
        soup         = BeautifulSoup(benefit_html, "html.parser")
        found        = False

        selector_map = {
            "h5.tit04":             ("h5.tit04", "txt_list"),
            "h5.tit":               ("h5.tit",   "shopList"),
            'p[class*="wcms-tit"]': None,
            "dt":                   None,
        }

        for selector in selector_map:
            title_lines: dict[str, list] = {}
            title_order = []

            for title_el in soup.select(selector):
                benefit_title = _get_text(title_el)
                if not benefit_title:
                    continue

                if selector == "dt":
                    benefit_content = _get_dt_dd_content(title_el)
                elif selector == 'p[class*="wcms-tit"]':
                    benefit_content = _get_wcms_txt_content(title_el)
                elif selector == "h5.tit04":
                    benefit_content = _get_next_ul_content(title_el, "txt_list")
                else:
                    benefit_content = _get_next_ul_content(title_el, "shopList")

                row_type  = "유의사항" if (selector == "h5.tit04" and "유의사항" in benefit_title) else "상세혜택"
                raw_lines = [l.strip() for l in benefit_content.splitlines() if l.strip()]

                if benefit_title not in title_lines:
                    title_lines[benefit_title] = []
                    title_order.append((benefit_title, row_type))
                title_lines[benefit_title].extend(raw_lines)

            for benefit_title, row_type in title_order:
                converted = _transpose_table_content(title_lines[benefit_title])
                for line in converted:
                    rows.append(_build_benefit_row(card_id, tab_name, serviceName, benefit_title, line, row_type, updated_at))

            if title_lines:
                found = True

        if not found and serviceName:
            benefit_content = _get_only_wcms_txt_content(soup)
            content_lines   = [l.strip() for l in benefit_content.splitlines() if l.strip()]
            for line in _transpose_table_content(content_lines):
                rows.append(_build_benefit_row(card_id, tab_name, serviceName, serviceName, line, "상세혜택", updated_at))

    return rows

# ── 연회비 파싱 ───────────────────────────────────────────────

def _fee_clean(text) -> str:
    text = BeautifulSoup(str(text or ""), "html.parser").get_text(" ", strip=True)
    text = text.replace("총연회비", "총 연회비").replace("기본연회비", "기본 연회비").replace("제휴연회비", "제휴 연회비")
    text = text.replace("( ", "(").replace(" )", ")")
    text = re.sub(r"(\d[\d,]*)\s+(원)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip()


def _fee_expand(trs) -> list[list]:
    rows, spans = [], {}
    for tr in trs:
        row, col = [], 0
        for cell in tr.find_all(["th", "td"], recursive=False):
            while col in spans:
                row.append(spans[col]["text"])
                spans[col]["left"] -= 1
                if spans[col]["left"] == 0:
                    del spans[col]
                col += 1
            text    = _fee_clean(cell)
            rowspan = int(cell.get("rowspan", 1) or 1)
            colspan = int(cell.get("colspan", 1) or 1)
            for i in range(colspan):
                row.append(text)
                if rowspan > 1:
                    spans[col + i] = {"text": text, "left": rowspan - 1}
            col += colspan
        while col in spans:
            row.append(spans[col]["text"])
            spans[col]["left"] -= 1
            if spans[col]["left"] == 0:
                del spans[col]
            col += 1
        rows.append(row)
    return rows


def _make_fee_row(card_id, title, content, updated_at):
    unit, value = get_unit_value(content)
    return {
        "benefit_id":         next(BENEFIT_SEQ),
        "card_id":            card_id,
        "row_type":           "연회비",
        "benefit_group":      "연회비",
        "benefit_title":      title,
        "benefit_summary":            content[:120],
        "benefit_content":    content,
        "category":           "",
        "category_id":        "",
        "on_offline":         "",
        "benefit_type":       "",
        "benefit_value":      value,
        "benefit_unit":       unit,
        "target_merchants":   "",
        "excluded_merchants": "",
        "performance_level":  "",
        "performance_min":    "",
        "performance_max":    "",
        "min_amount":         "",
        "max_count":          "",
        "max_limit":          "",
        "max_limit_unit":     "",
        "updated_at":         updated_at,
        "benefit_main_title": title,
    }
async def parse_fees(card_id: str, nuxt_data: dict, session: aiohttp.ClientSession) -> list[dict]:
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows       = []
    fee_url    = nuxt_data.get("wcms", {}).get("detail", {}).get("htmlList", {}).get("feeUrl", "")
    if not fee_url:
        return rows

    fee_html = await fetch_html(session, fee_url)
    soup     = BeautifulSoup(fee_html, "html.parser")

    for indv in soup.select("article.terms > div.indv"):
        title = _fee_clean(indv.select_one("h4.t_web_em"))
        if not title:
            continue

        table = indv.find("table")
        if table:
            head_rows = _fee_expand(table.select("thead tr"))
            max_cols  = max((len(r) for r in head_rows), default=0)
            headers   = []
            for i in range(1, max_cols):
                parts = []
                for r in head_rows:
                    txt = r[i] if i < len(r) else ""
                    if txt and txt != "구분" and txt not in parts:
                        parts.append(txt)
                headers.append(" ".join(parts).strip())

            for r in _fee_expand(table.select("tbody tr")):
                fee_type = _fee_clean(r[0] if r else "")
                if not fee_type:
                    continue
                for i, header in enumerate(headers, start=1):
                    if not header:
                        continue
                    amount = _fee_clean(r[i] if i < len(r) else "") or "없음"
                    rows.append(_make_fee_row(card_id, title, f"{header} {fee_type} {amount}", updated_at))

        notes = []
        for el in indv.select(".btm_info .alert_s_new, .btm_info li"):
            if (txt := _fee_clean(el)) and txt not in notes:
                notes.append(txt)
        for txt in notes:
            rows.append(_make_fee_row(card_id, title, txt, updated_at))

    # 연회비 유의사항
    notice_lines = []
    for box in soup.select(".b_note .list_box_nt"):
        h4 = box.select_one("h4.tit04")
        if not h4 or "유의사항" not in _get_text(h4):
            continue
        for li in box.select("ul.txt_list > li"):
            if txt := _get_text(li):
                notice_lines.append(txt)
        break

    if notice_lines:
        for line in notice_lines:
            line = line.strip()
            if not line:
                continue
            rows.append({
                "benefit_id":         next(BENEFIT_SEQ),
                "card_id":            card_id,
                "row_type":           "유의사항",
                "benefit_group":      "연회비",
                "benefit_title":      "연회비 유의사항",
                "benefit_summary":            line[:120],
                "benefit_content":    line,
                "category":           "",
                "category_id":        "",
                "on_offline":         "",
                "benefit_type":       "",
                "benefit_value":      "",
                "benefit_unit":       "",
                "target_merchants":   "",
                "excluded_merchants": "",
                "performance_level":  "",
                "performance_min":    "",
                "performance_max":    "",
                "min_amount":         "",
                "max_count":          "",
                "max_limit":          "",
                "max_limit_unit":     "",
                "updated_at":         updated_at,
                "benefit_main_title": "연회비 유의사항",
            })
    return rows

# ── 이벤트 파싱 ───────────────────────────────────────────────

def _extract_li_lines(li) -> list:
    lines = []
    li_copy = BeautifulSoup(str(li), "html.parser").find("li")
    for tag in li_copy.find_all(["ul", "div"]):
        tag.decompose()
    for br in li_copy.find_all("br"):
        br.replace_with("|||")
    txt = li_copy.get_text("", strip=True)
    for line in txt.split("|||"):
        if line := line.strip():
            lines.append(line)

    # 하위 ul li 처리 (직계 + span 직계)
    target_uls = li.find_all("ul", recursive=False)
    for span in li.find_all("span", recursive=False):
        target_uls += span.find_all("ul", recursive=False)

    for ul in target_uls:
        for sub_li in ul.find_all("li", recursive=False):
            sub_copy = BeautifulSoup(str(sub_li), "html.parser").find("li")
            for tag in sub_copy.find_all(["ul", "div"]):
                tag.decompose()
            if txt := sub_copy.get_text("", strip=True):
                lines.append(txt)
            # 한 단계 더
            for sub_ul in sub_li.find_all("ul", recursive=False):
                for sub_sub_li in sub_ul.find_all("li", recursive=False):
                    if txt := _get_text(sub_sub_li).strip():
                        lines.append(txt)

    return lines

def _parse_event_sections(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    sections = []
    cur_section, cur_lines = "기타", []

    for box in soup.select(".list_box_nt"):
        p = box.select_one("p > strong")
        if p:
            if cur_lines:
                sections.append({"section": cur_section, "content": "\n".join(cur_lines)})
            cur_section = _get_text(p).strip()
            cur_lines = []

        top_ul = box.select_one("ul.txt_list")
        if not top_ul:
            continue
        for li in top_ul.find_all("li", recursive=False):
            tit = li.find("strong", class_="e_tit")
            if tit:
                if cur_lines:
                    sections.append({"section": cur_section, "content": "\n".join(cur_lines)})
                cur_section = _get_text(tit).strip()
                tit.decompose()
                cur_lines = []
            cur_lines.extend(_extract_li_lines(li))

    if cur_lines:
        sections.append({"section": cur_section, "content": "\n".join(cur_lines)})

    return sections


async def parse_events(card_id: str, nuxt_data: dict, session: aiohttp.ClientSession) -> list[dict]:
    rows      = []
    card_name = BeautifulSoup(
        str(nuxt_data.get("wcms", {}).get("detail", {}).get("cardTitle", "")),
        "html.parser"
    ).get_text(" ", strip=True)
    banner_list = [x for x in nuxt_data.get("bannerList", []) if x.get("code") == card_id]

    for banner in banner_list:
        evt_url = banner.get("evtUrl", "")
        if not evt_url:
            continue
        event_url  = evt_url if evt_url.startswith("http") else CDN_BASE + evt_url
        event_html = await fetch_html(session, evt_url)
        sections   = _parse_event_sections(event_html)

        if not sections:
            sections = [{"section": "기타", "content": ""}]

        full_content = " ".join(sec["content"] for sec in sections)
        event_type   = classify_evt_type(full_content or banner.get("evtTitle", ""))

        for sec in sections:
            for line in sec["content"].splitlines():
                line = line.strip()
                if not line:
                    continue
                rows.append({
                    "card_id":           card_id,
                    "company":           CARD_COMPANY,
                    "card_name":         card_name,
                    "origin_event_code": banner.get("id", ""),
                    "event_title":       banner.get("evtTitle", ""),
                    "event_link":        event_url,
                    "start_date":        format_event_date(banner.get("sDate", "")),
                    "end_date":          format_event_date(banner.get("eDate", "")),
                    "event_type":        event_type,
                    "section":           sec["section"],
                    "event_content":     line,
                    "updated_at":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
    return rows


# ── 공지 파싱 ─────────────────────────────────────────────────

def _html_to_lines(soup) -> list[str]:
    html = re.sub(r'<!--.*?-->', '', str(soup), flags=re.S)
    soup = BeautifulSoup(html, "html.parser")
    root = soup.body or soup
    lines, tags = [], root.find_all(recursive=False)
    if not tags:
        text = root.get_text(" ", strip=True)
        return [text] if text else []
    for tag in tags:
        if tag.name in ["ol", "ul"]:
            lines += [li.get_text(" ", strip=True) for li in tag.find_all("li")]
        elif text := tag.get_text(" ", strip=True):
            lines.append(text)
    return lines


def _get_notice_li_lines(li) -> list[str]:
    lines   = []
    li_copy = BeautifulSoup(str(li), "html.parser").find("li")
    for tag in li_copy.find_all(["ul", "ol"]):
        tag.decompose()
    if text := li_copy.get_text(" ", strip=True):
        lines.append(text)
    for ul in li.find_all(["ul", "ol"], recursive=False):
        for sub_li in ul.find_all("li", recursive=False):
            lines += _get_notice_li_lines(sub_li)
    return lines


async def parse_notices(card_id: str, nuxt_data: dict, session: aiohttp.ClientSession) -> list[dict]:
    html_list  = nuxt_data.get("wcms", {}).get("detail", {}).get("htmlList", {})
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows       = []

    def _row(category, content):
        return {
            "notice_id":    next(NOTICE_ID_SEQ),
            "card_id":      card_id,
            "notice_category":     category,
            "sub_category": category,
            "notice_content":      content,
            "updated_at":   updated_at,
        }

    # 필수안내사항
    notice_html = await fetch_html(session, CDN_BASE + html_list["noticeUrl"])
    notice_soup = BeautifulSoup(notice_html, "html.parser")
    for wrap in notice_soup.select("div.notice-wrap"):
        title_el = wrap.select_one("p.notice-title")
        if not title_el:
            continue
        title = title_el.get_text("", strip=True).replace(" ", "")
        if title != "필수안내사항":
            continue
        ul = wrap.select_one("ul")
        if not ul:
            continue
        for li in ul.find_all("li", recursive=False):
            for content in _get_notice_li_lines(li):
                rows.append(_row("필수안내사항", content))

    # 기타안내
    etc_html = await fetch_html(session, CDN_BASE + html_list["etcUrl"])
    if "Forbidden" in etc_html:
        log(f"{card_id} etcUrl 403 skip")
        etc_soup = BeautifulSoup("", "html.parser")
    else:
        etc_soup = BeautifulSoup(etc_html, "html.parser")

    # 부가서비스안내
    add_html  = await fetch_html(session, CDN_BASE + html_list["addServiceUrl"])
    add_soup  = BeautifulSoup(add_html, "html.parser")
    for content in _html_to_lines(add_soup):
        rows.append(_row("부가서비스 변경 가능 사유", content))
    for content in _html_to_lines(etc_soup):
        rows.append(_row("기타안내사항", content))

    return rows


# ── 카드정보 파싱 ─────────────────────────────────────────────

def _get_network(fee_soup) -> str:
    brands     = []
    brand_list = ["Master", "VISA", "UnionPay", "Amex"]
    for th in fee_soup.select("table thead th"):
        text = _get_text(th)
        for brand in brand_list:
            if brand.lower() in text.lower() and brand not in brands:
                brands.append(brand)
        for img in th.find_all("img"):
            for brand in brand_list:
                if brand.lower() in img.get("alt", "").lower() and brand not in brands:
                    brands.append(brand)
    if not brands:
        header_text = _get_text(fee_soup.select_one("table thead")) if fee_soup.select_one("table thead") else ""
        if "해외겸용" in header_text:
            brands.append("Master")
    return ", ".join(brands)


def _get_annual_fee_info(fee_soup) -> dict:
    info = {
        "annual_fee_dom_basic": 0, "annual_fee_dom_premium": 0,
        "annual_fee_for_basic": 0, "annual_fee_for_premium": 0,
        "annual_fee_notes":     "",
    }
    affiliate_domestic = affiliate_overseas = ""
    has_transit = "후불교통" in fee_soup.get_text(" ", strip=True)

    for indv in fee_soup.select("div.indv"):
        h4 = indv.select_one("h4")
        if not h4:
            continue
        title     = _fee_clean(h4)
        is_family = "가족" in title
        table     = indv.find("table")
        if not table:
            continue

        head_rows = _fee_expand(table.select("thead tr"))
        max_cols  = max((len(r) for r in head_rows), default=0)
        headers   = []
        for i in range(1, max_cols):
            parts = []
            for r in head_rows:
                txt = _fee_clean(r[i]) if i < len(r) else ""
                if txt and txt != "구분" and txt not in parts:
                    parts.append(txt)
            headers.append(" ".join(parts))

        for row in _fee_expand(table.select("tbody tr")):
            if len(row) < 2:
                continue
            label  = _fee_clean(row[0]).replace(" ", "")
            values = []
            for cell in row[1:]:
                text = _fee_clean(cell).replace(",", "").replace("원", "").strip()
                values.append(text if text.isdigit() else "")

            if "총" in label and "연회비" in label:
                if len(values) == 1:
                    key = "premium" if is_family else "basic"
                    info[f"annual_fee_dom_{key}"] = values[0]
                    info[f"annual_fee_for_{key}"] = values[0]
                else:
                    for i, val in enumerate(values):
                        if not val:
                            continue
                        header = headers[i] if i < len(headers) else ""
                        key    = "premium" if is_family else "basic"
                        if "국내" in header or i == 1:
                            info[f"annual_fee_dom_{key}"] = val
                        elif "해외" in header or i == 0:
                            info[f"annual_fee_for_{key}"] = val

            elif "제휴" in label and "연회비" in label and not is_family:
                if len(values) == 1:
                    affiliate_domestic = affiliate_overseas = values[0]
                else:
                    for i, val in enumerate(values):
                        if not val:
                            continue
                        header = headers[i] if i < len(headers) else ""
                        if "국내" in header or i == 1:
                            affiliate_domestic = val
                        elif "해외" in header or i == 0:
                            affiliate_overseas = val

    note_parts = []
    if affiliate_domestic and affiliate_overseas and affiliate_domestic == affiliate_overseas:
        note_parts.append(f"제휴연회비 {int(affiliate_domestic):,}원")
    else:
        if affiliate_domestic:
            note_parts.append(f"제휴연회비(국내) {int(affiliate_domestic):,}원")
        if affiliate_overseas:
            note_parts.append(f"제휴연회비(해외) {int(affiliate_overseas):,}원")
    if has_transit:
        note_parts.append("후불교통 포함")
    info["annual_fee_note"] = " / ".join(note_parts)
    return info


TITLE_REPLACE = {
    "많이 쓰는 영역 30% 자동 맞춤 할인 (삼성 iD ON 카드)": "많이 쓰는 영역 30% 자동 맞춤 할인",
    "놀이공원할인서비스_일반(한국민속촌 포함)": "놀이공원 할인 서비스",
}
EXCLUDE_TITLES = [
    "카드이용TIP", "카드 디자인 소개", "컨택리스(비접촉) 결제 지원",
    "후불 교통카드 기능", "옵션패키지 자세히 보기", "이용처 안내",
    "CGV 3,000원 할인", "CGV 온라인가맹점 3천원 현장할인 (체크카드)",
    "해외 빅포인트 1.3% 적립 (taptap)", "라이프스타일 패키지(옵션 패키지 중 택1)",
    "아멕스 PLATINUM 등급 서비스",
]

def _get_summary(nuxt_data: dict) -> str:
    bubbles = nuxt_data.get("wcms", {}).get("detail", {}).get("bubble", [])
    titles = []
    for b in bubbles:
        title = (b.get("title") or "").strip()
        if not title or not b.get("serviceUrl", ""):
            continue
        if title in EXCLUDE_TITLES:
            continue
        title = TITLE_REPLACE.get(title, title)
        titles.append(title)
    return " / ".join(titles[:3])


def _get_image_url(nuxt_data: dict) -> str:
    img_info = nuxt_data.get("wcms", {}).get("detail", {}).get("imgInfo", {})
    pc_img1  = img_info.get("pcImg1", "")
    return CDN_BASE + pc_img1 if pc_img1 else ""


def _get_spending_info(benefit_rows: list) -> dict:
    amounts = []
    for row in benefit_rows:
        if row.get("row_type") != "상세혜택":
            continue
        text = row.get("benefit_content", "")
        if "전월" not in text and "실적" not in text:
            continue
        for price in re.findall(r"(\d[\d,]*)\s*만원", text):
            num = str(int(price.replace(",", "")) * 10000)
            if num not in amounts:
                amounts.append(num)
    amounts.sort(key=int)
    return {"min_performance": amounts[0] if amounts else ""}
    


async def parse_card_info(card_id: str, nuxt_data: dict, session: aiohttp.ClientSession, benefit_rows: list) -> dict:
    html_list = nuxt_data.get("wcms", {}).get("detail", {}).get("htmlList", {})
    card_name = BeautifulSoup(
        str(nuxt_data.get("wcms", {}).get("detail", {}).get("cardTitle", "")),
        "html.parser"
    ).get_text(" ", strip=True).strip()
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 카드 타입 분리
    card_type = "신용"
    for t in ["신용", "체크", "하이브리드", "직불"]:
        if card_name.endswith(f"({t})"):
            card_type = t
            card_name = card_name[:-len(f"({t})")].strip()
            break
        if card_name.endswith(t):
            card_type = t
            card_name = card_name[:-len(t)].strip()
            break
    if card_type == "신용":
        if "체크" in card_name or card_id.startswith("ABP"):
            card_type = "체크"
        elif "하이브리드" in card_name:
            card_type = "하이브리드"

    fee_html     = await fetch_html(session, CDN_BASE + html_list["feeUrl"])
    fee_soup     = BeautifulSoup(fee_html, "html.parser")
    network      = _get_network(fee_soup) or "Local"
    has_transit  = "True" if "후불교통" in fee_soup.get_text(" ", strip=True) else "False"
    is_dom_for   = "True" if any(b in network for b in ["Master", "VISA", "UnionPay", "Amex"]) else "False"
    annual_fee   = _get_annual_fee_info(fee_soup)
    summary      = _get_summary(nuxt_data)
    image_url    = _get_image_url(nuxt_data)
    spending     = _get_spending_info(benefit_rows)
    has_cashback = "TRUE" if "캐시백" in summary else "FALSE"

    return {
        "card_id":                    card_id,
        "company":                    CARD_COMPANY,
        "card_name":                  card_name,
        "card_type":                  card_type,
        "network":                    network,
        "is_domestic_foreign":        is_dom_for,
        "has_transport":                has_transit,
        "annual_fee_dom_basic":   annual_fee["annual_fee_dom_basic"] or 0,
        "annual_fee_dom_premium": annual_fee["annual_fee_dom_premium"] or 0,
        "annual_fee_for_basic":   annual_fee["annual_fee_for_basic"] or 0,
        "annual_fee_for_premium": annual_fee["annual_fee_for_premium"] or 0,
        "annual_fee_notes":           annual_fee.get("annual_fee_note", ""),
        "min_performance":            spending["min_performance"],
        "summary":                    summary, 
        "image_url":                  image_url,
        "link_url":                   BASE_URL + card_id,
        "has_cashback":               has_cashback,
        "updated_at":                 updated_at,
    }