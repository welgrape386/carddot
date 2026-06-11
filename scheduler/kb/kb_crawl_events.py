"""
kb_crawl_events_retry.py - 스킵된 이벤트 재크롤링 (48개 카드 기준)

현재 kb_events.csv에 없는 이벤트만 크롤링
→ 전체 카드 대상(cooperationcode 없음)은 스킵
→ 48개 카드 중 매칭된 것만 kb_events.csv에 추가
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import asyncio
import csv
import json
import os
import re
from datetime import datetime, timezone

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
FINAL_DIR     = os.path.join(BASE_DIR, "ouput")
EVENTS_JSON   = os.path.join(FINAL_DIR, "kb_events.json")
OUTPUT_CSV    = os.path.join(FINAL_DIR, "kb_events.csv")
CARDS_JSON    = os.path.join(FINAL_DIR, "kb_cards.json")  # kb_collect_cards.py 출력

COMPANY    = "국민"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

CSV_FIELDS = [
    "event_id", "card_id", "company", "card_name",
    "origin_event_code", "event_title", "event_link",
    "start_date", "end_date", "event_type",
    "section", "event_content", "updated_at",
]

EVENT_TYPE_KEYWORDS = {"캐시백", "포인트", "포인트리", "할인", "서비스", "마일리지", "경품"}

BUTTON_SKIP = re.compile(
    r'^(응모하기|신청하기|자세히\s*보기|신청하러\s*가기|신청하러\s*하기'
    r'|더보기|바로가기|[가-힣\s·]+추가\s*캐시백|[가-힣\s·]+추가\s*할인'
    r'|[가-힣\s·]+바로가기|[가-힣\s·]+신청하기)$'
)

SKIP_SECTIONS = {"대상카드", "행사 대상카드", "추천카드", "대상카드(New)", "대상카드(추천)"}

SECTION_MAP = {
    "이용 전 확인해주세요": "확인사항",
    "유의사항": "확인사항",
    "이용전 확인해주세요": "확인사항",
    "확인사항": "확인사항",
}

TYPE_MAP = {
    "포인트리": "포인트",
    "경품": "기타",
    "캐시백,경품": "캐시백",
    "할인,캐시백": "할인",
}


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def parse_dates(text):
    full  = re.findall(r'(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})', text)
    short = re.findall(r'[~～]\s*(\d{1,2})[.\-](\d{1,2})', text)
    if not full:
        return "", ""
    s = full[0]
    start_date = f"{s[0]}-{int(s[1]):02d}-{int(s[2]):02d}"
    if len(full) >= 2:
        e = full[1]
        end_date = f"{e[0]}-{int(e[1]):02d}-{int(e[2]):02d}"
    elif short:
        e = short[0]
        end_date = f"{s[0]}-{int(e[0]):02d}-{int(e[1]):02d}"
    else:
        end_date = ""
    return start_date, end_date


def classify_event_type(tags):
    filtered = [t for t in tags if t in EVENT_TYPE_KEYWORDS]
    raw = ",".join(filtered)
    return TYPE_MAP.get(raw, raw)


def parse_table(tbl):
    rows = tbl.find_all("tr")
    if not rows:
        return ""
    headers = [cell.get_text(strip=True) for cell in rows[0].find_all(["th", "td"])]
    lines = []
    for tr in rows[1:]:
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
        if not any(cells):
            continue
        parts = [f"{h}: {v}" for h, v in zip(headers, cells) if v] if headers else [v for v in cells if v]
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def clean_tag_text(tag):
    table_texts = []
    for tbl in tag.find_all("table"):
        t = parse_table(tbl)
        if t:
            table_texts.append(t)
        tbl.decompose()
    lines = []
    for line in tag.get_text("\n", strip=True).split("\n"):
        line = line.strip()
        if not line or len(line) < 2:
            continue
        if BUTTON_SKIP.match(line):
            continue
        lines.append(line)
    result = []
    if lines:
        result.append("\n".join(lines))
    if table_texts:
        result.extend(table_texts)
    return "\n".join(result)


def load_card_meta():
    """kb_cards.json에서 card_id → {card_name} 매핑 로드."""
    meta = {}
    if not os.path.exists(CARDS_JSON):
        print(f"  [경고] {CARDS_JSON} 없음 - 카드 메타 없이 진행")
        return meta
    with open(CARDS_JSON, encoding="utf-8") as f:
        for card in json.load(f):
            cid = str(card.get("card_id", "")).zfill(5)
            if cid:
                meta[cid] = {"card_name": card.get("card_name", "")}
    print(f"  카드 메타 로드: {len(meta)}개 카드")
    return meta


def load_existing_events():
    if not os.path.exists(OUTPUT_CSV):
        return set(), []
    with open(OUTPUT_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    saved_nums = set(r["origin_event_code"] for r in rows)
    return saved_nums, rows


def get_next_event_id(card_id, existing_rows):
    """카드별 최대 이벤트 번호 파악 후 다음 번호 반환"""
    existing = [r["event_id"] for r in existing_rows if r["card_id"] == card_id and r["event_id"]]
    if not existing:
        return f"{card_id}_E0001"
    nums = []
    for eid in existing:
        m = re.search(r'_E(\d+)$', eid)
        if m:
            nums.append(int(m.group(1)))
    next_num = max(nums) + 1 if nums else 1
    return f"{card_id}_E{next_num:04d}"


def parse_event_body(html, event, card_meta):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find(id="eventBodyRE")
    if not body:
        return []

    head  = body.find(class_=lambda c: c and "eventHead" in " ".join(c))
    title = head.get_text(" ", strip=True) if head else event["event_title"]

    start_date, end_date = parse_dates(event["period"])
    event_type = classify_event_type(event["tags"])

    # cooperationcode 추출
    card_ids = []
    for m in re.finditer(r'cooperationcode=(\d{5})', html):
        cid = m.group(1).zfill(5)
        if cid not in card_ids:
            card_ids.append(cid)

    matched = [cid for cid in card_ids if cid in card_meta]

    # cooperationcode 없으면 전체 대상 → 스킵
    if not card_ids:
        return None  # None = 전체 대상 스킵
    if not matched:
        return []    # 빈 리스트 = 우리 카드 아님

    # 섹션 파싱
    sections = []
    cols = body.find_all("div", class_="column")
    if len(cols) >= 2:
        target_text = cols[1].get_text("\n", strip=True)
        target_text = re.sub(r'^대상\s*', '', target_text).strip()
        if target_text:
            sections.append(("대상", target_text))

    skip_section   = False
    current_section = ""
    current_lines   = []

    for tag in body.children:
        if not hasattr(tag, "name") or not tag.name:
            continue
        cls = " ".join(tag.get("class", []))
        if "btnGroup" in cls:
            continue
        if tag.name == "h3":
            sec_name = tag.get_text(strip=True)
            if not skip_section and current_lines:
                sec_mapped = SECTION_MAP.get(current_section, current_section)
                sections.append((sec_mapped, "\n".join(current_lines)))
            current_lines = []
            if sec_name in SKIP_SECTIONS:
                skip_section    = True
                current_section = ""
            else:
                skip_section    = False
                current_section = sec_name
            continue
        if skip_section:
            continue
        if "eventHead" in cls or cls == "column":
            continue
        if "no-robot" in cls:
            if current_lines:
                sec_mapped = SECTION_MAP.get(current_section, current_section)
                sections.append((sec_mapped, "\n".join(current_lines)))
                current_lines   = []
                current_section = ""
            text = clean_tag_text(tag)
            if text:
                sections.append(("확인사항", text))
            continue
        text = clean_tag_text(tag)
        if text:
            current_lines.append(text)

    if current_lines:
        sec_mapped = SECTION_MAP.get(current_section, current_section)
        sections.append((sec_mapped, "\n".join(current_lines)))

    # 같은 섹션 합치기
    merged = {}
    for sec, content in sections:
        if sec in merged:
            merged[sec] += "\n" + content
        else:
            merged[sec] = content

    if not merged:
        merged = {"": ""}

    return {"matched": matched, "title": title, "start_date": start_date,
            "end_date": end_date, "event_type": event_type, "sections": merged}


async def crawl_retry():
    card_meta = load_card_meta()
    saved_nums, existing_rows = load_existing_events()

    with open(EVENTS_JSON, encoding="utf-8") as f:
        all_events = json.load(f)

    # 저장 안 된 이벤트만
    target_events = [e for e in all_events if e["event_num"] not in saved_nums]
    print(f"  재크롤링 대상: {len(target_events)}개 이벤트")
    print("-" * 60)

    new_rows = []
    matched_count  = 0
    skipped_all    = 0
    skipped_nomatch = 0

    # 카드별 현재 이벤트 번호 트래킹
    card_event_counter = {}
    for r in existing_rows:
        cid = r["card_id"]
        eid = r["event_id"]
        if cid and eid:
            m = re.search(r'_E(\d+)$', eid)
            if m:
                num = int(m.group(1))
                card_event_counter[cid] = max(card_event_counter.get(cid, 0), num)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx  = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()

        try:
            for i, event in enumerate(target_events, 1):
                print(f"  [{i:3d}/{len(target_events)}] {event['event_title'][:35]}")

                try:
                    await page.goto(event["event_url"], wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                    html = await page.content()
                except Exception as e:
                    print(f"    ❌ 로드 실패: {e}")
                    continue

                result = parse_event_body(html, event, card_meta)

                if result is None:
                    skipped_all += 1
                    print(f"    ⏭ 전체 카드 대상 → 스킵")
                elif result == []:
                    skipped_nomatch += 1
                    print(f"    ⏭ 매칭 카드 없음 → 스킵")
                else:
                    matched_count += 1
                    for cid in result["matched"]:
                        card_event_counter[cid] = card_event_counter.get(cid, 0) + 1
                        event_id = f"{cid}_E{card_event_counter[cid]:04d}"
                        base = {
                            "event_id":          event_id,
                            "card_id":           cid,
                            "company":           COMPANY,
                            "card_name":         card_meta.get(cid, {}).get("card_name", ""),
                            "origin_event_code": event["event_num"],
                            "event_title":       result["title"],
                            "event_link":        event["event_url"],
                            "start_date":        result["start_date"],
                            "end_date":          result["end_date"],
                            "event_type":        result["event_type"],
                            "updated_at":        now_str(),
                        }
                        for sec, content in result["sections"].items():
                            new_rows.append({**base, "section": sec, "event_content": content})

                    names = [card_meta.get(cid, {}).get("card_name", cid) for cid in result["matched"]]
                    print(f"    ✅ 매칭: {names}")

                await asyncio.sleep(1.5)

        finally:
            await browser.close()

    # CSV upsert
    if new_rows:
        all_rows = existing_rows + new_rows
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_rows)

    print("=" * 60)
    print(f"✅ 완료!")
    print(f"   재크롤링: {len(target_events)}개")
    print(f"   신규 매칭: {matched_count}개 이벤트 ({len(new_rows)}행 추가)")
    print(f"   전체 대상 스킵: {skipped_all}개")
    print(f"   미매칭 스킵: {skipped_nomatch}개")
    print(f"   CSV 총 행수: {len(existing_rows) + len(new_rows)}행")
    print("=" * 60)


# ─────────────────────────────────────────────
# import용 함수 (main_scheduler.py 에서 호출)
# ─────────────────────────────────────────────

def assign_event_ids(rows: list, existing_rows: list = None) -> list:
    """
    card_id별 이벤트 순번 부여 → event_id 할당.
    existing_rows가 주어지면 기존 번호 이어서 부여.
    """
    if existing_rows is None:
        existing_rows = []

    card_counter: dict[str, int] = {}
    for r in existing_rows:
        cid = r.get("card_id", "")
        eid = r.get("event_id", "")
        if cid and eid:
            m = re.search(r'_E(\d+)$', eid)
            if m:
                card_counter[cid] = max(card_counter.get(cid, 0), int(m.group(1)))

    # (card_id, origin_event_code) → event_id 매핑 (동일 이벤트 행들은 같은 id)
    code_to_id: dict[tuple, str] = {}
    for row in rows:
        cid  = row.get("card_id", "")
        code = row.get("origin_event_code", "")
        key  = (cid, code)
        if key not in code_to_id:
            card_counter[cid] = card_counter.get(cid, 0) + 1
            code_to_id[key] = f"{cid}_E{card_counter[cid]:04d}"
        row["event_id"] = code_to_id[key]

    return rows


def upsert_events_csv(filepath: str, new_rows: list):
    """기존 CSV에 신규 이벤트 행 upsert (origin_event_code + card_id + section 키)."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    existing = []
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8-sig") as f:
            existing = list(csv.DictReader(f))

    new_keys = {
        (r.get("origin_event_code", ""), r.get("card_id", ""), r.get("section", ""))
        for r in new_rows
    }
    merged = [
        r for r in existing
        if (r.get("origin_event_code", ""), r.get("card_id", ""), r.get("section", ""))
        not in new_keys
    ] + new_rows

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged)

    print(f"  [저장] {filepath} -> {len(merged)}행 (신규 {len(new_rows)}행)")


