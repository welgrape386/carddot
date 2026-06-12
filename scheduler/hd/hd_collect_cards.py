"""
hd_collect_cards.py - 현대카드 카드 목록 수집 + 신규 카드 감지

신용카드 / 체크카드 목록 페이지 크롤링 →
기존 hd_cards.json과 비교 → 신규 카드 반환 + JSON 업데이트

[단독 실행]
  python hd_collect_cards.py

[import 사용]
  from hd_collect_cards import collect_cards
  new_cards = await collect_cards()  # 신규 카드 리스트 반환
"""

import asyncio
import json
import os
import re

from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

BASE_URL     = "https://www.hyundaicard.com"
CREDIT_URL   = f"{BASE_URL}/cpc/ma/CPCMA0101_01.hc"
CHECK_URL    = f"{BASE_URL}/cpc/cr/CPCCR0621_11.hc?cardflag=C"
CARDS_JSON   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hd_ouput", "hd_cards.json")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ─────────────────────────────────────────────
# HTML 파싱
# ─────────────────────────────────────────────

def _parse_card_list(html: str, card_type: str) -> list[dict]:
    """카드 목록 HTML → 카드 dict 리스트"""
    soup = BeautifulSoup(html, "html.parser")
    cards = []

    for a in soup.find_all("a"):
        onclick = a.get("onclick", "")
        m = re.search(r"goCardDetail\('([A-Z0-9]+)'\)", onclick)
        if not m:
            continue
        card_id = m.group(1)

        # 카드명 후보 클래스 순서대로 시도
        card_name = ""
        for cls in ("h4_b_lt", "tit", "card_tit", "name", "card_name", "title", "card_title"):
            el = a.find("span", class_=cls) or a.find(["h3", "h4", "strong", "p"], class_=cls)
            if el:
                txt = el.get_text(strip=True)
                if txt and "연회비" not in txt and len(txt) > 1:
                    card_name = txt
                    break

        # 이미지 먼저 찾기 (alt에 카드명 있을 수 있음)
        img = a.find("img")
        image_url = ""
        if img:
            src = img.get("src", "") or img.get("data-src", "")
            image_url = src if src.startswith("http") else BASE_URL + src
            # alt에서 카드명 추출 시도
            if not card_name:
                alt = img.get("alt", "").strip()
                if alt and "연회비" not in alt and len(alt) > 1:
                    card_name = alt

        # fallback: 연회비/금액 텍스트 제외하고 첫 번째 span/strong
        if not card_name:
            for el in a.find_all(["span", "strong", "h3", "h4", "p"]):
                txt = el.get_text(strip=True)
                # 연회비, 금액(원), 카드사 브랜드만 있는 경우 제외
                if (txt and "연회비" not in txt and len(txt) > 1
                        and not re.match(r'^(Visa|Amex|Master|국내전용|\d|,|원)+$', txt)):
                    card_name = txt
                    break

        # 상세 URL
        card_url = f"{BASE_URL}/cpc/cr/CPCCR0201_01.hc?cardWcd={card_id}"

        if card_id and card_name:
            cards.append({
                "card_id":   card_id,
                "card_name": card_name,
                "card_type": card_type,
                "url":       card_url,
                "image_url": image_url,
                "has_transport": False,
                "events":    [],
            })

    # card_id 중복 제거 (순서 유지)
    seen = set()
    result = []
    for c in cards:
        if c["card_id"] not in seen:
            seen.add(c["card_id"])
            result.append(c)
    return result


# ─────────────────────────────────────────────
# 메인 수집 함수 (import용)
# ─────────────────────────────────────────────

async def collect_cards() -> list[dict]:
    """
    현대카드 카드 목록 수집 + 신규 카드 감지.

    Returns:
        신규 카드 dict 리스트 (기존 JSON에 없는 것만)
        [] → 신규 없음
    """
    # 기존 JSON 로드
    existing = {}
    if os.path.exists(CARDS_JSON):
        with open(CARDS_JSON, encoding="utf-8") as f:
            for c in json.load(f):
                existing[c["card_id"]] = c

    fetched = {}  # card_id → dict

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx  = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()
        await Stealth().apply_stealth_async(page)

        try:
            for url, card_type in [
                (CREDIT_URL, "신용"),
                (CHECK_URL,  "체크"),
            ]:
                print(f"  [{card_type}] {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                html = await page.content()

                cards = _parse_card_list(html, card_type)
                print(f"  -> {len(cards)}개 파싱")
                for c in cards:
                    fetched[c["card_id"]] = c

        except Exception as e:
            print(f"  [오류] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    # 신규 카드 추출 (기존에 없는 card_id)
    new_cards = [c for cid, c in fetched.items() if cid not in existing]

    # 기존 카드 중 카드명이 잘못된 것 수정 (이름에 "연회비" 포함된 경우)
    fixed = []
    needs_detail = []  # fetched에 없는 "연회비" 카드 → 상세 페이지 직접 방문
    for cid, card in existing.items():
        if "연회비" in card.get("card_name", ""):
            if cid in fetched and fetched[cid]["card_name"] and "연회비" not in fetched[cid]["card_name"]:
                old_name = card["card_name"]
                card["card_name"] = fetched[cid]["card_name"]
                fixed.append(f"{cid}: '{old_name}' → '{card['card_name']}'")
            else:
                needs_detail.append(card)

    # fetched에 없는 "연회비" 카드: 상세 페이지에서 직접 파싱
    if needs_detail:
        print(f"\n  [상세 페이지 이름 재조회] {len(needs_detail)}개")
        async with async_playwright() as p2:
            browser2 = await p2.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx2 = await browser2.new_context(user_agent=USER_AGENT)
            page2 = await ctx2.new_page()
            try:
                for card in needs_detail:
                    try:
                        await page2.goto(card["url"], wait_until="domcontentloaded", timeout=30000)
                        await page2.wait_for_timeout(2000)
                        html2 = await page2.content()
                        soup2 = BeautifulSoup(html2, "html.parser")
                        name = ""
                        for cls in ("h4_b_lt", "tit", "card_tit", "name", "card_name", "title"):
                            el = soup2.find("span", class_=cls) or soup2.find(["h3","h4","strong"], class_=cls)
                            if el:
                                txt = el.get_text(strip=True)
                                if txt and "연회비" not in txt and len(txt) > 1:
                                    name = txt
                                    break
                        if name:
                            old = card["card_name"]
                            card["card_name"] = name
                            fixed.append(f"{card['card_id']}: '{old}' → '{name}'")
                            print(f"    * {card['card_id']}: {name}")
                        else:
                            print(f"    ! {card['card_id']}: 이름 조회 실패")
                    except Exception as e:
                        print(f"    ! {card['card_id']}: {e}")
            finally:
                await browser2.close()

    if fixed:
        print(f"\n  [카드명 수정 {len(fixed)}개]")
        for f in fixed:
            print(f"    * {f}")

    if new_cards:
        print(f"\n  [신규 카드 {len(new_cards)}개 감지]")
        for c in new_cards:
            print(f"    + {c['card_id']} | {c['card_name']} ({c['card_type']})")

    if new_cards or fixed:
        # JSON 업데이트 (기존 + 신규)
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
    print("현대카드 카드 목록 수집 + 신규 감지")
    print("=" * 60)
    new_cards = await collect_cards()
    print()
    print("=" * 60)
    print(f"[완료] 신규 카드 {len(new_cards)}개")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
