"""
kb_collect_cards.py - KB국민카드 전체 카드 목록 수집 + 신규 카드 감지

신용/체크 카드 목록 페이지 탭 전체 순회 →
기존 kb_cards.json과 비교 → 신규 카드 반환 + JSON 업데이트

[단독 실행]
  python kb_collect_cards.py

[import 사용]
  from kb_collect_cards import collect_cards
  new_cards = await collect_cards()
"""

import asyncio
import json
import os
import re
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from playwright.async_api import async_playwright

BASE_URL   = "https://card.kbcard.com"
CARD_URLS  = [
    ("신용", f"{BASE_URL}/CRD/DVIEW/HCAMCXPRICAC0047"),
    ("체크", f"{BASE_URL}/CRD/DVIEW/HCAMCXPRICAC0056"),
]
CARDS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ouput", "kb_cards.json")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ─────────────────────────────────────────────
# 탭 순회 + 카드 수집
# ─────────────────────────────────────────────

async def _collect_from_page(page, card_type: str) -> dict:
    """한 페이지(신용/체크)의 탭 전체 순회 → card_id: dict"""
    results = {}

    await page.wait_for_timeout(3000)

    tabs = await page.query_selector_all("li a.btn.btn--tertiary.mw-auto")
    tab_names = [(await t.inner_text()).strip() for t in tabs]
    print(f"  [{card_type}] 탭 {len(tab_names)}개: {tab_names}")

    for tab_name in tab_names:
        # 탭 클릭
        for t in await page.query_selector_all("li a.btn.btn--tertiary.mw-auto"):
            if (await t.inner_text()).strip() == tab_name:
                await t.click()
                await page.wait_for_timeout(1500)
                break

        cards = await page.query_selector_all(".linkDetail")
        for card in cards:
            onclick = await card.get_attribute("onclick") or ""
            m = re.search(r"goDetail\('(\d+)'", onclick)
            if not m:
                continue
            code = m.group(1)
            if code in results:
                continue
            text = (await card.inner_text()).strip().split("\n")[0]
            image_url = (
                f"https://img1.kbcard.com/ST/img/cxc/kbcard/upload/img/product/{code}_img.png"
            )
            link_url = f"{BASE_URL}/CRD/DVIEW/HCAMCXPRICAC0076?mainCC=a&cooperationcode={code}"
            results[code] = {
                "card_id":       code,
                "company":       "국민",
                "card_name":     text,
                "card_type":     card_type,
                "image_url":     image_url,
                "link_url":      link_url,
                "has_transport": False,
                "events":        [],
            }

    print(f"  [{card_type}] {len(results)}개 수집")
    return results


# ─────────────────────────────────────────────
# 메인 수집 함수
# ─────────────────────────────────────────────

async def collect_cards() -> list[dict]:
    """
    KB국민카드 전체 카드 목록 수집 + 신규 카드 감지.

    Returns:
        신규 카드 dict 리스트 (기존 JSON에 없는 것만)
    """
    existing = {}
    if os.path.exists(CARDS_JSON):
        with open(CARDS_JSON, encoding="utf-8") as f:
            for c in json.load(f):
                existing[c["card_id"]] = c

    print(f"  [기존 카드] {len(existing)}개")

    fetched = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()

        try:
            for card_type, url in CARD_URLS:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                cards = await _collect_from_page(page, card_type)
                fetched.update(cards)
        except Exception as e:
            print(f"  [오류] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    print(f"  [수집 완료] 총 {len(fetched)}개")

    new_cards = [c for cid, c in fetched.items() if cid not in existing]

    if new_cards:
        print(f"\n  [신규 카드 {len(new_cards)}개 감지]")
        for c in new_cards:
            print(f"    + {c['card_id']} | {c['card_name']} ({c['card_type']})")

        merged = list(existing.values()) + new_cards
        os.makedirs(os.path.dirname(CARDS_JSON), exist_ok=True)
        with open(CARDS_JSON, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"  [저장] {CARDS_JSON} -> {len(merged)}개")
    else:
        print("  [신규 카드 없음]")

    return new_cards


# ─────────────────────────────────────────────
# 단독 실행
# ─────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("KB국민카드 전체 카드 목록 수집 + 신규 감지")
    print("=" * 60)
    new_cards = await collect_cards()
    print()
    print("=" * 60)
    print(f"[완료] 신규 카드 {len(new_cards)}개")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
