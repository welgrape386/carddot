"""
hd_detect_card_events.py - 현대카드 신규 이벤트 감지

흐름:
  1. hd_cards.json 로드 → 보유 카드 목록
  2. 각 카드 상세 페이지 방문 → bnftWebEvntCd 코드 추출
  3. hyundai_events.csv의 기존 (card_id, event_num) 쌍과 비교 → 신규 감지
  4. 신규 이벤트 상세 페이지 HTML 수집 + 메타 추출
  5. hd_crawl_events.parse_event_detail 호출 → CSV 행 생성
  6. hd_events.json 업데이트 (신규 이벤트 메타 추가)
  7. 신규 CSV 행 반환 (저장은 호출자가 처리)

[import 사용]
  from hd_detect_card_events import detect_and_crawl
  new_rows = await detect_and_crawl()
"""

import asyncio
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

BASE_URL  = "https://www.hyundaicard.com"
_BASE     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hd_ouput")

CARDS_JSON    = os.path.join(_BASE, "hd_cards.json")
EVENTS_CSV    = os.path.join(_BASE, "hyundai_events.csv")
EVENTS_JSON   = os.path.join(_BASE, "hd_events.json")
NEW_CSV_TMPL  = os.path.join(_BASE, "hd_new_events_{date}.csv")

EVENT_DETAIL_URL = f"{BASE_URL}/cpb/ev/CPBEV0101_06.hc?bnftWebEvntCd={{event_num}}"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ─────────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────────

def load_cards() -> list[dict]:
    if not os.path.exists(CARDS_JSON):
        print(f"  [오류] {CARDS_JSON} 없음")
        return []
    with open(CARDS_JSON, encoding="utf-8") as f:
        return json.load(f)


def load_known_events() -> set[tuple]:
    """기존 CSV에서 (card_id, origin_event_code) 쌍 로드."""
    if not os.path.exists(EVENTS_CSV):
        return set()
    with open(EVENTS_CSV, encoding="utf-8-sig") as f:
        return {(r["card_id"], r["origin_event_code"]) for r in csv.DictReader(f)}


def load_events_json() -> dict:
    """hd_events.json → {event_num: event_dict}"""
    if not os.path.exists(EVENTS_JSON):
        return {}
    with open(EVENTS_JSON, encoding="utf-8") as f:
        return {e["event_num"]: e for e in json.load(f)}


