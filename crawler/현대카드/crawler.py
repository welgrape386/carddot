"""
crawler.py - Playwright로 페이지 접속 및 raw 데이터 수집
"""

import re
from datetime import datetime
from playwright.async_api import async_playwright

from config import IMG_BASE_URL, COMPANY_MAP, CARD_ID_PATTERN, BROWSER_HEADLESS, USER_AGENT
from utils  import clean, parse_fee, parse_networks, remove_comma


# =============================================
# URL 메타 추출
# =============================================

def extract_card_id(url: str) -> str:
    m = CARD_ID_PATTERN.search(url)
    return m.group(1) if m else "UNKNOWN"


def extract_company(url: str) -> str:
    for domain, company in COMPANY_MAP.items():
        if domain in url:
            return company
    return "알수없음"


# =============================================
# 공통 유틸
# =============================================

async def get_text_lines(el) -> list:
    """
    요소 내부 텍스트를 br 기준으로 줄 분리
    inner_text()는 br을 무시하므로 innerHTML에서 br → \n 치환 후 처리
    HTML 엔티티(&gt; 등)는 unescape로 복원
    """
    import html as html_mod
    raw_html = await el.inner_html()
    # br 태그를 줄바꿈으로 변환
    raw_html = re.sub(r'<br\s*/?>', '\n', raw_html, flags=re.IGNORECASE)
    # 나머지 태그 제거
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    # HTML 엔티티 복원 (&gt; → >, &amp; → & 등)
    text = html_mod.unescape(text)
    # 줄 분리 및 정리
    lines = [clean(l) for l in text.splitlines() if clean(l)]
    return lines


# =============================================
# card_info 수집
# =============================================

