"""
kb_collect_event_urls.py - KB국민카드 이벤트 목록 수집

https://card.kbcard.com/BON/DVIEW/HBBMCXCRVNEC0001
전체 이벤트 목록 → 더보기 반복 → kb_events.json 저장

[출력]
  kb_events.json

[단독 실행]
  python kb_collect_event_urls.py

[import 사용]
  from kb_collect_event_urls import collect_event_urls
  events = await collect_event_urls()
"""

import asyncio
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

EVENT_LIST_URL   = "https://card.kbcard.com/BON/DVIEW/HBBMCXCRVNEC0001"
EVENT_DETAIL_BASE = "https://card.kbcard.com/BON/DVIEW/HBBMCXCRVNEC0001?mainCC=a&eventNum={event_num}"
EVENTS_JSON      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb_events.json")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 카테고리 필터 코드 → event_type 매핑
# KB: 캐시백/포인트/할인/서비스/기타
CATEGORIES = [
    ("캐시백", "cashback"),
    ("포인트", "point"),
    ("할인",   "discount"),
    ("서비스", "service"),
    ("기타",   "etc"),
]

DEFAULT_TAG = "기타"


def _parse_event_list(html: str) -> dict:
    """이벤트 목록 HTML 파싱 → {event_num: {...}} 반환"""
    soup = BeautifulSoup(html, "html.parser")
    results = {}

    for a in soup.find_all("a", href=re.compile(r"goDetail")):
        href = a.get("href", "")
        m = re.search(r"goDetail\(['\"](\d+)['\"]", href)
        if not m:
            continue
        event_num = m.group(1)

        # 제목 (.subject)
        title_el = a.find(class_="subject")
        title = re.sub(r'\s+', ' ', title_el.get_text(" ", strip=True)).strip() if title_el else ""

        # 기간 (.date)
        date_el = a.find(class_="date")
        period = date_el.get_text(strip=True) if date_el else ""

        # 태그 (.category em)
        tags = []
        cat_el = a.find(class_="category")
        if cat_el:
            for em in cat_el.find_all("em"):
                tag = em.get_text(strip=True)
                if tag:
                    tags.append(tag)

        event_url = EVENT_DETAIL_BASE.format(event_num=event_num)

        results[event_num] = {
            "event_num":   event_num,
            "event_url":   event_url,
            "event_title": title,
            "period":      period,
            "tags":        tags if tags else [DEFAULT_TAG],
        }

    return results




async def collect_event_urls() -> list:
    """
    KB국민카드 이벤트 목록 전체 수집.

    반환 형식:
      [
        {
          "event_num":   "1000776",
          "event_url":   "https://card.kbcard.com/BON/DVIEW/HBBMCXCRVNEC0001?mainCC=a&eventNum=1000776",
          "event_title": "이벤트 제목",
          "period":      "2026.01.01~2026.06.30",
          "tags":        ["캐시백"],
        },
        ...
      ]
    """
    all_events = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx  = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()

        try:
            print(f"  이벤트 목록 페이지 접속...")
            await page.goto(EVENT_LIST_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # 페이지 순환 (페이지 세트 넘기기 포함)
            current_page = 1
            while True:
                html = await page.content()
                all_events.update(_parse_event_list(html))
                print(f"  → 페이지 {current_page}: 누적 {len(all_events)}개")

                # 현재 페이지 세트에서 다음 페이지 버튼 찾기
                next_page = current_page + 1
                next_btn = page.locator(
                    f"a[href*='doSearchSpider'][href*='\"{next_page}\"'], "
                    f"button[onclick*='doSearchSpider'][onclick*='\"{next_page}\"']"
                ).first

                try:
                    is_visible = await next_btn.is_visible(timeout=3000)
                except Exception:
                    is_visible = False

                if not is_visible:
                    # 다음 페이지 세트로 넘기는 > 버튼 확인
                    next_set_btn = page.locator("button.page.next").first
                    try:
                        set_visible = await next_set_btn.is_visible(timeout=3000)
                    except Exception:
                        set_visible = False

                    if set_visible:
                        await next_set_btn.click()
                        await page.wait_for_timeout(2000)
                        current_page += 1
                        continue
                    else:
                        break  # 더 이상 페이지 없음

                await next_btn.click()
                await page.wait_for_timeout(2000)
                current_page += 1

            print(f"\n  → 전체 {len(all_events)}개 수집 완료")

        except Exception as e:
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    # 태그 없는 이벤트 기본값 설정
    result = []
    for event in all_events.values():
        if not event["tags"]:
            event["tags"] = [DEFAULT_TAG]
        result.append(event)

    print(f"  → 최종 {len(result)}개 (태그 매핑 완료)")
    return result


async def main():
    print("=" * 60)
    print("KB국민카드 이벤트 목록 수집")
    print("=" * 60)

    events = await collect_event_urls()

    with open(EVENTS_JSON, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"\n[완료] {EVENTS_JSON} 저장 완료 ({len(events)}개)")

    print("\n[샘플 3개]")
    for e in events[:3]:
        print(f"  {e['event_num']} | {e['event_title'][:30]} | {e['period']} | {e['tags']}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