def save_events_json(event_map: dict):
    os.makedirs(_BASE, exist_ok=True)
    with open(EVENTS_JSON, "w", encoding="utf-8") as f:
        json.dump(list(event_map.values()), f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# 카드 상세 페이지 → 이벤트 코드 추출
# ─────────────────────────────────────────────

def extract_event_codes(html: str) -> list[str]:
    codes = re.findall(r"bnftWebEvntCd=([A-Z0-9]+)", html)
    seen, result = set(), []
    for c in codes:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


# ─────────────────────────────────────────────
# 이벤트 메타 추출 (제목 / 기간)
# ─────────────────────────────────────────────

def extract_event_meta(html: str, event_num: str) -> dict:
    soup  = BeautifulSoup(html, "html.parser")
    url   = EVENT_DETAIL_URL.format(event_num=event_num)

    title_el = (
        soup.find(class_="event_title")
        or soup.find(class_="tit_event")
        or soup.find("h2")
        or soup.find("h1")
    )
    title = title_el.get_text(" ", strip=True) if title_el else ""

    period_el = soup.find(class_=re.compile(r"(date|period|term)", re.I))
    period = period_el.get_text(strip=True) if period_el else ""

    return {
        "event_num":   event_num,
        "event_url":   url,
        "event_title": title,
        "period":      period,
        "tags":        ["기타"],
    }


# ─────────────────────────────────────────────
# 메인 감지 함수
# ─────────────────────────────────────────────

async def detect_and_crawl() -> list[dict]:
    """
    보유 카드 기반 신규 이벤트 감지 + 파싱.

    Returns:
        신규 이벤트 CSV 행 리스트 (event_id 미부여, 저장 전)
    """
    cards       = load_cards()
    known       = load_known_events()       # (card_id, event_num) 기존 조합
    events_json = load_events_json()        # {event_num: dict} 기존 이벤트 메타

    if not cards:
        return []

    card_meta = {
        c["card_id"]: {"card_name": c.get("card_name", ""), "card_type": c.get("card_type", "")}
        for c in cards
    }

    print(f"  보유 카드: {len(cards)}개 | 기존 이벤트: {len(events_json)}개")

    # 신규 (card_id, event_num) 쌍 및 수집 필요 이벤트 코드
    new_pairs: list[tuple[str, str]] = []
    new_event_nums: set[str] = set()

    # ── Step 1: 각 카드 상세 페이지 스캔 ────────────────────────
    print("\n[Step 1] 카드 상세 페이지 스캔...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx  = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()

        # 이벤트 HTML 캐시 (Step 2에서 메타도 추출)
        event_htmls: dict[str, str] = {}

        try:
            for i, card in enumerate(cards, 1):
                card_id   = card["card_id"]
                card_url  = card.get("url", f"{BASE_URL}/cpc/cr/CPCCR0201_01.hc?cardWcd={card_id}")

                try:
                    await page.goto(card_url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2000)
                    html = await page.content()
                except Exception as e:
                    print(f"  [{i}/{len(cards)}] {card_id} 로드 실패: {e}")
                    continue

                codes = extract_event_codes(html)
                new_for_card = [c for c in codes if (card_id, c) not in known]

                if new_for_card:
                    print(f"  [{i}/{len(cards)}] {card_id} | 신규 {len(new_for_card)}개: {new_for_card}")
                    for code in new_for_card:
                        new_pairs.append((card_id, code))
                        new_event_nums.add(code)
                else:
                    print(f"  [{i}/{len(cards)}] {card_id} | 신규 없음 ({len(codes)}개 확인)")

                await asyncio.sleep(1.0)

            print(f"\n  → 신규 (카드, 이벤트) 조합: {len(new_pairs)}개")

            if not new_pairs:
                return []

            # ── Step 2: 신규 이벤트 상세 페이지 크롤링 + 메타 추출 ─────
            print("\n[Step 2] 신규 이벤트 상세 크롤링...")

            for event_num in new_event_nums:
                if event_num in events_json:
                    # 기존 메타 재사용, HTML만 새로 수집
                    print(f"  {event_num}: 기존 메타 재사용")
                else:
                    url = EVENT_DETAIL_URL.format(event_num=event_num)
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        await page.wait_for_timeout(2000)
                        html = await page.content()
                        event_htmls[event_num] = html
                        meta = extract_event_meta(html, event_num)
                    except Exception as e:
                        print(f"  {event_num} 크롤링 실패: {e}")
                        meta = {
                            "event_num":   event_num,
                            "event_url":   EVENT_DETAIL_URL.format(event_num=event_num),
                            "event_title": "",
                            "period":      "",
                            "tags":        ["기타"],
                        }
                    events_json[event_num] = meta
                    print(f"  {event_num}: {meta['event_title'][:40]}")
                    await asyncio.sleep(1.0)

            # 기존 메타 재사용인 이벤트 HTML 수집
            for event_num in new_event_nums:
                if event_num not in event_htmls:
                    url = events_json[event_num]["event_url"]
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        await page.wait_for_timeout(2000)
                        event_htmls[event_num] = await page.content()
                    except Exception as e:
                        print(f"  {event_num} HTML 수집 실패: {e}")
                        event_htmls[event_num] = ""
                    await asyncio.sleep(1.0)

        except Exception as e:
            print(f"\n[오류] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    # ── Step 3: 파싱 → CSV 행 생성 ───────────────────────────────
    print("\n[Step 3] 이벤트 파싱...")

    from hd_crawl_events import parse_event_detail

    all_new_rows: list[dict] = []

    for card_id, event_num in new_pairs:
        event = events_json.get(event_num, {})
        html  = event_htmls.get(event_num, "")

        if not html or not event:
            print(f"  {card_id} × {event_num}: HTML/메타 없음 - 스킵")
            continue

        # 카드 한 개 기준으로 파싱 (event_card_map으로 card_id 직접 지정)
        rows = parse_event_detail(
            html,
            event,
            card_meta={card_id: card_meta[card_id]},
            event_card_map={event_num: [card_id]},
        )

        if rows:
            all_new_rows.extend(rows)
            print(f"  {card_id} × {event_num}: {len(rows)}행")
        else:
            print(f"  {card_id} × {event_num}: 파싱 결과 없음")

    # hd_events.json 저장 (신규 메타 반영)
    save_events_json(events_json)
    print(f"\n  [저장] {EVENTS_JSON} → {len(events_json)}개")

    return all_new_rows


# ─────────────────────────────────────────────
# 단독 실행
# ─────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("현대카드 보유 카드 기반 신규 이벤트 감지")
    print("=" * 60)

    new_rows = await detect_and_crawl()

    if not new_rows:
        print("\n[완료] 신규 이벤트 없음")
        return

    from hd_crawl_events import assign_event_ids, upsert_events_csv, CSV_FIELDS
    new_rows = assign_event_ids(new_rows)
    upsert_events_csv(EVENTS_CSV, new_rows)

    today   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_csv = NEW_CSV_TMPL.format(date=today)
    os.makedirs(_BASE, exist_ok=True)
    with open(new_csv, "w", newline="", encoding="utf-8-sig") as f:
        import csv as _csv
        writer = _csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(new_rows)
    print(f"  [신규 CSV] {new_csv} → {len(new_rows)}행")

    print()
    print("=" * 60)
    print(f"[완료] 신규 이벤트 {len(new_rows)}행 감지")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
