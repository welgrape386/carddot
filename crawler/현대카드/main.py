"""
main.py - 실행 진입점
카드 추가 시 CARD_URLS 리스트에 URL만 추가
현재 단계: card_info + card_benefit(원문) 수집
"""

import asyncio
import os
from crawler import run_crawler
from saver   import append_csv
from config  import OUTPUT_INFO, OUTPUT_BENEFIT, OUTPUT_NOTICE, OUTPUT_EVENTS, INFO_FIELDS, BENEFIT_FIELDS, NOTICE_FIELDS, EVENT_FIELDS

CARD_URLS = [
    "https://www.hyundaicard.com/cpc/cr/CPCCR0201_01.hc?cardWcd=ME4",
    # "https://www.hyundaicard.com/cpc/cr/CPCCR0201_01.hc?cardWcd=XPE4",
    # "https://www.hyundaicard.com/cpc/cr/CPCCR0201_01.hc?cardWcd=MZROE3",
]


def reset_output():
    for filepath in [OUTPUT_INFO, OUTPUT_BENEFIT, OUTPUT_NOTICE, OUTPUT_EVENTS]:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"  초기화: {filepath}")


async def main():
    print("=" * 50)
    print("현대카드 크롤러 시작")
    print(f"총 {len(CARD_URLS)}개 카드")
    print("=" * 50)

    print("\n[출력 파일 초기화]")
    reset_output()

    for url in CARD_URLS:
        print(f"\n[URL] {url}")
        try:
            card_info, benefits, notices, events = await run_crawler(url)

            # card_info 출력
            print(f"  card_id    : {card_info['card_id']}")
            print(f"  card_name  : {card_info['card_name']}")
            print(f"  network    : {card_info['network']}")
            print(f"  annual_fee : 해외 {card_info['annual_fee_for_basic']} / 국내 {card_info['annual_fee_dom_basic']}")
            print(f"  notes      : {card_info['annual_fee_notes']}")
            print(f"  summary    : {card_info['summary']}")

            # benefit 출력
            print(f"\n  [혜택 목록]")
            for b in benefits:
                print(f"    [{b['benefit_group']}] {b['benefit_title']} | {b['benefit_summary'][:50]}")

            # events 출력
            print(f"\n  [이벤트 목록]")
            seen_evt = set()
            for e in events:
                key = e['origin_event_code']
                if key not in seen_evt:
                    seen_evt.add(key)
                    print(f"    [{e['origin_event_code']}] {e['event_title']} | {e['start_date']} ~ {e['end_date']} | {e['event_type']}")

            # CSV 저장
            append_csv(OUTPUT_INFO,    [card_info], INFO_FIELDS)
            append_csv(OUTPUT_BENEFIT, benefits,    BENEFIT_FIELDS)
            append_csv(OUTPUT_NOTICE,  notices,     NOTICE_FIELDS)
            append_csv(OUTPUT_EVENTS,  events,      EVENT_FIELDS)

        except Exception as e:
            print(f"  오류 발생: {e}")
            raise

    print("\n" + "=" * 50)
    print("완료!")
    print("=" * 50)


asyncio.run(main())