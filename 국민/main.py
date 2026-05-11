"""
main.py - KB국민카드 크롤링 진입점

동작 순서:
1. Playwright 브라우저 1개를 공유해 카드 목록 순서대로 크롤링
2. 실패 카드 1회 재시도
3. 결과를 card_info / card_benefit / card_notices / card_events CSV로 저장

출력 파일:
    card_info.csv    카드 기본정보 (1카드 1행)
    card_benefit.csv 혜택 + 유의사항 + 연회비
    card_notices.csv 이용전확인사항
    card_events.csv  KB카드 미지원 (헤더만)
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

from config import CARD_LIST, CARD_COMPANY, CARD_PAGE_CODE
from crawler import get_page_html, log, line
from parser import (
    parse_card_info,
    discover_main_tabs,
    parse_benefit_tab,
    parse_notice_tabs_for_benefit,
    parse_fee_tabs,
    parse_notices,
)
from saver import save_results

from bs4 import BeautifulSoup


async def crawl_kb_card(browser, cooperation_code: str) -> dict:
    """카드 1개 크롤링 → 파싱 결과 dict 반환."""
    html, target_url = await get_page_html(browser, cooperation_code)
    soup = BeautifulSoup(html, "html.parser")
    crawled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 카드명 추출
    from parser import clean as _clean
    card_name_default = "KB국민카드"
    card_name = card_name_default
    h1 = soup.find("h1", class_="cardName")
    if h1:
        card_name = _clean(h1.get_text())
    elif soup.find("div", class_="cardTit"):
        inner_h1 = soup.find("div", class_="cardTit").find("h1")
        if inner_h1:
            card_name = _clean(inner_h1.get_text())

    if not soup.find("div", class_="cardTit") and not soup.find("ul", class_="cardKind"):
        raise ValueError(f"유효하지 않은 카드 페이지: {cooperation_code}")

    card_info = parse_card_info(soup, cooperation_code)
    all_tabs  = discover_main_tabs(soup)
    log(f"  감지된 탭: {[t['tab_name'] for t in all_tabs]}")

    tab_rows: list[dict] = []
    notice_tab_ids: list[str] = []
    fee_tab_ids: list[str] = []

    for tab in all_tabs:
        if tab["tab_type"] == "benefit":
            parsed = parse_benefit_tab(soup, tab["tab_id"], tab["tab_name"])
            tab_rows.extend(parsed)
            log(f"  [{tab['tab_name']}] {len(parsed)}행")
        elif tab["tab_type"] == "fee":
            fee_tab_ids.append(tab["tab_id"])
        elif tab["tab_type"] == "notice":
            notice_tab_ids.append(tab["tab_id"])

    benefit_notices = parse_notice_tabs_for_benefit(soup, notice_tab_ids)
    tab_rows += benefit_notices
    fee_summary, fee_detail = parse_fee_tabs(soup, fee_tab_ids)
    notice_rows = parse_notices(soup)

    # 연회비 탭 결과로 card_info 보완
    for key in ["국내전용_일반", "해외겸용_일반", "국내전용_프리미엄", "해외겸용_프리미엄"]:
        if fee_summary.get(key):
            card_info[key] = fee_summary[key]
    if fee_summary.get("결제네트워크브랜드") and not card_info.get("결제네트워크브랜드"):
        card_info["결제네트워크브랜드"] = fee_summary["결제네트워크브랜드"]
    if fee_summary.get("연회비_비고") and not card_info.get("연회비_비고"):
        card_info["연회비_비고"] = fee_summary["연회비_비고"]

    log(f"[3/3] 수집 완료")
    log(f"  혜택 탭: {len(tab_rows)}행 (확인사항 {len(benefit_notices)}행 포함)")
    log(f"  연회비: {len(fee_detail)}행 | notices: {len(notice_rows)}건")

    return {
        "card_code":   f"{CARD_PAGE_CODE}_{cooperation_code}",
        "target_url":  target_url,
        "card_name":   card_name,
        "card_info":   card_info,
        "tab_rows":    tab_rows,
        "fee_detail":  fee_detail,
        "notice_rows": notice_rows,
        "crawled_at":  crawled_at,
    }


async def main():
    total = len(CARD_LIST)
    line()
    log(f"KB국민카드 크롤링 시작 - 총 {total}개 카드")
    line()

    success, fail = 0, 0
    failed_codes: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for idx, coop_code in enumerate(CARD_LIST, 1):
            log(f"[{idx}/{total}] cooperationcode={coop_code} 크롤링 중...")
            try:
                data = await crawl_kb_card(browser, coop_code)
                save_results(data)
                success += 1
            except ValueError as e:
                log(f"  [SKIP] {e}")
            except Exception as e:
                log(f"  [ERR] {coop_code} 오류: {e}")
                import traceback; traceback.print_exc()
                failed_codes.append(coop_code)
                fail += 1

        # 실패 카드 1회 재시도
        if failed_codes:
            log(f"\n[재시도] {len(failed_codes)}개 재시도...")
            for coop_code in failed_codes:
                try:
                    data = await crawl_kb_card(browser, coop_code)
                    save_results(data)
                    success += 1
                    fail -= 1
                    log(f"  [OK] {coop_code} 재시도 성공")
                except Exception as e:
                    log(f"  [ERR] {coop_code} 재시도 실패: {e}")

        await browser.close()

    line()
    log(f"전체 크롤링 완료 — 성공: {success}, 실패: {fail}")
    line()


if __name__ == "__main__":
    asyncio.run(main())
