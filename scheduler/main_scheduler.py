"""
main_scheduler.py - KB + 현대카드 + 삼성카드 통합 스케줄러

Pipeline A - 신규 카드 감지:
  카드 목록 페이지 스크래핑 → 기존 JSON 비교 → 신규 카드 감지
  저장: ① 전체 카드 CSV (upsert)  ② 신규 카드만 CSV

Pipeline B - 신규 이벤트 감지:
  [HD] 보유 카드 페이지 라이브 스캔 → bnftWebEvntCd 비교 → 신규 이벤트
  [KB] 이벤트 목록 페이지 스크래핑 → 기존 JSON 비교 → 신규 이벤트
  [Samsung] 카드 상세 페이지 bannerList → 기존 JSON 비교 → 신규 이벤트
  저장: ① 전체 이벤트 CSV (upsert)  ② 신규 이벤트만 CSV

[실행]
  python main_scheduler.py
  python main_scheduler.py --pipeline a   # 카드 감지만
  python main_scheduler.py --pipeline b   # 이벤트 감지만
  python main_scheduler.py --company hd   # 현대카드만
  python main_scheduler.py --company kb   # KB만
  python main_scheduler.py --company samsung  # 삼성카드만

[GitHub Actions]
  .github/workflows/scheduler.yml 에서 daily cron 실행
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
ROOT_DIR    = os.path.dirname(os.path.abspath(__file__))
HD_DIR      = os.path.join(ROOT_DIR, "hd")
KB_DIR      = os.path.join(ROOT_DIR, "kb")
SAMSUNG_DIR = os.path.join(ROOT_DIR, "samsung")

for d in [HD_DIR, KB_DIR, SAMSUNG_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

# HD 경로
HD_FINAL_DIR      = os.path.join(HD_DIR, "hd_ouput")
HD_CARDS_JSON     = os.path.join(HD_FINAL_DIR, "hd_cards.json")
HD_CARDS_CSV      = os.path.join(HD_FINAL_DIR, "hd_cards.csv")
HD_NEW_CARDS_CSV  = os.path.join(HD_FINAL_DIR, "hd_new_cards_{date}.csv")
HD_EVENTS_CSV     = os.path.join(HD_FINAL_DIR, "hyundai_events.csv")
HD_NEW_EVENTS_CSV = os.path.join(HD_FINAL_DIR, "hd_new_events_{date}.csv")
HD_EVENTS_JSON    = os.path.join(HD_FINAL_DIR, "hd_events.json")

# KB 경로
KB_FINAL_DIR      = os.path.join(KB_DIR, "ouput")
KB_CARDS_JSON     = os.path.join(KB_FINAL_DIR, "kb_cards.json")
KB_CARDS_CSV      = os.path.join(KB_FINAL_DIR, "kb_cards.csv")
KB_NEW_CARDS_CSV  = os.path.join(KB_FINAL_DIR, "kb_new_cards_{date}.csv")
KB_EVENTS_CSV     = os.path.join(KB_FINAL_DIR, "kb_events.csv")
KB_NEW_EVENTS_CSV = os.path.join(KB_FINAL_DIR, "kb_new_events_{date}.csv")
KB_EVENTS_JSON    = os.path.join(KB_FINAL_DIR, "kb_events.json")

# Samsung 경로
SS_FINAL_DIR      = os.path.join(SAMSUNG_DIR, "output")
SS_CARDS_JSON     = os.path.join(SS_FINAL_DIR, "samsung_cards.json")
SS_CARDS_CSV      = os.path.join(SS_FINAL_DIR, "samsung_cards.csv")
SS_NEW_CARDS_CSV  = os.path.join(SS_FINAL_DIR, "samsung_new_cards_{date}.csv")
SS_EVENTS_CSV     = os.path.join(SS_FINAL_DIR, "samsung_events.csv")
SS_NEW_EVENTS_CSV = os.path.join(SS_FINAL_DIR, "samsung_new_events_{date}.csv")
SS_EVENTS_JSON    = os.path.join(SS_FINAL_DIR, "samsung_events.json")

# CSV 컬럼
HD_CARD_FIELDS = ["card_id", "card_name", "card_type", "url", "image_url"]
KB_CARD_FIELDS = ["card_id", "company", "card_name", "card_type", "image_url", "link_url"]
SS_CARD_FIELDS = ["card_id", "company", "card_name", "card_type", "image_url", "link_url"]

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────

def load_json(path: str):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def upsert_cards_csv(filepath: str, all_cards: list, fields: list):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    existing = {}
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                existing[row["card_id"]] = row
    for card in all_cards:
        existing[card["card_id"]] = {f: card.get(f, "") for f in fields}
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing.values())
    print(f"  [전체 CSV] {filepath} → {len(existing)}행")


def save_new_csv(filepath: str, rows: list, fields: list):
    if not rows:
        return
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  [신규 CSV] {filepath} → {len(rows)}행")


def section(title: str):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


# ─────────────────────────────────────────────
# Pipeline A - 신규 카드 감지
# ─────────────────────────────────────────────

async def pipeline_a_hd():
    """현대카드 신규 카드 감지 → JSON 업데이트 + 전체 CSV upsert + 신규 CSV"""
    import os as _os
    _orig = _os.getcwd()
    _os.chdir(HD_DIR)
    try:
        from hd_collect_cards import collect_cards
        new_cards = await collect_cards()

        all_cards = load_json(HD_CARDS_JSON)
        upsert_cards_csv(HD_CARDS_CSV, all_cards, HD_CARD_FIELDS)

        if new_cards:
            save_new_csv(HD_NEW_CARDS_CSV.format(date=TODAY), new_cards, HD_CARD_FIELDS)

            # TODO: 탐지 검증 후 파싱 활성화
            # from crawl4ai import AsyncWebCrawler
            # from hd_crawl4ai import BROWSER_CFG, crawl_card
            # from hd_parser_ai import process_card, save_card_data
            # async with AsyncWebCrawler(config=BROWSER_CFG) as crawler:
            #     for card in new_cards:
            #         cid = card["card_id"]
            #         ok = await crawl_card(crawler, card)
            #         if not ok:
            #             print(f"  [{cid}] 크롤링 실패 - 파싱 스킵")
            #             continue
            #         info, benefits, notices = process_card(cid, card)
            #         save_card_data(cid, info, benefits, notices)
            #         print(f"  [{cid}] 파싱 완료 | 혜택 {len(benefits)}행")

        return new_cards
    finally:
        _os.chdir(_orig)


async def pipeline_a_kb():
    """KB국민카드 신규 카드 감지 → JSON 업데이트 + 전체 CSV upsert + 신규 CSV"""
    import os as _os
    _orig = _os.getcwd()
    _os.chdir(KB_DIR)
    try:
        from kb_collect_cards import collect_cards
        new_cards = await collect_cards()

        all_cards = load_json(KB_CARDS_JSON)
        upsert_cards_csv(KB_CARDS_CSV, all_cards, KB_CARD_FIELDS)

        if new_cards:
            save_new_csv(KB_NEW_CARDS_CSV.format(date=TODAY), new_cards, KB_CARD_FIELDS)

            # TODO: 탐지 검증 후 파싱 활성화
            # from crawl4ai import AsyncWebCrawler, BrowserConfig
            # from kb_crawl import BROWSER_CFG, CRAWL_CFG, crawl_card
            # from kb_parser_ai import process_card, save_card_data
            # async with AsyncWebCrawler(config=BROWSER_CFG) as crawler:
            #     for card in new_cards:
            #         cid = card["card_id"]
            #         ok = await crawl_card(crawler, card)
            #         if not ok:
            #             print(f"  [{cid}] 크롤링 실패 - 파싱 스킵")
            #             continue
            #         info, benefits, notices = process_card(cid, card)
            #         save_card_data(cid, info, benefits, notices)
            #         print(f"  [{cid}] 파싱 완료 | 혜택 {len(benefits)}행")

        return new_cards
    finally:
        _os.chdir(_orig)


async def pipeline_a_samsung():
    """삼성카드 신규 카드 감지 → 전체 CSV upsert + 신규 CSV + 파싱"""
    import os as _os
    _orig = _os.getcwd()
    _os.chdir(SAMSUNG_DIR)
    try:
        from samsung_collect_cards import collect_cards
        new_cards = await collect_cards()

        all_cards = load_json(SS_CARDS_JSON)
        upsert_cards_csv(SS_CARDS_CSV, all_cards, SS_CARD_FIELDS)

        if new_cards:
            save_new_csv(SS_NEW_CARDS_CSV.format(date=TODAY), new_cards, SS_CARD_FIELDS)

            import aiohttp
            from playwright.async_api import async_playwright
            from main import crawl_card, parse_and_save, init_csv, USER_AGENT, SAMSUNG, DETAIL_URL

            init_csv()
            async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT, "Referer": SAMSUNG}) as session:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    ctx  = await browser.new_context(user_agent=USER_AGENT, locale="ko-KR")
                    page = await ctx.new_page()
                    try:
                        for card in new_cards:
                            cid = card["card_id"]
                            card["page_url"] = card.get("link_url", f"{DETAIL_URL}?code={cid}")
                            print(f"  [{cid}] 크롤링+파싱 중...")
                            card_data = await crawl_card(page, card, session)
                            if not card_data:
                                print(f"  [{cid}] 크롤링 실패 - 스킵")
                                continue
                            await parse_and_save(card_data, session)
                            print(f"  [{cid}] 파싱 완료")
                    finally:
                        await browser.close()

        return new_cards
    finally:
        _os.chdir(_orig)


# ─────────────────────────────────────────────
# Pipeline B - 신규 이벤트 감지
# ─────────────────────────────────────────────

async def pipeline_b_hd():
    """현대카드 신규 이벤트 감지 → 전체 CSV upsert + 신규 CSV"""
    import os as _os
    _orig = _os.getcwd()
    _os.chdir(HD_DIR)
    try:
        from hd_detect_card_events import detect_and_crawl
        new_rows = await detect_and_crawl()

        if new_rows:
            from hd_crawl_events import assign_event_ids, upsert_events_csv, CSV_FIELDS
            new_rows = assign_event_ids(new_rows)
            upsert_events_csv(HD_EVENTS_CSV, new_rows)
            save_new_csv(HD_NEW_EVENTS_CSV.format(date=TODAY), new_rows, CSV_FIELDS)

        return new_rows or []
    finally:
        _os.chdir(_orig)


async def pipeline_b_kb():
    """KB국민카드 신규 이벤트 감지 → 전체 CSV upsert + 신규 CSV"""
    import os as _os
    _orig = _os.getcwd()
    _os.chdir(KB_DIR)
    try:
        from kb_collect_event_urls import collect_event_urls

        current_events = await collect_event_urls()
        existing_map   = {e.get("event_num", ""): e for e in load_json(KB_EVENTS_JSON)}
        new_events     = [e for e in current_events if e.get("event_num", "") not in existing_map]

        print(f"  전체 {len(current_events)}개 | 신규 {len(new_events)}개")

        merged = {**existing_map, **{e.get("event_num", ""): e for e in current_events}}
        os.makedirs(os.path.dirname(KB_EVENTS_JSON), exist_ok=True)
        with open(KB_EVENTS_JSON, "w", encoding="utf-8") as f:
            json.dump(list(merged.values()), f, ensure_ascii=False, indent=2)

        if not new_events:
            return []

        from kb_crawl_events import crawl_events, assign_event_ids, upsert_events_csv, CSV_FIELDS
        new_rows = await crawl_events(new_events)
        if new_rows:
            new_rows = assign_event_ids(new_rows)
            upsert_events_csv(KB_EVENTS_CSV, new_rows)
            save_new_csv(KB_NEW_EVENTS_CSV.format(date=TODAY), new_rows, CSV_FIELDS)

        return new_rows or []
    finally:
        _os.chdir(_orig)


async def pipeline_b_samsung():
    """삼성카드 신규 이벤트 감지 → 전체 CSV upsert + 신규 CSV"""
    import os as _os
    _orig = _os.getcwd()
    _os.chdir(SAMSUNG_DIR)
    try:
        from samsung_detect_events import detect_new_events
        new_rows = await detect_new_events()

        if new_rows:
            from samsung_detect_events import assign_event_ids, upsert_events_csv, CSV_FIELDS
            new_rows = assign_event_ids(new_rows)
            upsert_events_csv(new_rows)
            save_new_csv(SS_NEW_EVENTS_CSV.format(date=TODAY), new_rows, CSV_FIELDS)

        return new_rows or []
    finally:
        _os.chdir(_orig)


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pipeline",
        choices=["a", "b", "all"],
        default="all",
        help="실행할 파이프라인 (a: 카드감지, b: 이벤트감지, all: 둘 다)",
    )
    parser.add_argument(
        "--company",
        choices=["hd", "kb", "samsung", "all"],
        default="all",
        help="실행할 카드사 (hd: 현대카드, kb: KB국민카드, samsung: 삼성카드, all: 전체)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"통합 스케줄러 실행: {TODAY}  company={args.company}  pipeline={args.pipeline}")
    print("=" * 60)

    errors = []

    if args.pipeline in ("a", "all"):
        section("[Pipeline A] 신규 카드 감지")
        if args.company in ("hd", "all"):
            print("\n▶ 현대카드")
            try:
                new = await pipeline_a_hd()
                print(f"  → 신규 카드 {len(new)}개" if new else "  → 신규 카드 없음")
            except Exception as e:
                print(f"  [오류] {e}")
                errors.append(f"HD 카드: {e}")
        if args.company in ("kb", "all"):
            print("\n▶ KB국민카드")
            try:
                new = await pipeline_a_kb()
                print(f"  → 신규 카드 {len(new)}개" if new else "  → 신규 카드 없음")
            except Exception as e:
                print(f"  [오류] {e}")
                errors.append(f"KB 카드: {e}")
        if args.company in ("samsung", "all"):
            print("\n▶ 삼성카드")
            try:
                new = await pipeline_a_samsung()
                print(f"  → 신규 카드 {len(new)}개" if new else "  → 신규 카드 없음")
            except Exception as e:
                print(f"  [오류] {e}")
                errors.append(f"Samsung 카드: {e}")

    if args.pipeline in ("b", "all"):
        section("[Pipeline B] 신규 이벤트 감지")
        if args.company in ("hd", "all"):
            print("\n▶ 현대카드")
            try:
                new = await pipeline_b_hd()
                print(f"  → 신규 이벤트 {len(new)}행" if new else "  → 신규 이벤트 없음")
            except Exception as e:
                print(f"  [오류] {e}")
                import traceback; traceback.print_exc()
                errors.append(f"HD 이벤트: {e}")
        if args.company in ("kb", "all"):
            print("\n▶ KB국민카드")
            try:
                new = await pipeline_b_kb()
                print(f"  → 신규 이벤트 {len(new)}행" if new else "  → 신규 이벤트 없음")
            except Exception as e:
                print(f"  [오류] {e}")
                import traceback; traceback.print_exc()
                errors.append(f"KB 이벤트: {e}")
        if args.company in ("samsung", "all"):
            print("\n▶ 삼성카드")
            try:
                new = await pipeline_b_samsung()
                print(f"  → 신규 이벤트 {len(new)}행" if new else "  → 신규 이벤트 없음")
            except Exception as e:
                print(f"  [오류] {e}")
                import traceback; traceback.print_exc()
                errors.append(f"Samsung 이벤트: {e}")

    # 최종 요약
    print()
    print("=" * 60)
    print(f"[완료] {TODAY}")
    if errors:
        print(f"  오류 {len(errors)}건:")
        for err in errors:
            print(f"    - {err}")
        sys.exit(1)
    else:
        print("  모든 파이프라인 정상 완료")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
