"""
samsung_collect_cards.py - 삼성카드 카드 목록 수집 + 신규 카드 감지

카드 상세 페이지의 window.__NUXT__.wcms.pdList 파싱 →
기존 samsung_cards.json과 비교 → 신규 카드 반환 + JSON 업데이트

[단독 실행]
  python samsung_collect_cards.py

[import 사용]
  from samsung_collect_cards import collect_cards
  new_cards = await collect_cards()
"""

import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

# 같은 폴더의 main.py (card_naea/예은/main.py 복사본)에서 import
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from main import get_card_list, goto_and_wait  # noqa: E402

SAMSUNG    = "https://www.samsungcard.com"
DETAIL_URL = f"{SAMSUNG}/home/card/cardinfo/PGHPPCCCardCardinfoDetails001"

CARDS_JSON = os.path.join(_DIR, "output", "samsung_cards.json")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def collect_cards() -> list[dict]:
    """
    삼성카드 카드 목록 수집 + 신규 카드 감지.

    Returns:
        신규 카드 dict 리스트 (기존 JSON에 없는 것만)
        [] → 신규 없음
    """
    existing = {}
    if os.path.exists(CARDS_JSON):
        with open(CARDS_JSON, encoding="utf-8") as f:
            for c in json.load(f):
                existing[c["card_id"]] = c

    fetched = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx  = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()

        try:
            raw_cards = await get_card_list(page)
            for c in raw_cards:
                cid = c["card_id"]
                fetched[cid] = {
                    "card_id":   cid,
                    "company":   "삼성",
                    "card_name": c.get("card_name", ""),
                    "card_type": "",
                    "image_url": "",
                    "link_url":  f"{DETAIL_URL}?code={cid}",
                }
        except Exception as e:
            print(f"  [오류] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    new_cards = [c for cid, c in fetched.items() if cid not in existing]

    # 신규 카드 이름 채우기 (상세 페이지 cardTitle)
    if new_cards:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx  = await browser.new_context(user_agent=USER_AGENT)
            page = await ctx.new_page()
            try:
                for c in new_cards:
                    try:
                        url = c["link_url"]
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(2000)
                        title = await page.evaluate(
                            "() => { try { return window.__NUXT__.data[0].wcms.detail.cardTitle || ''; } catch(e) { return ''; } }"
                        )
                        if title:
                            import re as _re
                            c["card_name"] = _re.sub(r"<[^>]+>", "", title).strip()
                    except Exception as e:
                        print(f"    [이름 조회 실패] {c['card_id']}: {e}")
            finally:
                await browser.close()

    if new_cards:
        print(f"\n  [신규 카드 {len(new_cards)}개 감지]")
        for c in new_cards:
            print(f"    + {c['card_id']} | {c['card_name']}")

        merged = list(existing.values()) + new_cards
        os.makedirs(os.path.dirname(CARDS_JSON), exist_ok=True)
        with open(CARDS_JSON, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"  [저장] {CARDS_JSON} -> {len(merged)}개")
    else:
        print("  [신규 카드 없음]")

    return new_cards


async def main():
    print("=" * 60)
    print("삼성카드 카드 목록 수집 + 신규 감지")
    print("=" * 60)
    new_cards = await collect_cards()
    print()
    print("=" * 60)
    print(f"[완료] 신규 카드 {len(new_cards)}개")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
