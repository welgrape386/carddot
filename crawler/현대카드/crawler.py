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
# card_info 수집
# =============================================

async def crawl_card_info(page, url: str) -> dict:
    card_id = extract_card_id(url)
    company = extract_company(url)

    # 카드명
    el = await page.query_selector("h2.h0_eb_size55")
    card_name = clean(await el.inner_text()) if el else card_id

    # card_type
    all_text = await page.inner_text("body")
    card_type = "체크" if "체크카드" in all_text else "신용"

    # 네트워크 / 본인 연회비 (#viewYearPay)
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

    # annual_fee_notes: 연회비 팝업에서 금액 포함 텍스트만 추출
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

    # 후불교통
    has_transport = "후불교통" in all_text

    # 전월실적 최솟값
    perf_vals = sorted(set(
        int(x) * 10000
        for x in re.findall(r"전월\s*이용\s*금액\s*(\d+)만원", all_text)
        if 1 <= int(x) * 10000 <= 10_000_000
    ))
    min_performance = perf_vals[0] if perf_vals else 0

    # summary
    summary_parts = [
        clean(await el.inner_text())
        for el in await page.query_selector_all(".card_tit_wrap ul li")
    ]
    summary = " / ".join([s for s in summary_parts if s])

    # 카드 이미지 (우선순위: _h.png → _f.png → card_id 포함)
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

    # has_cashback
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

async def crawl_main_benefits(page, card_id: str) -> list:
    """
    row_type     : 주요혜택
    benefit_group: 팝업 h1 텍스트 (HTML에서 직접 읽기, 하드코딩 없음)
    benefit_title: cate_tit 텍스트 (HTML에서 직접 읽기)
    benefit_content: em / p / sub_txt 텍스트 (행 단위)
    """
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    # JS로 box_card_type 전체 순회
    # cate_tit가 item_wrap 안/밖에 혼재하므로 JS에서 순서대로 추적
    # benefit_group: item의 .link href → popup.open('ID') → 해당 팝업 h1 텍스트
    all_items = await page.evaluate(r"""() => {
        const SKIP = new Set(['메탈 플레이트']);
        const results = [];

        document.querySelectorAll('#cms_area .box_card_type').forEach(box => {
            let currentCate = '';

            function traverse(parent) {
                for (const child of parent.children) {
                    if (child.classList.contains('cate_tit')) {
                        const p = child.querySelector('p');
                        currentCate = p ? p.innerText.trim() : child.innerText.trim();

                    } else if (child.classList.contains('item_wrap')) {
                        for (const inner of child.children) {
                            if (inner.classList.contains('cate_tit')) {
                                const p = inner.querySelector('p');
                                currentCate = p ? p.innerText.trim() : inner.innerText.trim();

                            } else if (inner.classList.contains('item')) {
                                if (SKIP.has(currentCate)) continue;

                                // benefit_group: 팝업 h1 텍스트
                                let popupGroup = '';
                                const link = inner.querySelector('.link');
                                if (link) {
                                    const href = link.getAttribute('href') || '';
                                    const m = href.match(/popup\.open\('([^']+)'/);
                                    if (m) {
                                        const popEl = document.getElementById(m[1]);
                                        const h1 = popEl ? popEl.querySelector('h1') : null;
                                        popupGroup = h1 ? h1.innerText.trim() : '';
                                    }
                                }

                                const em  = inner.querySelector('.item_tit em');
                                const p   = inner.querySelector('.item_tit p');
                                const sub = inner.querySelector('.sub_txt');

                                results.push({
                                    benefit_group: popupGroup,
                                    benefit_title: currentCate,
                                    em_text:  em  ? em.innerText.trim()  : '',
                                    p_text:   p   ? p.innerText.trim()   : '',
                                    sub_text: sub ? sub.innerText.trim() : '',
                                });
                            }
                        }
                    }
                }
            }
            traverse(box);
        });

        return results;
    }""")

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

    for item in all_items:
        bg = item['benefit_group']
        bt = item['benefit_title']
        if item['em_text']:
            rows.append(make_row(bg, bt, clean(item['em_text'])))
        if item['p_text']:
            rows.append(make_row(bg, bt, clean(item['p_text'])))
        if item['sub_text']:
            rows.append(make_row(bg, bt, clean(item['sub_text'])))

    print(f"  주요혜택 {len(rows)}행 수집")
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

        card_info     = await crawl_card_info(page, url)
        main_benefits = await crawl_main_benefits(page, card_info['card_id'])

        await browser.close()

    return card_info, main_benefits