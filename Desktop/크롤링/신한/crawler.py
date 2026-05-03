"""
crawler.py - 신한카드 페이지 크롤링 (Playwright 기반)
"""

import asyncio
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from config import USER_AGENT, BROWSER_HEADLESS

_api_cache = {}


async def _intercept_response(response):
    url = response.url
    try:
        if "cardinfo_data.json" in url:
            body = await response.json()
            _api_cache["cardinfo_data"] = body
            print(f"  [API 캡처] cardinfo_data.json ({len(str(body))} chars)")
        elif "MOBFM004R25.ajax" in url:
            try:
                body = await response.json()
            except Exception:
                body = await response.text()
            _api_cache["annual_fee_ajax"] = body
            print(f"  [API 캡처] MOBFM004R25.ajax")
        elif "eventBanner.json" in url:
            body = await response.json()
            _api_cache["event_banner"] = body
            print(f"  [API 캡처] eventBanner.json")
        elif "cardLinkList.json" in url:
            body = await response.json()
            _api_cache["card_link_list"] = body
            print(f"  [API 캡처] cardLinkList.json")
    except Exception:
        pass


async def fetch_card_page(url: str) -> dict:
    """카드 상세 페이지 크롤링"""
    _api_cache.clear()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=BROWSER_HEADLESS)
        context = await browser.new_context(user_agent=USER_AGENT)
        page    = await context.new_page()
        page.on("response", _intercept_response)

        print(f"  [크롤링] {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        # 연회비 팝업 클릭
        annual_fee_html = ""
        try:
            btn = await page.query_selector("button.btn-pop")
            if btn:
                await btn.click()
                await asyncio.sleep(2)
                annual_fee_html = await page.content()
                print(f"  [연회비 팝업 HTML] {len(annual_fee_html)} chars")
        except Exception as e:
            print(f"  [경고] 연회비 팝업 클릭 실패: {e}")

        # 연회비 텍스트
        annual_fee_text = ""
        try:
            for sel in [".annual-fee", ".fee-area", "[class*='annualFee']", "[class*='fee']"]:
                el = await page.query_selector(sel)
                if el:
                    annual_fee_text = await el.inner_text()
                    if annual_fee_text.strip():
                        print(f"  [연회비] {annual_fee_text[:60]}")
                        break
            if not annual_fee_text.strip():
                body_text = await page.inner_text("body")
                m = re.search(r"연회비[^\n]{0,150}", body_text)
                if m:
                    annual_fee_text = m.group(0)
        except Exception as e:
            print(f"  [경고] 연회비 추출 실패: {e}")

        # 연회비 팝업 강제 닫기
        try:
            await page.evaluate("""
                () => {
                    const pop = document.querySelector('#popAnnualFee');
                    if (pop) pop.style.display = 'none';
                }
            """)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"  [경고] 연회비 팝업 닫기 실패: {e}")

        # 탭 클릭 → 슬라이드 매핑 수집 (정적 HTML 순서로 처리)

        # 이벤트 링크 수집
        event_links = []
        try:
            html_content = await page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            for a in soup.find_all("a", onclick=re.compile(r"goEventLink")):
                onclick = a.get("onclick", "")
                url_m   = re.search(r"goEventLink\(\s*'([^']+)'", onclick)
                if not url_m:
                    continue
                path     = url_m.group(1)
                full_url = path if path.startswith("http") else f"https://www.shinhancard.com{path}"
                tit_el   = a.find("strong", class_="tit")
                title    = tit_el.get_text(strip=True) if tit_el else ""
                sub_el   = a.find("em", class_="txt")
                sub_txt  = sub_el.get_text(strip=True) if sub_el else ""
                if title:
                    event_links.append({"text": title, "sub": sub_txt, "url": full_url})
        except Exception as e:
            print(f"  [경고] 이벤트 링크 수집 실패: {e}")

        html = await page.content()
        await browser.close()

    return {
        "html":            html,
        "annual_fee_text": annual_fee_text,
        "annual_fee_html": annual_fee_html,
        "api_data":        dict(_api_cache),
        "event_links":     event_links,
        "url":             url,
    }


