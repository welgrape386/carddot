import asyncio
import json

from config import CARDS
from crawler import fetch_all_cards, fetch_event_page
from parser import parse_card_info, parse_benefits, parse_notices, parse_events
from saver import save_card_info, save_benefits, save_notices, save_events


async def main():
    print("=" * 55)
    print("  신한카드 크롤링 시작")
    print("=" * 55)

    results = await fetch_all_cards(CARDS)

    all_info, all_benefits, all_notices, all_events = [], [], [], []

    for r in results:
        card_name = r["카드명"]
        res = r.get("result")

        if res is None:
            print(f"\n❌ [{card_name}] 크롤링 실패 - 스킵")
            continue

        print(f"\n✅ [{card_name}] 파싱 시작")

        # 이벤트 상세 크롤링
        event_details = {}
        if res["event_links"]:
            print(f"  [이벤트 상세 크롤링] {len(res['event_links'])}건")
            for ev in res["event_links"]:
                ev_url = ev["url"]
                try:
                    detail = await fetch_event_page(ev_url)
                    event_details[ev_url] = detail
                    print(f"    → 제목: {detail['title']}")
                    print(f"    → 기간: {detail['period']}")
                except Exception as e:
                    print(f"    → 실패: {e}")
                    event_details[ev_url] = {}

        # 파싱
        all_info.append(parse_card_info(r, res))
        all_benefits.extend(parse_benefits(r, res))
        all_notices.extend(parse_notices(r, res))
        all_events.extend(parse_events(r, res, event_details))

        print(f"  혜택목록: {len(all_benefits)}행 | 유의사항: {len(all_notices)}행 | 이벤트: {len(all_events)}건")

    # 전체 합본 CSV 저장
    print(f"\n{'=' * 55}")
    print("  전체 합본 CSV 저장 중...")

    if all_info:
        save_card_info(all_info, "../csv/shinhan_info.csv")
    if all_benefits:
        save_benefits(all_benefits, "../csv/shinhan_benefit.csv")
    if all_notices:
        save_notices(all_notices, "../csv/shinhan_notice.csv")
    if all_events:
        save_events(all_events, "../csv/shinhan_event.csv")

    print("\n✅ 전체 완료!")


if __name__ == "__main__":
    asyncio.run(main())