async def crawl_card_info(page, url: str) -> dict:
    card_id = extract_card_id(url)
    company = extract_company(url)

    el = await page.query_selector("h2.h0_eb_size55")
    card_name = clean(await el.inner_text()) if el else card_id

    all_text = await page.inner_text("body")
    card_type = "체크" if "체크카드" in all_text else "신용"

    network_raws = []
    fee_map = {}
    for li in await page.query_selector_all("#viewYearPay li"):
        span_el = await li.query_selector("span")
        p_el    = await li.query_selector("p")
        if not span_el:
            continue
        span_text = clean(await span_el.inner_text())
        fee_val   = parse_fee(clean(await p_el.inner_text()) if p_el else "0")
        network_raws.append(span_text)
        for brand in parse_networks([span_text]):
            fee_map[brand] = fee_val
        if "국내전용" in span_text:
            fee_map["국내전용"] = fee_val

    networks = parse_networks(network_raws)
    network  = ", ".join(networks)
    is_domestic_foreign = any(
        n in networks for n in ["Visa", "Amex", "Master", "Mastercard", "JCB", "UnionPay"]
    )
    annual_fee_for_basic   = fee_map.get("Visa") or fee_map.get("Amex") or fee_map.get("Master") or 0
    annual_fee_dom_basic   = fee_map.get("국내전용", 0)
    annual_fee_for_premium = 0
    annual_fee_dom_premium = 0

    annual_fee_notes = ""
    info_ul = await page.query_selector("ul.info-detail")
    if info_ul:
        seen = []
        for li in await info_ul.query_selector_all("li"):
            raw = remove_comma(clean(await li.inner_text()))
            lines = [l.strip() for l in re.split(r'\s{2,}|\n', raw) if l.strip()]
            for line in lines:
                if re.search(r'\d+원', line) and line not in seen:
                    if not re.match(r'^국내', line):
                        seen.append(line)
        annual_fee_notes = " / ".join(seen)

    has_transport = "후불교통" in all_text

    perf_vals = sorted(set(
        int(x) * 10000
        for x in re.findall(r"전월\s*이용\s*금액\s*(\d+)만원", all_text)
        if 1 <= int(x) * 10000 <= 10_000_000
    ))
    min_performance = perf_vals[0] if perf_vals else 0

    summary_parts = [
        clean(await el.inner_text())
        for el in await page.query_selector_all(".card_tit_wrap ul li")
    ]
    summary = " / ".join([s for s in summary_parts if s])

    image_url = ""
    all_imgs  = await page.query_selector_all("img")
    for pattern in [
        lambda s: card_id in s and "_h.png" in s,
        lambda s: card_id in s and "_f.png" in s and "/card/" in s,
        lambda s: card_id in s and s.endswith(".png") and "/card/" in s,
    ]:
        for img in all_imgs:
            src = await img.get_attribute("src") or ""
            if pattern(src):
                image_url = (IMG_BASE_URL + src) if src.startswith("/") else src
                break
        if image_url:
            break

    has_cashback = any(
        kw in all_text
        for kw in ["캐시백", "연회비 환급", "연회비 반환", "연회비 지원", "연회비 적립", "연회비 면제"]
    )

    return {
        "card_id":                card_id,
        "company":                company,
        "card_name":              card_name,
        "card_type":              card_type,
        "network":                network,
        "is_domestic_foreign":    is_domestic_foreign,
        "has_transport":          has_transport,
        "annual_fee_dom_basic":   annual_fee_dom_basic,
        "annual_fee_dom_premium": annual_fee_dom_premium,
        "annual_fee_for_basic":   annual_fee_for_basic,
        "annual_fee_for_premium": annual_fee_for_premium,
        "annual_fee_notes":       annual_fee_notes,
        "min_performance":        min_performance,
        "summary":                summary,
        "image_url":              image_url,
        "link_url":               url,
        "has_cashback":           has_cashback,
        "updated_at":             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# =============================================
# 주요혜택 수집 (메인 페이지 노출 영역)
# =============================================

async def get_popup_group(page, item_el) -> str:
    link = await item_el.query_selector(".link")
    if not link:
        return ""
    href = await link.get_attribute("href") or ""
    m = re.search(r"popup\.open\('([^']+)'", href)
    if not m:
        return ""
    pop_id = m.group(1)
    pop_el = await page.query_selector(f"#{pop_id}")
    if not pop_el:
        return ""
    h1 = await pop_el.query_selector("h1")
    return clean(await h1.inner_text()) if h1 else ""


async def get_item_contents(item_el) -> dict:
    em_el = await item_el.query_selector(".item_tit em")
    em_text = clean(await em_el.inner_text()) if em_el else ""

    sub_el = await item_el.query_selector(".sub_txt")
    sub_text = clean(await sub_el.inner_text()) if sub_el else ""

    sub_p_texts = set()
    if sub_el:
        for p in await sub_el.query_selector_all("p"):
            sub_p_texts.add(clean(await p.inner_text()))

    p_texts = []
    for p in await item_el.query_selector_all("p"):
        t = clean(await p.inner_text())
        if t and t not in sub_p_texts:
            p_texts.append(t)

    dl_texts = []
    for dl in await item_el.query_selector_all("dl"):
        dt_el = await dl.query_selector("dt")
        dd_el = await dl.query_selector("dd")
        if dt_el and dd_el:
            dl_texts.append(f"{clean(await dt_el.inner_text())} {clean(await dd_el.inner_text())}")

    return {
        "em_text":  em_text,
        "p_texts":  p_texts,
        "dl_texts": dl_texts,
        "sub_text": sub_text,
    }


async def crawl_main_benefits(page, card_id: str) -> list:
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    def make_row(benefit_group, benefit_title, content):
        return {
            "benefit_id":         "",
            "card_id":            card_id,
            "row_type":           "주요혜택",
            "benefit_group":      benefit_group,
            "benefit_title":      benefit_title,
            "benefit_summary":    "",
            "benefit_content":    content,
            "category":           "",
            "category_id":        "",
            "on_offline":         "",
            "region":             "",
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
            "updated_at":         now,
        }

    boxes = await page.query_selector_all("#cms_area .box_card_type")
    for box in boxes:
        current_cate = ""
        children = await box.query_selector_all(":scope > *")
        for child in children:
            cls = await child.get_attribute("class") or ""
            if "cate_tit" in cls:
                p_el = await child.query_selector("p")
                current_cate = clean(await p_el.inner_text()) if p_el else clean(await child.inner_text())
            elif "item_wrap" in cls:
                inner_children = await child.query_selector_all(":scope > *")
                for inner in inner_children:
                    inner_cls = await inner.get_attribute("class") or ""
                    if "cate_tit" in inner_cls:
                        p_el = await inner.query_selector("p")
                        current_cate = clean(await p_el.inner_text()) if p_el else clean(await inner.inner_text())
                    elif "item" in inner_cls:
                        benefit_group = await get_popup_group(page, inner)
                        contents      = await get_item_contents(inner)
                        if contents["em_text"]:
                            rows.append(make_row(benefit_group, current_cate, contents["em_text"]))
                        for p_text in contents["p_texts"]:
                            rows.append(make_row(benefit_group, current_cate, p_text))
                        for dl_text in contents["dl_texts"]:
                            rows.append(make_row(benefit_group, current_cate, dl_text))
                        if contents["sub_text"]:
                            rows.append(make_row(benefit_group, current_cate, contents["sub_text"]))

    print(f"  주요혜택 {len(rows)}행 수집")
    return rows


# =============================================
# 상세혜택 수집 (팝업 내용)
# =============================================

async def parse_ul_lines(ul_el) -> list:
    """
    ul 재귀 파싱
    - li 직접 텍스트: br 기준 줄 분리, 자식 ul/table 텍스트 제외
    - li 안 table: 헤더:값 / 형식으로 행 변환
    - 자식 ul 재귀
    """
    lines = []
    for li in await ul_el.query_selector_all(":scope > li"):
        child_ul    = await li.query_selector("ul")
        child_table = await li.query_selector("table")

        # li 직접 텍스트: br 기준 줄 분리, 자식 ul/table 제외
        li_html = await li.inner_html()
        # 자식 ul/table HTML 제거 (evaluate로 outerHTML 추출)
        if child_ul:
            ul_html = await child_ul.evaluate("el => el.outerHTML")
            li_html = li_html.replace(ul_html, "")
        if child_table:
            box_tbl = await li.query_selector(".box_table")
            tbl_html = await (box_tbl or child_table).evaluate("el => el.outerHTML")
            li_html = li_html.replace(tbl_html, "")

        # br → \n 치환 후 텍스트 추출
        li_html = re.sub(r'<br\s*/?>', '\n', li_html, flags=re.IGNORECASE)
        li_text = re.sub(r'<[^>]+>', ' ', li_html)
        for line in [clean(l) for l in li_text.splitlines() if clean(l)]:
            lines.append(line)

        # li 안의 table: 헤더:값 / 형식
        if child_table:
            headers = []
            header_row = await child_table.query_selector("thead tr")
            if header_row:
                for cell in await header_row.query_selector_all("th, td"):
                    headers.append(clean(await cell.inner_text()))

            tbody = await child_table.query_selector("tbody")
            data_rows = await (tbody or child_table).query_selector_all("tr")
            for tr in data_rows:
                cells = [clean(await td.inner_text()) for td in await tr.query_selector_all("td")]
                if not any(cells):
                    continue
                parts = []
                for j, val in enumerate(cells):
                    if not val:
                        continue
                    header = headers[j] if j < len(headers) else ""
                    parts.append(f"{header}: {val}" if header else val)
                if parts:
                    lines.append(" / ".join(parts))

        # 자식 ul 재귀
        if child_ul:
            lines.extend(await parse_ul_lines(child_ul))

    return lines


async def crawl_detail_benefits(page, card_id: str) -> list:
    """
    팝업 내 상세혜택 수집
    benefit_group : 팝업 h1
    benefit_title : 토글(accodBtn) 텍스트
    benefit_content: 토글 안의 모든 내용 - 한 문장씩
    """
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    def make_row(benefit_group, benefit_title, summary, content, row_type="상세혜택"):
        return {
            "benefit_id":         "",
            "card_id":            card_id,
            "row_type":           row_type,
            "benefit_group":      benefit_group,
            "benefit_title":      benefit_title,
            "benefit_summary":    summary,
            "benefit_content":    content,
            "category":           "",
            "category_id":        "",
            "on_offline":         "",
            "region":             "",
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
            "updated_at":         now,
        }

    async def parse_bundle(bundle_el, benefit_group, benefit_title, row_type="상세혜택"):
        """
        card_bundle 파싱
        - box_title : benefit_summary (파싱용) + content에도 저장 (br 기준 줄 분리)
        - box_txt   : ul 있으면 parse_ul_lines, 없으면 get_text_lines
        - 직접 하위 ul
        - box_line 구조
        """
        bundle_rows = []

        # box_title: br 기준으로 줄 분리
        title_el = await bundle_el.query_selector(".box_title")
        summary  = clean(await title_el.inner_text()) if title_el else ""

        notice_kws = ["유의사항", "주의사항", "안내사항", "공통"]
        if any(kw in summary for kw in notice_kws):
            row_type = "유의사항"

        if title_el:
            for line in await get_text_lines(title_el):
                bundle_rows.append(make_row(benefit_group, benefit_title, summary, line, row_type))

        # box_txt
        txt_el = await bundle_el.query_selector(".box_txt")
        if txt_el:
            ul_el = await txt_el.query_selector("ul")
            if ul_el:
                for line in await parse_ul_lines(ul_el):
                    t = clean(line)
                    if t:
                        bundle_rows.append(make_row(benefit_group, benefit_title, summary, t, row_type))
            else:
                for line in await get_text_lines(txt_el):
                    bundle_rows.append(make_row(benefit_group, benefit_title, summary, line, row_type))

        # bundle 직접 하위 ul
        for ul in await bundle_el.query_selector_all(":scope > ul"):
            for line in await parse_ul_lines(ul):
                t = clean(line)
                if t:
                    bundle_rows.append(make_row(benefit_group, benefit_title, summary, t, row_type))

        # box_line 구조 (M포인트 교환 등)
        for box_line in await bundle_el.query_selector_all(".box_line"):
            line_tit = await box_line.query_selector(".line_tit")
            if not line_tit:
                continue
            for p in await line_tit.query_selector_all(":scope > p"):
                t = clean(await p.inner_text())
                if t:
                    bundle_rows.append(make_row(benefit_group, benefit_title, summary, t, row_type))
            for ul in await line_tit.query_selector_all(":scope > ul"):
                for line in await parse_ul_lines(ul):
                    t = clean(line)
                    if t:
                        bundle_rows.append(make_row(benefit_group, benefit_title, summary, t, row_type))

        # 아무것도 없으면 전체 텍스트 줄바꿈 단위
        if not bundle_rows:
            for line in await get_text_lines(bundle_el):
                bundle_rows.append(make_row(benefit_group, benefit_title, summary, line, row_type))

        return bundle_rows

    # 카드 이용 유의사항 팝업은 notices 전용 → benefit에서 제외
    NOTICE_ONLY_POPUP_IDS = {"popCardUse"}

    # 모든 팝업 순회
    for pop_el in await page.query_selector_all(".modal_pop"):
        pop_id = await pop_el.get_attribute("id") or ""
        if pop_id in NOTICE_ONLY_POPUP_IDS:
            continue

        h1_el = await pop_el.query_selector("h1")
        if not h1_el:
            continue
        benefit_group = clean(await h1_el.inner_text())

        box_el = await pop_el.query_selector(".box_content")
        if not box_el:
            continue

        # big_accod: 토글 단위
        # benefit_title = 토글 버튼 텍스트
        accods = await box_el.query_selector_all(".big_accod")
        for accod in accods:
            btn_el = await accod.query_selector(".accodBtn")
            benefit_title = clean(await btn_el.inner_text()) if btn_el else benefit_group

            notice_kws = ["유의사항", "안내", "기준", "주의"]
            row_type = "유의사항" if any(kw in benefit_title for kw in notice_kws) else "상세혜택"

            slide_el = await accod.query_selector(".accodSlide")
            if not slide_el:
                continue

            # card_bundle 순회
            for bundle in await slide_el.query_selector_all(".card_bundle"):
                rows.extend(await parse_bundle(bundle, benefit_group, benefit_title, row_type))

            # box_line 직접 순회 (M포인트 교환 등 card_bundle 없는 구조)
            for box_line in await slide_el.query_selector_all(":scope > .box_line"):
                line_tit = await box_line.query_selector(".line_tit")
                if not line_tit:
                    continue
                for p in await line_tit.query_selector_all(":scope > p"):
                    t = clean(await p.inner_text())
                    if t:
                        rows.append(make_row(benefit_group, benefit_title, "", t, row_type))
                for ul in await line_tit.query_selector_all(":scope > ul"):
                    for line in await parse_ul_lines(ul):
                        t = clean(line)
                        if t:
                            rows.append(make_row(benefit_group, benefit_title, "", t, row_type))

        # big_accod 없는 팝업 (popAffiService 등)
        if not accods:
            top_tit = await box_el.query_selector(".box_top_tit")
            benefit_title = clean(await top_tit.inner_text()) if top_tit else benefit_group
            for bundle in await box_el.query_selector_all(".card_bundle"):
                rows.extend(await parse_bundle(bundle, benefit_group, benefit_title))

        # infocontWrap: 혜택 유의사항
        # 구조: p.title(infocontWrap 제목=benefit_title) > list_item > box_title(대제목) + sub_item > cont(소제목) + ul(내용)
        info_wrap = await box_el.query_selector(".infocontWrap")
        if info_wrap:
            # infocontWrap 상단 p.title → benefit_title (M포인트 사용 기준 / 혜택 제공 기준 등)
            info_title_el = await info_wrap.query_selector("p.title")
            info_title = clean(await info_title_el.inner_text()) if info_title_el else benefit_group

            for list_item in await info_wrap.query_selector_all(".list_item"):
                big_title_el = await list_item.query_selector(".box_title")
                big_title = clean(await big_title_el.inner_text()) if big_title_el else ""

                # big_title 자체도 content에 저장
                if big_title:
                    rows.append(make_row(benefit_group, info_title, big_title, big_title, "유의사항"))

                for sub_item in await list_item.query_selector_all(".sub_item"):
                    cont_el   = await sub_item.query_selector(".cont")
                    sub_title = clean(await cont_el.inner_text()) if cont_el else ""
                    item_summary = f"{big_title} - {sub_title}" if sub_title else big_title

                    # 소제목 자체도 content에 저장
                    if sub_title:
                        rows.append(make_row(benefit_group, info_title, item_summary, sub_title, "유의사항"))

                    # ul li 내용
                    for ul in await sub_item.query_selector_all(":scope > ul"):
                        for line in await parse_ul_lines(ul):
                            t = clean(line)
                            if t and len(t) > 8:
                                rows.append(make_row(benefit_group, info_title, item_summary, t, "유의사항"))



    print(f"  상세혜택 {len(rows)}행 수집")
    return rows


# =============================================
# 유의사항 수집 (card_notices.csv)
# =============================================

async def crawl_notices(page, card_id: str) -> list:
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    def make_row(notice_category, sub_category, content):
        return {
            "notice_id":       "",
            "card_id":         card_id,
            "notice_category": notice_category,
            "sub_category":    sub_category,
            "notice_content":  content,
            "updated_at":      now,
        }

    async def extract_lines(el) -> list:
        """
        요소 안의 텍스트를 한 문장씩 추출.
        - p/li 직접 텍스트: br 기준으로 분리
        - li 안에 하위 ul 있으면: 직접 텍스트와 하위 li를 각각 별도 행으로
        inner_text() 사용으로 &gt; → > 자동 변환
        """
        result = []
        seen   = set()

        async def add(text):
            t = clean(text)
            if t and len(t) > 8 and t not in seen:
                seen.add(t)
                result.append(t)

        async def split_by_br(node):
            """node의 직접 텍스트만 br 기준으로 분리 (하위 ul 내용 제외)"""
            # 하위 ul을 빈 문자열로 치환 후 inner_text 추출
            raw = await page.evaluate("""el => {
                const clone = el.cloneNode(true);
                clone.querySelectorAll('ul').forEach(u => u.remove());
                return clone.innerText;
            }""", node)
            for line in raw.splitlines():
                await add(line)

        # box_title (소제목 div) - p/ul보다 먼저, 순서대로
        for title in await el.query_selector_all(":scope > .box_title"):
            await add(await title.inner_text())

        # 최상위 p 태그
        for p in await el.query_selector_all(":scope > p"):
            await split_by_br(p)

        # 최상위 ul > li (직접 자식만)
        for ul in await el.query_selector_all(":scope > ul"):
            for li in await ul.query_selector_all(":scope > li"):
                # li 직접 텍스트 (br 분리, 하위 ul 제외)
                await split_by_br(li)
                # 하위 ul > li 각각
                for child_li in await li.query_selector_all("ul > li"):
                    t = clean(await child_li.inner_text())
                    await add(t)

        return result

    # 1. 카드 이용 유의사항: popCardUse
    # 구조: big_accod(토글=sub_category) > accodSlide > card_bundle(p/ul>li)
    pop_use = await page.query_selector("#popCardUse")
    if pop_use:
        for accod in await pop_use.query_selector_all(".big_accod"):
            btn_el  = await accod.query_selector(".accodBtn")
            sub_cat = clean(await btn_el.inner_text()) if btn_el else ""

            slide = await accod.query_selector(".accodSlide")
            if not slide:
                continue

            for bundle in await slide.query_selector_all(".card_bundle"):
                for line in await extract_lines(bundle):
                    rows.append(make_row("카드 이용 유의사항", sub_cat, line))

    # 2. 필수 안내사항: .useinfo (bul_list > li, 하위 dash_list 포함)
    useinfo = await page.query_selector(".useinfo")
    if useinfo:
        for ul in await useinfo.query_selector_all(".bul_list"):
            for li in await ul.query_selector_all(":scope > li"):
                # li 직접 텍스트 (br 분리, 하위 ul 제외)
                raw = await page.evaluate("""el => {
                    const clone = el.cloneNode(true);
                    clone.querySelectorAll('ul').forEach(u => u.remove());
                    return clone.innerText;
                }""", li)
                for line in raw.splitlines():
                    t = clean(line)
                    if t and len(t) > 8:
                        rows.append(make_row("필수 안내사항", "이용 안내", t))
                # 하위 dash_list li 각각
                for child_li in await li.query_selector_all("ul > li"):
                    t = clean(await child_li.inner_text())
                    if t and len(t) > 8:
                        rows.append(make_row("필수 안내사항", "이용 안내", t))

    print(f"  유의사항 {len(rows)}행 수집")
    return rows


# =============================================
# 이벤트 수집 (card_events.csv)
# =============================================

def classify_evt_type(title: str) -> str:
    """
    이벤트 제목 키워드로 event_type 분류
    캐시백 / 포인트 / 할인 / 서비스 / 기타
    """
    title_lower = title
    if any(kw in title_lower for kw in ["캐시백", "연회비"]):
        return "캐시백"
    if any(kw in title_lower for kw in ["포인트", "적립", "M포인트"]):
        return "포인트"
    if any(kw in title_lower for kw in ["할인", "DC", "discount"]):
        return "할인"
    if any(kw in title_lower for kw in ["서비스", "라운지", "보험", "혜택"]):
        return "서비스"
    return "기타"


def parse_event_dates(date_str: str) -> tuple:
    """
    '2026. 4. 1 ~ 2026. 4. 30' → ('2026-04-01', '2026-04-30')
    날짜 파싱 실패 시 원문 반환
    """
    parts = [p.strip() for p in date_str.split("~")]
    results = []
    for part in parts[:2]:
        # 숫자만 추출 후 날짜 조립
        nums = re.findall(r"\d+", part)
        if len(nums) >= 3:
            y, m, d = nums[0], nums[1].zfill(2), nums[2].zfill(2)
            results.append(f"{y}-{m}-{d}")
        else:
            results.append(part)
    start = results[0] if len(results) > 0 else ""
    end   = results[1] if len(results) > 1 else ""
    return start, end


async def crawl_events(page, card_info: dict) -> list:
    """
    카드 메인 페이지에서 이벤트 버튼 링크 수집 →
    각 이벤트 페이지 접속 → 섹션별 content 수집
    """
    now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    card_id  = card_info["card_id"]
    company  = card_info["company"]
    card_name = card_info["card_name"]
    rows     = []

    def make_row(event_code, title, link, start, end, evt_type, section, content):
        return {
            "card_id":           card_id,
            "company":           company,
            "card_name":         card_name,
            "origin_event_code": event_code,
            "event_title":       title,
            "event_link":        link,
            "start_date":        start,
            "end_date":          end,
            "event_type":        evt_type,
            "section":           section,
            "event_content":     content,
            "updated_at":        now,
        }

    # 1. 메인 페이지에서 이벤트 링크 수집
    # 패턴: href="/cpb/ev/CPBEV0101_06.hc?bnftWebEvntCd=XXXXX"
    event_links = []
    for a in await page.query_selector_all("a[href*='bnftWebEvntCd']"):
        href       = await a.get_attribute("href") or ""
        btn_text   = clean(await a.inner_text())
        m = re.search(r"bnftWebEvntCd=([A-Z0-9]+)", href)
        if not m:
            continue
        event_code = m.group(1)
        full_url   = f"https://www.hyundaicard.com{href}" if href.startswith("/") else href
        event_links.append((event_code, btn_text, full_url))

    print(f"  이벤트 링크 {len(event_links)}개 발견")

    # 2. 각 이벤트 페이지 순회
    for event_code, btn_text, event_url in event_links:
        print(f"    이벤트 접속: {event_code} / {event_url}")
        try:
            await page.goto(event_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(1500)
        except Exception as e:
            print(f"    접속 실패: {e}")
            continue

        # 이벤트 제목 / 기간
        title_el = await page.query_selector(".title_box h3")
        event_title = clean(await title_el.inner_text()) if title_el else btn_text
        event_title = re.sub(r"\s+", " ", event_title)  # br로 나뉜 줄 병합

        date_el  = await page.query_selector(".title_box p")
        start_date, end_date = ("", "")
        if date_el:
            start_date, end_date = parse_event_dates(clean(await date_el.inner_text()))

        evt_type = classify_evt_type(event_title)

        # 섹션별 content 수집 (list-con1 > div)
        list_con = await page.query_selector(".list-con1")
        if list_con:
            for section_div in await list_con.query_selector_all(":scope > div"):
                # 섹션 제목
                h_el = await section_div.query_selector("h3, h4")
                section_name = clean(await h_el.inner_text()) if h_el else ""

                # p 텍스트 (ev_icobox 밖에 있는 것만, SVG 포함 div 제외)
                for p in await section_div.query_selector_all(":scope > p"):
                    t = clean(await p.inner_text())
                    if t and len(t) > 4:
                        rows.append(make_row(
                            event_code, event_title, event_url,
                            start_date, end_date, evt_type, section_name, t
                        ))

                # ul > li (ev_icobox 밖 일반 ul, 직접 자식 li)
                for ul in await section_div.query_selector_all(":scope > ul"):
                    for li in await ul.query_selector_all(":scope > li"):
                        raw = await page.evaluate("""el => {
                            const clone = el.cloneNode(true);
                            clone.querySelectorAll('ul').forEach(u => u.remove());
                            return clone.innerText;
                        }""", li)
                        for line in raw.splitlines():
                            t = clean(line)
                            if t and len(t) > 4:
                                rows.append(make_row(
                                    event_code, event_title, event_url,
                                    start_date, end_date, evt_type, section_name, t
                                ))
                        for child_li in await li.query_selector_all("ul > li"):
                            t = clean(await child_li.inner_text())
                            if t and len(t) > 4:
                                rows.append(make_row(
                                    event_code, event_title, event_url,
                                    start_date, end_date, evt_type, section_name, t
                                ))

                # ev_icobox: STEP 구조
                # 구조: ul.ev_icolist > li > p.STEP번호 + p.설명
                # → "STEP1 : 현대카드 홈페이지 및 앱에서 카드 신청" 한 행으로
                icobox = await section_div.query_selector(".ev_icobox")
                if icobox:
                    for li in await icobox.query_selector_all("li"):
                        step_el = await li.query_selector("p.p1_b_ctr_1ln, p.p1_b_ctr")
                        desc_el = await li.query_selector("p.p2_m_ctr_2ln, p.p2_m_ctr")
                        if step_el and desc_el:
                            step = clean(await step_el.inner_text())
                            desc = clean(await desc_el.inner_text())
                            desc = re.sub(r"\s+", " ", desc)  # br로 나뉜 줄 병합
                            if step and desc:
                                rows.append(make_row(
                                    event_code, event_title, event_url,
                                    start_date, end_date, evt_type, section_name,
                                    f"{step} : {desc}"
                                ))

        # 확인해 주세요 섹션 (event_box_list)
        box_list = await page.query_selector(".event_box_list")
        if box_list:
            for section_div in await box_list.query_selector_all("div"):
                h_el = await section_div.query_selector("h3, h4")
                section_name = clean(await h_el.inner_text()) if h_el else "확인해 주세요"

                for ul in await section_div.query_selector_all("ul.bul_list01, ul.bul_list"):
                    for li in await ul.query_selector_all(":scope > li"):
                        raw = await page.evaluate("""el => {
                            const clone = el.cloneNode(true);
                            clone.querySelectorAll('ul').forEach(u => u.remove());
                            return clone.innerText;
                        }""", li)
                        for line in raw.splitlines():
                            t = clean(line)
                            if t and len(t) > 4:
                                rows.append(make_row(
                                    event_code, event_title, event_url,
                                    start_date, end_date, evt_type, section_name, t
                                ))
                        for child_li in await li.query_selector_all("ul > li"):
                            t = clean(await child_li.inner_text())
                            if t and len(t) > 4:
                                rows.append(make_row(
                                    event_code, event_title, event_url,
                                    start_date, end_date, evt_type, section_name, t
                                ))

    print(f"  이벤트 {len(rows)}행 수집")
    return rows


# =============================================
# 메인 실행
# =============================================

async def run_crawler(url: str) -> tuple:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=BROWSER_HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(user_agent=USER_AGENT)
        page    = await context.new_page()

        print(f"  접속 중... {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        print(f"  로딩 완료")

        card_info       = await crawl_card_info(page, url)
        main_benefits   = await crawl_main_benefits(page, card_info['card_id'])
        detail_benefits = await crawl_detail_benefits(page, card_info['card_id'])
        notices         = await crawl_notices(page, card_info['card_id'])
        events          = await crawl_events(page, card_info)

        await browser.close()

    return card_info, main_benefits + detail_benefits, notices, events