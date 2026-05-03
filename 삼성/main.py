"""
main.py - 삼성카드 크롤링 진입점
"""

import asyncio
import aiohttp

from config import CARD_LIST, CARD_COMPANY
from crawler import get_nuxt_data, log, line
from parser import parse_benefits, parse_fees, parse_events, parse_notices, parse_card_info
from saver import save_rows_to_csv
from crawler import get_nuxt_data, save_list_page_html, log, line


async def crawl_one(card_code: str, session: aiohttp.ClientSession):
    log(f"[{card_code}] 시작")

    result = await get_nuxt_data(card_code)
    log(f"[{card_code}] 기본정보 완료 / 출시일: {result['sell_start_dt'] or '-'}")

    nuxt_data = result["nuxt_data"]

    benefit_rows = await parse_benefits(card_code, nuxt_data, session)
    fee_rows     = await parse_fees(card_code, nuxt_data, session)
    log(f"[{card_code}] 혜택 {len(benefit_rows)}건 / 연회비 {len(fee_rows)}건")

    event_rows  = await parse_events(card_code, nuxt_data, session)
    log(f"[{card_code}] 이벤트 {len(event_rows)}건")

    notice_rows = await parse_notices(card_code, nuxt_data, session)
    log(f"[{card_code}] 공지 {len(notice_rows)}건")

    info_row = await parse_card_info(card_code, nuxt_data, session, benefit_rows)
    log(f"[{card_code}] 완료")

    return {
        "benefit_rows": benefit_rows + fee_rows,
        "event_rows":   event_rows,
        "notice_rows":  notice_rows,
        "info_row":     info_row,
    }

async def main():
    await save_list_page_html()
    log(f"삼성카드 크롤링 시작 - 총 {len(CARD_LIST)}개 카드")
    line()

    all_benefits = []
    all_events   = []
    all_notices  = []
    all_info     = []

    async with aiohttp.ClientSession(headers={
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }) as session:

        for idx, card_code in enumerate(CARD_LIST, 1):
            log(f"[{idx}/{len(CARD_LIST)}] {card_code} 크롤링 중...")
            try:
                result = await crawl_one(card_code, session)
                all_benefits.extend(result["benefit_rows"])
                all_events.extend(result["event_rows"])
                all_notices.extend(result["notice_rows"])
                all_info.append(result["info_row"])
            except Exception as e:
                log(f"[ERR] {card_code} 오류: {e}")

    save_rows_to_csv(all_benefits, "../csv/samsung_benefit.csv")
    save_rows_to_csv(all_events,   "../csv/samsung_event.csv")
    save_rows_to_csv(all_notices,  "../csv/samsung_notice.csv")
    save_rows_to_csv(all_info,     "../csv/samsung_info.csv")
    
    line()
    log(f"전체 크롤링 완료 - 성공 {len(all_info)} / 전체 {len(CARD_LIST)}")
    line()

if __name__ == "__main__":
    asyncio.run(main())