async def fetch_event_page(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=BROWSER_HEADLESS)
        page    = await (await browser.new_context(user_agent=USER_AGENT)).new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(1)
        html = await page.content()
        await browser.close()

    with open("event_debug.html", "w", encoding="utf-8") as f:
        f.write(html)

    soup  = BeautifulSoup(html, "html.parser")
    clean = lambda el: re.sub(r"\s+", " ", el.get_text()).strip()

    # 제목
    tit_el = soup.find("div", class_="e-tit1")
    title  = clean(tit_el) if tit_el else ""

    # 기간
    period = ""
    if d := soup.find("div", attrs={"data-date1": True}):
        d1, d2 = d.get("data-date1", ""), d.get("data-date2", "")
        period = f"{d1} ~ {d2}" if d2 else d1
    elif d := soup.find("div", class_="e-date1"):
        period = clean(d)
    elif d := soup.find("div", id="endEventDate"):
        period = d.get_text(strip=True)

    # 유의사항 먼저 추출 + 복사 (decompose로 파괴되므로)
    notice_el = soup.find("div", class_="s-notice-all")
    notice_el_copy = BeautifulSoup(str(notice_el), "html.parser") if notice_el else None

    # 섹션별 상세내용
    sections   = []
    content_el = soup.find("div", id="eventContents")
    if content_el:
        for tag in content_el.find_all(["style", "script"]):
            tag.decompose()
        for cls in ["s-evtShare_btn", "btn-wrap02", "s-notice-all"]:
            for tag in content_el.find_all("div", class_=cls):
                tag.decompose()

        cur_sec, cur_lines = "이벤트내용", []
        for el in content_el.descendants:
            if not hasattr(el, "get"):
                continue
            cls = " ".join(el.get("class", []))
            if any(c in cls for c in ["s-tit0", "s-tit1"]):
                if cur_lines:
                    sections.append({"section": cur_sec, "lines": cur_lines})
                cur_sec, cur_lines = clean(el), []
            elif el.name == "li" and not el.find_parent("li"):
                if (txt := clean(el)) and len(txt) > 2:
                    cur_lines.append(txt)
            elif "s-txt1" in cls and el.name in ["div", "p"]:
                if (txt := clean(el)) and len(txt) > 2:
                    cur_lines.append(txt)
        if cur_lines:
            sections.append({"section": cur_sec, "lines": cur_lines})

    # 유의사항 파싱 (위에서 미리 추출한 notice_el 사용)
    if notice_el_copy:
        dt  = notice_el_copy.find("dt")
        sec = clean(dt) if dt else "유의사항"
        dd  = notice_el_copy.find("dd")
        lines = []
        # ✅ 수정 코드
        if dd:
            for li in dd.find_all("li"):
                is_nested = bool(li.find_parent("li"))
                if is_nested:
                    txt = clean(li)
                    if txt and len(txt) > 2:
                        lines.append(txt.lstrip("- ").strip())
                else:
                    # 하위 ul 제거 후 부모 텍스트만 추출
                    li_copy = BeautifulSoup(str(li), "html.parser")
                    for sub_ul in li_copy.find_all("ul"):
                        sub_ul.decompose()
                    parent_txt = re.sub(r"\s+", " ", li_copy.get_text()).strip()
                    if parent_txt and len(parent_txt) > 2:
                        lines.append(parent_txt)

            for p in dd.find_all("p", class_="s-para"):
                if txt := clean(p):
                    lines.append(txt)

        if lines:  
            sections.append({"section": sec, "lines": lines})

    return {"title": title, "period": period, "sections": sections}


async def fetch_all_cards(cards: list) -> list:
    results = []
    for card in cards:
        print(f"\n{'='*55}")
        print(f"카드명  : {card['카드명']}")
        print(f"URL     : {card['url']}")
        try:
            result = await fetch_card_page(card["url"])
            results.append({**card, "result": result})
            print(f"  → HTML 길이      : {len(result['html']):,} chars")
            print(f"  → 연회비 텍스트  : {result['annual_fee_text'][:60] if result['annual_fee_text'] else '(없음)'}")
            print(f"  → API 캡처 키    : {list(result['api_data'].keys())}")
            print(f"  → 이벤트 링크 수 : {len(result['event_links'])}")
        except Exception as e:
            print(f"  [오류] {card['카드명']}: {e}")
            results.append({**card, "result": None})
    return results


if __name__ == "__main__":
    from config import CARDS

    async def main():
        results = await fetch_all_cards(CARDS)

        test_event_url = "https://www.shinhancard.com/pconts/html/benefit/event/1238076_2239.html"
        print(f"\n{'='*55}")
        print(f"[이벤트 페이지 테스트]")
        ev = await fetch_event_page(test_event_url)
        print(f"  제목    : {ev['title']}")
        print(f"  기간    : {ev['period']}")
        print(f"  섹션 수 : {len(ev['sections'])}")
        for s in ev["sections"]:
            print(f"  [{s['section']}] {len(s['lines'])}줄")

    asyncio.run(main())