async def crawl_events(events: list, card_meta: dict = None) -> list:
    """
    KB 이벤트 목록 크롤링 → CSV 행 리스트 반환 (import용).

    Args:
        events: [{event_num, event_url, event_title, period, tags}, ...]
        card_meta: {card_id: {card_name}, ...} (None이면 내부 로드)

    Returns:
        CSV 행 리스트 (전체 카드 대상 이벤트는 포함하지 않음)
    """
    if card_meta is None:
        try:
            card_meta = load_card_meta()
        except Exception:
            card_meta = {}

    _, existing_rows = load_existing_events()
    card_event_counter: dict[str, int] = {}
    for r in existing_rows:
        cid = r.get("card_id", "")
        eid = r.get("event_id", "")
        if cid and eid:
            m = re.search(r'_E(\d+)$', eid)
            if m:
                card_event_counter[cid] = max(card_event_counter.get(cid, 0), int(m.group(1)))

    new_rows = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx  = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()

        try:
            for i, event in enumerate(events, 1):
                print(f"  [{i:3d}/{len(events)}] {event.get('event_title','')[:35]}")

                try:
                    await page.goto(event["event_url"], wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                    html = await page.content()
                except Exception as e:
                    print(f"    [실패] {e}")
                    continue

                result = parse_event_body(html, event, card_meta)

                if result is None:
                    print(f"    [스킵] 전체 카드 대상")
                elif result == []:
                    print(f"    [스킵] 매칭 카드 없음")
                else:
                    for cid in result["matched"]:
                        card_event_counter[cid] = card_event_counter.get(cid, 0) + 1
                        event_id = f"{cid}_E{card_event_counter[cid]:04d}"
                        base = {
                            "event_id":          event_id,
                            "card_id":           cid,
                            "company":           COMPANY,
                            "card_name":         card_meta.get(cid, {}).get("card_name", ""),
                            "origin_event_code": event["event_num"],
                            "event_title":       result["title"],
                            "event_link":        event["event_url"],
                            "start_date":        result["start_date"],
                            "end_date":          result["end_date"],
                            "event_type":        result["event_type"],
                            "updated_at":        now_str(),
                        }
                        for sec, content in result["sections"].items():
                            new_rows.append({**base, "section": sec, "event_content": content})

                    names = [card_meta.get(c, {}).get("card_name", c) for c in result["matched"]]
                    print(f"    [매칭] {names}")

                await asyncio.sleep(1.5)

        finally:
            await browser.close()

    return new_rows


if __name__ == "__main__":
    print("=" * 60)
    print("KB 스킵 이벤트 재크롤링 (38개 카드 기준)")
    print("=" * 60)
    asyncio.run(crawl_retry())
