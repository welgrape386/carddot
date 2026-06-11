"""
hd_collect_event_urls.py - 현대카드 이벤트 목록 수집

https://www.hyundaicard.com/cpb/ev/CPBEV0101_01.hc
카테고리별 필터 클릭 → "더 보기" 반복 → 전체 이벤트 수집

[출력]
  hd_events.json

[단독 실행]
  python hd_collect_event_urls.py

[import 사용]
  from hd_collect_event_urls import collect_event_urls
  events = await collect_event_urls()
"""

import asyncio
import json
import os
import re

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

BASE_URL       = "https://www.hyundaicard.com"
EVENT_LIST_URL = f"{BASE_URL}/cpb/ev/CPBEV0101_01.hc"
EVENT_DETAIL_BASE = f"{BASE_URL}/cpb/ev/CPBEV0101_06.hc?bnftWebEvntCd={{event_num}}"
EVENTS_JSON    = "hd_events.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 현대카드 필터 코드 → 이벤트 타입 매핑
# 현대: 캐시백(01) / 무이자(02) / 할인(03) / M포인트(04) / 기타(05)
# 우리: 캐시백 / 할인 / 포인트 / 서비스 / 기타
CATEGORIES = [
    ("캐시백", "01", "캐시백"),   # 현대 캐시백  → 캐시백
    ("할인",   "02", "무이자"),   # 현대 무이자  → 할인
    ("할인",   "03", "할인"),     # 현대 할인    → 할인
    ("포인트", "04", "M포인트"),  # 현대 M포인트 → 포인트
    ("기타",   "05", "기타"),     # 현대 기타    → 기타
]

# 태그 미분류 이벤트 기본값
DEFAULT_TAG = "기타"


# ─────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────

def _normalize_period(raw: str) -> str:
    """
    '2026. 6. 5 ~ 2026. 7. 23'  →  '2026.06.05~2026.07.23'
    """
    parts = re.findall(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', raw)
    if len(parts) == 2:
        s = f"{parts[0][0]}.{int(parts[0][1]):02d}.{int(parts[0][2]):02d}"
        e = f"{parts[1][0]}.{int(parts[1][1]):02d}.{int(parts[1][2]):02d}"
        return f"{s}~{e}"
    return raw.strip()


def _parse_event_list(html: str) -> dict:
    """
    #event_list1 파싱 → {event_num: {event_num, event_url, event_title, period}}
    """
    soup = BeautifulSoup(html, "html.parser")
    results = {}

    for li in soup.select("#event_list1 li"):
        a = li.find("a")
        if not a:
            continue

        href = a.get("href", "")
        m = re.search(r'bnftWebEvntCd=([^&]+)', href)
        if not m:
            continue
        event_num = m.group(1)

        # 제목 (<br> → 공백)
        title_span = a.find("span", class_="txt_title")
        if title_span:
            # <br> 태그를 공백으로 치환 후 텍스트 추출
            for br in title_span.find_all("br"):
                br.replace_with(" ")
            title = title_span.get_text(" ", strip=True)
            title = re.sub(r'\s+', ' ', title).strip()
        else:
            title = ""

        # 기간
        date_span = a.find("span", class_="txt_date")
        period_raw = date_span.get_text(strip=True) if date_span else ""
        period = _normalize_period(period_raw)

        # 상세 URL
        event_url = EVENT_DETAIL_BASE.format(event_num=event_num)

        results[event_num] = {
            "event_num":   event_num,
            "event_url":   event_url,
            "event_title": title,
            "period":      period,
        }

    return results


# ─────────────────────────────────────────────
# 카테고리별 수집
# ─────────────────────────────────────────────

async def _collect_category(page, cat_code: str) -> dict:
    """
    카테고리 필터 클릭 → 더 보기 끝까지 → {event_num: ...} 반환
    """
    btn = page.locator(f'.event_detail_list a[data-code="{cat_code}"]')
    await btn.click()
    await page.wait_for_timeout(2000)

    all_events = {}
    while True:
        html = await page.content()
        events = _parse_event_list(html)
        all_events.update(events)

        more_div = page.locator("#moreDiv")
        if not await more_div.is_visible():
            break

        await more_div.locator("a").click()
        await page.wait_for_timeout(2000)

    return all_events


# ─────────────────────────────────────────────
# 메인 수집 함수 (import용)
# ─────────────────────────────────────────────

async def collect_event_urls() -> list:
    """
    현대카드 이벤트 목록 전체 수집 + 카테고리별 태그 매핑.

    반환 형식:
      [
        {
          "event_num":   "UUI988",
          "event_url":   "https://www.hyundaicard.com/cpb/ev/CPBEV0101_06.hc?bnftWebEvntCd=UUI988",
          "event_title": "국내 제휴 호텔 6~7월 이벤트 혜택 안내",
          "period":      "2026.06.05~2026.07.23",
          "tags":        ["캐시백"],
        },
        ...
      ]
    """
    tag_map   = {}  # event_num → [태그, ...]
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

            # ── 전체(06): 모든 이벤트 기본 정보 수집 ─────────────────
            print(f"\n  [전체] 이벤트 수집 중...")
            all_btn = page.locator('.event_detail_list a[data-code="06"]')
            await all_btn.click()
            await page.wait_for_timeout(2000)

            while True:
                html = await page.content()
                events = _parse_event_list(html)
                all_events.update(events)

                more_div = page.locator("#moreDiv")
                if not await more_div.is_visible():
                    break
                await more_div.locator("a").click()
                await page.wait_for_timeout(2000)

            print(f"  → 전체 {len(all_events)}개 수집 완료")

            # ── 카테고리별 태그 매핑 ──────────────────────────────────
            for tag_name, cat_code, cat_label in CATEGORIES:
                print(f"\n  [{cat_label}({cat_code})] → '{tag_name}' 수집 중...")
                cat_events = await _collect_category(page, cat_code)
                for event_num in cat_events:
                    tag_map.setdefault(event_num, []).append(tag_name)
                print(f"  → {len(cat_events)}개")

        except Exception as e:
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    # 태그 병합 (카테고리 미분류 이벤트는 DEFAULT_TAG)
    result = []
    for event_num, event in all_events.items():
        tags = tag_map.get(event_num, [DEFAULT_TAG])
        # 중복 제거 (무이자+할인이 동시에 걸리는 경우 "할인" 하나로)
        event["tags"] = list(dict.fromkeys(tags))
        result.append(event)

    print(f"\n  → 최종 {len(result)}개 (태그 매핑 완료)")
    return result


# ─────────────────────────────────────────────
# 단독 실행
# ─────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("현대카드 이벤트 목록 수집")
    print("=" * 60)

    events = await collect_event_urls()

    with open(EVENTS_JSON, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"\n[완료] {EVENTS_JSON} 저장 완료 ({len(events)}개)")

    # 샘플 출력
    print("\n[샘플 3개]")
    for e in events[:3]:
        print(f"  {e['event_num']} | {e['event_title'][:30]} | {e['period']} | {e['tags']}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
