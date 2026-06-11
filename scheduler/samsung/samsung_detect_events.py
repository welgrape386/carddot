"""
samsung_detect_events.py - 삼성카드 신규 이벤트 감지

보유 카드(samsung_cards.json) 각각의 상세 페이지 bannerList 파싱 →
기존 samsung_events.json에 없는 이벤트 id = 신규 이벤트 →
신규 이벤트 CSV 행 반환

[단독 실행]
  python samsung_detect_events.py

[import 사용]
  from samsung_detect_events import detect_new_events
  new_rows = await detect_new_events()
"""

import asyncio
import csv
import json
import os
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright

_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from main import get_nuxt_data, goto_and_wait  # noqa: E402

SAMSUNG    = "https://www.samsungcard.com"
DETAIL_URL = f"{SAMSUNG}/home/card/cardinfo/PGHPPCCCardCardinfoDetails001"

_OUT          = os.path.join(_DIR, "output")
CARDS_JSON    = os.path.join(_OUT, "samsung_cards.json")
EVENTS_JSON   = os.path.join(_OUT, "samsung_events.json")
EVENTS_CSV    = os.path.join(_OUT, "samsung_events.csv")
NEW_CSV_TMPL  = os.path.join(_OUT, "samsung_new_events_{date}.csv")

CSV_FIELDS = [
    "event_id", "card_id", "company", "card_name",
    "origin_event_code", "event_title", "event_link",
    "start_date", "end_date", "event_type", "section",
    "event_content", "updated_at",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _format_date(value: str) -> str:
    """'20240101' 또는 '20240101-120000' → '2024-01-01'"""
    v = (value or "").split("-")[0]
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}" if len(v) >= 8 else ""


def load_cards() -> list[dict]:
    if not os.path.exists(CARDS_JSON):
        print(f"  [오류] {CARDS_JSON} 없음")
        return []
    with open(CARDS_JSON, encoding="utf-8") as f:
        return json.load(f)


def load_events_json() -> dict:
    """samsung_events.json → {origin_event_code: event_dict}"""
    if not os.path.exists(EVENTS_JSON):
        return {}
    with open(EVENTS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {e["origin_event_code"]: e for e in data if e.get("origin_event_code")}


def save_events_json(event_map: dict):
    os.makedirs(_OUT, exist_ok=True)
    with open(EVENTS_JSON, "w", encoding="utf-8") as f:
        json.dump(list(event_map.values()), f, ensure_ascii=False, indent=2)


def assign_event_ids(rows: list[dict]) -> list[dict]:
    """event_id가 비어 있는 행에 순번 기반 ID 부여"""
    max_num = 0
    if os.path.exists(EVENTS_CSV):
        with open(EVENTS_CSV, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                eid = row.get("event_id", "")
                try:
                    max_num = max(max_num, int(eid.split("_E")[-1]))
                except Exception:
                    pass

    counter = max_num
    for row in rows:
        if not row.get("event_id"):
            counter += 1
            row["event_id"] = f"SS_{counter:06d}"
    return rows


def upsert_events_csv(new_rows: list[dict]):
    """전체 이벤트 CSV upsert (event_id 기준)"""
    os.makedirs(_OUT, exist_ok=True)
    existing: dict[str, dict] = {}
    if os.path.exists(EVENTS_CSV):
        with open(EVENTS_CSV, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                existing[row["event_id"]] = row

    for row in new_rows:
        existing[row["event_id"]] = {f: row.get(f, "") for f in CSV_FIELDS}

    with open(EVENTS_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing.values())

    print(f"  [전체 CSV] {EVENTS_CSV} → {len(existing)}행")


async def detect_new_events() -> list[dict]:
    """
    보유 카드 기반 삼성카드 신규 이벤트 감지.

    Returns:
        신규 이벤트 CSV 행 리스트
    """
    cards      = load_cards()
    events_map = load_events_json()

    if not cards:
        print("  [오류] 카드 목록 없음")
        return []

    print(f"  보유 카드: {len(cards)}개 | 기존 이벤트: {len(events_map)}개")

    all_new_rows: list[dict] = []
    updated_at = _now_str()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx  = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()

        try:
            for i, card in enumerate(cards, 1):
                card_id   = card["card_id"]
                card_name = card.get("card_name", card_id)
                url       = card.get("link_url", f"{DETAIL_URL}?code={card_id}")

                try:
                    await goto_and_wait(
                        page, url,
                        "() => { try { return !!(window.__NUXT__?.data?.[0]?.wcms); } catch(e) { return false; } }",
                    )
                    nuxt = await get_nuxt_data(page)
                except Exception as e:
                    print(f"  [{i}/{len(cards)}] {card_id} 로드 실패: {e}")
                    await asyncio.sleep(1.0)
                    continue

                if not nuxt or not isinstance(nuxt, dict):
                    print(f"  [{i}/{len(cards)}] {card_id} NUXT 없음")
                    await asyncio.sleep(1.0)
                    continue

                banner_list  = nuxt.get("bannerList") or []
                card_banners = [
                    b for b in banner_list
                    if isinstance(b, dict) and b.get("code") == card_id
                ]

                new_for_card = [
                    b for b in card_banners
                    if str(b.get("id", "")) not in events_map
                ]

                if new_for_card:
                    print(f"  [{i}/{len(cards)}] {card_id} | 신규 {len(new_for_card)}개")
                    for b in new_for_card:
                        evt_id = str(b.get("id", ""))
                        row = {
                            "event_id":          "",
                            "card_id":           card_id,
                            "company":           "삼성",
                            "card_name":         card_name,
                            "origin_event_code": evt_id,
                            "event_title":       b.get("evtTitle", ""),
                            "event_link":        b.get("evtUrl", ""),
                            "start_date":        _format_date(b.get("sDate", "")),
                            "end_date":          _format_date(b.get("eDate", "")),
                            "event_type":        "이벤트",
                            "section":           "혜택",
                            "event_content":     "",
                            "updated_at":        updated_at,
                        }
                        all_new_rows.append(row)
                        events_map[evt_id] = row
                else:
                    print(f"  [{i}/{len(cards)}] {card_id} | 신규 없음 (배너 {len(card_banners)}개 확인)")

                await asyncio.sleep(1.0)

        except Exception as e:
            print(f"\n[오류] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    save_events_json(events_map)
    print(f"\n  [저장] {EVENTS_JSON} -> {len(events_map)}개")

    return all_new_rows


async def main():
    print("=" * 60)
    print("삼성카드 신규 이벤트 감지")
    print("=" * 60)

    new_rows = await detect_new_events()

    if not new_rows:
        print("\n[완료] 신규 이벤트 없음")
        return

    new_rows = assign_event_ids(new_rows)
    upsert_events_csv(new_rows)

    today   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_csv = NEW_CSV_TMPL.format(date=today)
    os.makedirs(_OUT, exist_ok=True)
    with open(new_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(new_rows)
    print(f"  [신규 CSV] {new_csv} -> {len(new_rows)}행")

    print()
    print("=" * 60)
    print(f"[완료] 신규 이벤트 {len(new_rows)}행 감지")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
