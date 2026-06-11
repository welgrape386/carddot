"""
hd_crawl_events.py - 현대카드 이벤트 상세 파싱 → CSV

hd_events.json 읽기 → 각 이벤트 상세 페이지 접속
→ event_content 파싱 → card_id 매핑 → CSV 저장

[카드 매핑 전략 - 2단계]
  1순위: 카드 상세 HTML(html/*.html)에 박힌 bnftWebEvntCd 역매핑
  2순위: 이벤트 "대상 카드" 섹션 텍스트 → 카드명 키워드 매칭
  미매핑:  card_id="" (전체 대상)

[CSV 컬럼]
  card_id, company, card_name, origin_event_code,
  event_title, event_link, start_date, end_date,
  event_type, section, event_content, updated_at

[단독 실행]
  python hd_crawl_events.py

[import 사용]
  from hd_crawl_events import crawl_events, load_card_meta
  card_meta = load_card_meta()
  rows = await crawl_events(events, card_meta)
"""

import asyncio
import csv
import json
import os
import re
from datetime import datetime, timezone

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
_BASE          = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hd_ouput")
EVENTS_JSON    = os.path.join(_BASE, "hd_events.json")
CARDS_JSON     = os.path.join(_BASE, "hd_cards.json")
CARDS_HTML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hd_html")
OUTPUT_DIR     = _BASE
OUTPUT_CSV     = os.path.join(OUTPUT_DIR, "hyundai_events.csv")
COMPANY        = "현대"

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

# 섹션 파싱 제외 (카드 목록만 있고 내용 없는 섹션)
SKIP_SECTIONS = {"대상 카드", "대상카드"}
# 네비게이션 섹션 (이전글/다음글)
NAV_SECTIONS  = {"이전글", "다음글", "목록"}

# ─────────────────────────────────────────────
# 카드명 키워드 매핑
# (긴 키워드 우선 → 짧은 키워드로 오매칭 방지)
# ─────────────────────────────────────────────
# card_id → [키워드, ...] (앞에서부터 우선순위)
_CARD_KEYWORDS: dict[str, list[str]] = {
    # ── 더 시리즈 ──────────────────────────────
    "TBE4":   ["the Black"],
    "TPE4":   ["the Purple"],
    "TRSTE2": ["the Red Stripe Edition2", "the Red Stripe"],
    "TRE6":   ["the Red"],
    "TGE3":   ["the Green Edition3", "the Green"],
    "TPIE2":  ["the Pink Edition2", "the Pink"],
    "TO":     ["the Orange", "MY BUSINESS the Orange"],
    # ── 프리미엄 ───────────────────────────────
    "SPM":    ["현대카드 Summit", "현대카드MY BUSINESS Summit", "Summit"],
    "BTMCE":  ["Summit CE"],
    "MXBE2":  ["MX Black Edition2", "MX Black"],
    "BTCP":   ["Boutique - Copper"],
    "BTVV":   ["Boutique - Velvet"],
    "BTST":   ["Boutique - Satin"],
    "MPE4":   ["MM"],
    # ── M/X/Z 시리즈 ───────────────────────────
    "ME4":    ["현대카드M Edition", "현대카드M"],
    "XPE4":   ["현대카드X Edition", "현대카드X", "현대카드 X"],
    "XCUT":   ["X Cut"],
    "XSAV":   ["X Save"],
    "ZWK":    ["Z everyday", "Z 에브리데이"],
    "ZFE2":   ["Z family Edition2", "Z family", "Z 패밀리"],
    "ZWE2":   ["Z work Edition2", "Z work", "Z 워크"],
    "ZOE2":   ["Z play", "Z 플레이"],
    "ZRUP":   ["ZERO Up"],
    "MZROE3": ["ZERO Edition3 (포인트형)", "ZERO Edition3"],
    "ZROE3":  ["ZERO Edition3 (할인형)"],
    # ── D/H/O/S/T ──────────────────────────────
    "HCD":    ["현대카드D", "카드D", " D,", " D "],
    "HCH":    ["현대카드H", "카드H", " H,", " H "],
    "HCO":    ["현대카드O", "카드O", " O,", " O "],
    "HCS":    ["현대카드S", "카드S", " S,", " S "],
    "HCT":    ["현대카드T", "카드T", " T,", " T "],
    # ── American Express ───────────────────────
    "AMPTE2": ["American Express  The Platinum Card Edition2",
               "American Express The Platinum Card Edition2",
               "The Platinum Card Edition2"],
    "AMGLE2": ["American Express Gold Card Edition2", "American Express Gold"],
    "AMGRE2": ["American Express Green Card Edition2", "American Express Green"],
    # ── 제휴카드 ───────────────────────────────
    "NVE2":   ["네이버 현대카드", "네이버"],
    "OLVYHC": ["올리브영"],
    "NXNX":   ["넥슨"],
    "GEPHC":  ["GS칼텍스", "GS Caltex"],
    "ESPE3":  ["지마켓", "스마일카드"],
    "SGE2":   ["SSG.COM", "SSG"],
    "HGEHC":  ["제네시스", "Genesis"],
    "NOLHC":  ["NOL", "인터파크"],
    "SCHC":   ["쏘카"],
    "MLGTE3": ["LG U+-현대카드", "LG U+"],
    "CWYHC":  ["코웨이 현대카드", "코웨이"],
    "LGEHC":  ["LG전자 현대카드", "LG전자"],
    "SKIHC":  ["SK인텔릭스"],
    "CCKHC":  ["쿠쿠"],
    "CHHHC":  ["청호나이스"],
    "MCWYE3": ["coway-현대카드", "coway"],
    "YSHC":   ["예스24"],
    "MCJE2":  ["The CJ"],
    "MIMB":   ["iM뱅크"],
    "MDBI":   ["DB손해보험 현대카드", "DB손해보험"],
    "MHMFI":  ["현대해상 현대카드", "현대해상"],
    "SLHC":   ["햇살론"],
    "FCDY":   ["청소년 가족카드", "가족카드"],
    "HDSHE2": ["현대홈쇼핑 현대카드", "현대홈쇼핑"],
    # ── 체크/하이브리드 ────────────────────────
    "CCM":    ["체크(포인트형)"],
    "CCD":    ["체크(캐시백형)"],
    "CCA":    ["체크(Apple Pay", "Apple Pay Rewards"],
    "CCMH":   ["하이브리드(포인트형)"],
    "CCDH":   ["하이브리드(캐시백형)"],
    "CCAH":   ["하이브리드(Apple"],
}

# 긴 키워드 우선: (keyword, card_id) 리스트, 길이 내림차순
_KW_LIST: list[tuple[str, str]] = sorted(
    [(kw, cid) for cid, kws in _CARD_KEYWORDS.items() for kw in kws],
    key=lambda x: -len(x[0]),
)


def match_cards_from_text(target_text: str, card_meta: dict) -> list:
    """
    '대상 카드' 섹션 텍스트에서 card_id 목록 추출.
    긴 키워드 우선 매칭, 중복 제거.
    키워드 뒤에 한글/영문자가 바로 이어지는 경우 제외 (오매칭 방지).
    예: '현대카드M' → '현대카드MY BUSINESS' 에서 불매칭.
    """
    matched = []
    # ® © ™ 등 특수문자 제거 후 비교
    text = re.sub(r"[®©™]", "", target_text)
    for kw, cid in _KW_LIST:
        if cid in matched:
            continue
        if cid not in card_meta:
            continue
        # 키워드 뒤에 한글·영문자·숫자가 바로 오지 않을 때만 매칭
        pattern = re.escape(kw) + r"(?![가-힣A-Za-z0-9])"
        if re.search(pattern, text):
            matched.append(cid)
    return matched


# ─────────────────────────────────────────────
# 1순위: 카드 HTML → 이벤트 코드 역매핑
# ─────────────────────────────────────────────

def load_event_card_map() -> dict:
    """
    html/*.html 파일에서 bnftWebEvntCd 패턴 추출 →
    event_code → [card_id, ...] 매핑 반환.
    """
    event_to_cards: dict[str, list] = {}
    if not os.path.isdir(CARDS_HTML_DIR):
        return event_to_cards

    for fname in os.listdir(CARDS_HTML_DIR):
        if not fname.endswith("_main.html"):
            continue
        card_id = fname.replace("_main.html", "")
        fpath   = os.path.join(CARDS_HTML_DIR, fname)
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            html = f.read()
        codes = list(dict.fromkeys(re.findall(r"bnftWebEvntCd=([A-Z0-9]+)", html)))
        for code in codes:
            event_to_cards.setdefault(code, [])
            if card_id not in event_to_cards[code]:
                event_to_cards[code].append(card_id)

    return event_to_cards


# ─────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────

def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def parse_dates(period: str) -> tuple:
    """'2026.06.05~2026.07.23' → ('2026-06-05', '2026-07-23')"""
    parts = re.findall(r"(\d{4})\.(\d{2})\.(\d{2})", period)
    if len(parts) >= 2:
        s = f"{parts[0][0]}-{parts[0][1]}-{parts[0][2]}"
        e = f"{parts[1][0]}-{parts[1][1]}-{parts[1][2]}"
        return s, e
    full = re.findall(r"(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})", period)
    if len(full) >= 2:
        s = f"{full[0][0]}-{int(full[0][1]):02d}-{int(full[0][2]):02d}"
        e = f"{full[1][0]}-{int(full[1][1]):02d}-{int(full[1][2]):02d}"
        return s, e
    return "", ""


def clean_text(el) -> str:
    """BeautifulSoup 요소 → 정제된 텍스트."""
    lines = []
    for line in el.get_text("\n", strip=True).split("\n"):
        line = line.strip()
        if line and len(line) >= 2:
            lines.append(line)
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 카드 메타 로드
# ─────────────────────────────────────────────

def load_card_meta() -> dict:
    """card_id → {card_name, card_type}"""
    meta = {}
    if os.path.exists(CARDS_JSON):
        with open(CARDS_JSON, encoding="utf-8") as f:
            for c in json.load(f):
                meta[c["card_id"]] = {
                    "card_name": c.get("card_name", ""),
                    "card_type": c.get("card_type", ""),
                }
    return meta


# ─────────────────────────────────────────────
# 이벤트 상세 파싱
# ─────────────────────────────────────────────

def _find_container(soup) -> object:
    """
    세 가지 컨테이너 형식 지원:
      1) div.event_content  (일반 이벤트)
      2) div.list-con1      (일부 이벤트)
      3) div.w792           (직접 mt52 배치 이벤트)
    """
    return (
        soup.find(class_="event_content")
        or soup.find(class_="list-con1")
        or soup.find("div", class_="w792")
    )


def _get_section_header(div) -> str | None:
    """
    .mt52 div 내에서 섹션 헤더 텍스트 추출.
    p.h3_b_lt 또는 h4.h3_b_lt 모두 지원.
    """
    h = div.find(["p", "h4"], class_="h3_b_lt")
    return h.get_text(strip=True) if h else None


def _extract_target_card_text(ec) -> str:
    """
    컨테이너에서 '대상 카드' 섹션 텍스트 추출.
    """
    for div in ec.find_all("div", class_="mt52"):
        sec = _get_section_header(div)
        if sec and sec in SKIP_SECTIONS:
            h = div.find(["p", "h4"], class_="h3_b_lt")
            if h:
                h.decompose()
            return div.get_text(" ", strip=True)
    return ""


# 섹션명 정규화 규칙 (패턴 → 정규화명), 위에서부터 순서대로 적용
# 패턴이 섹션명과 매칭되면 해당 정규화명으로 변환
_SECTION_RULES: list[tuple[re.Pattern, str]] = [
    # 혜택으로 시작하는 모든 변형 → 혜택
    # 예: "혜택 1.", "혜택 2.", "혜택 ①, ② 이용 방법"의 혜택 부분은 아래 방법 규칙에서 처리
    (re.compile(r"^혜택\s*[\d①②③④⑤]+[.\s]"), "혜택"),

    # 방법 포함 → 이용 방법
    # 예: "신청 방법", "이용 방법", "혜택 ①, ② 이용 방법"
    (re.compile(r"방법"), "이용 방법"),

    # 대상 관련 장소/상품 → 대상
    # 예: "제휴 호텔", "대상 호텔", "대상 공항", "대상점", "대상 상품"
    (re.compile(r"(호텔|공항|대상점|대상\s*상품)"), "대상"),

    # 서비스/수수료/안내/제공일 성격 → 혜택
    # 예: "브랜드별 선택제공서비스 안내", "추가 발급수수료", "혜택 제공일"
    (re.compile(r"(서비스\s*안내|발급수수료|선택제공|제공일)"), "혜택"),
]


def _normalize_section_name(name: str) -> str:
    """섹션명 하나를 규칙 기반으로 정규화."""
    for pattern, normalized in _SECTION_RULES:
        if pattern.search(name):
            return normalized
    return name


def _normalize_sections(sections: list) -> list:
    """
    섹션명 정규화 + 같은 섹션명으로 병합.
    """
    normalized = []
    for name, content in sections:
        norm = _normalize_section_name(name)

        # 직전 섹션과 같은 이름이면 내용 병합
        if normalized and normalized[-1][0] == norm:
            normalized[-1] = (norm, normalized[-1][1] + "\n" + content)
        else:
            normalized.append((norm, content))

    return normalized


def parse_event_detail(
    html: str,
    event: dict,
    card_meta: dict,
    event_card_map: dict | None = None,
) -> list:
    """
    이벤트 상세 페이지 HTML 파싱 → CSV 행 리스트 반환.

    Args:
        html:           이벤트 상세 페이지 HTML
        event:          hd_events.json 이벤트 dict
        card_meta:      card_id → {card_name}
        event_card_map: event_code → [card_id, ...] (카드HTML 역매핑)
    """
    soup = BeautifulSoup(html, "html.parser")
    ec   = _find_container(soup)
    if not ec:
        return []

    start_date, end_date = parse_dates(event["period"])
    event_type = ",".join(event.get("tags", []))
    event_num  = event["event_num"]

    # ── 카드 ID 결정 (2단계) ──────────────────
    managed = []

    # 1순위: 카드 HTML 역매핑
    if event_card_map and event_num in event_card_map:
        managed = [c for c in event_card_map[event_num] if c in card_meta]

    # 2순위: "대상 카드" 텍스트 키워드 매칭
    if not managed:
        target_text = _extract_target_card_text(ec)
        if target_text:
            managed = match_cards_from_text(target_text, card_meta)

    # event_content 내 cardWcd 링크 (일부 이벤트)
    if not managed:
        ec_html = str(ec)
        wcd_ids = list(dict.fromkeys(
            m.group(1) for m in re.finditer(r"cardWcd=([A-Z][A-Z0-9]+)", ec_html)
            if m.group(1) in card_meta
        ))
        managed = wcd_ids

    if not managed:
        return []  # 전체 대상 이벤트는 제외

    # ── 섹션 파싱 ─────────────────────────────
    sections = []

    # [Visa] / [Mastercard] / [UnionPay] 처럼 [브랜드명] 형태 헤더 패턴
    _BRAND_HEADER = re.compile(r"^\[.+\]$")

    for div in ec.find_all("div", class_="mt52", recursive=False):
        sec_name = _get_section_header(div)
        if not sec_name:
            continue
        if sec_name in NAV_SECTIONS:
            continue
        if sec_name in SKIP_SECTIONS:
            continue

        h = div.find(["p", "h4"], class_="h3_b_lt")
        content_parts = []
        for sibling in (h.find_next_siblings() if h else div.children):
            if not hasattr(sibling, "name") or not sibling.name:
                continue
            text = clean_text(sibling)
            if text:
                content_parts.append(text)
        content = "\n".join(content_parts)
        if not content:
            continue

        # [브랜드명] 헤더는 직전 섹션에 병합
        if _BRAND_HEADER.match(sec_name) and sections:
            prev_name, prev_content = sections[-1]
            sections[-1] = (prev_name, prev_content + "\n" + sec_name + "\n" + content)
        else:
            sections.append((sec_name, content))

    # 확인사항 (event_box_list > .mt80)
    ebl = ec.find(class_="event_box_list")
    if ebl:
        notice_div = ebl.find(class_="mt80")
        if notice_div:
            text = clean_text(notice_div)
            if text:
                sections.append(("확인사항", text))

    # ── 섹션명 정규화 ─────────────────────────
    sections = _normalize_sections(sections)

    if not sections:
        sections = [("", "")]

    # ── 행 생성: card_id × section ────────────
    rows = []
    for cid in managed:
        base = {
            "card_id":           cid,
            "company":           COMPANY,
            "card_name":         card_meta.get(cid, {}).get("card_name", "") if cid else "",
            "origin_event_code": event_num,
            "event_title":       event["event_title"],
            "event_link":        event["event_url"],
            "start_date":        start_date,
            "end_date":          end_date,
            "event_type":        event_type,
            "updated_at":        now_str(),
        }
        for sec_name, content in sections:
            rows.append({**base, "section": sec_name, "event_content": content})

    return rows


# ─────────────────────────────────────────────
# 이벤트 상세 크롤링 (import용 핵심 함수)
# ─────────────────────────────────────────────

async def crawl_events(events: list, card_meta: dict) -> list:
    """
    이벤트 상세 페이지 크롤링 + 파싱 → CSV 행 리스트 반환.
    """
    event_card_map = load_event_card_map()
    print(f"  카드HTML 역매핑: {len(event_card_map)}개 이벤트 커버")

    all_rows = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx  = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()

        try:
            for i, event in enumerate(events, 1):
                event_num = event["event_num"]
                print(f"  [{i}/{len(events)}] {event_num} | {event['event_title'][:30]}")

                try:
                    await page.goto(
                        event["event_url"],
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                    await page.wait_for_timeout(3000)
                    html = await page.content()
                except Exception as e:
                    print(f"    [실패] 로드 오류: {e}")
                    continue

                rows = parse_event_detail(html, event, card_meta, event_card_map)
                if rows:
                    all_rows.extend(rows)
                    card_ids = list(dict.fromkeys(r["card_id"] for r in rows if r["card_id"]))
                    secs     = list(dict.fromkeys(r["section"] for r in rows))
                    src = "HTML역매핑" if event_num in event_card_map else \
                          "키워드매칭" if card_ids else "전체"
                    print(f"    -> {len(rows)}행 | [{src}] 카드: {card_ids if card_ids else '전체'} | 섹션: {secs}")
                else:
                    print(f"    [경고] 파싱 결과 없음")

                await asyncio.sleep(1.5)

        except Exception as e:
            print(f"  [오류] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    return all_rows


# ─────────────────────────────────────────────
# event_id 부여
# ─────────────────────────────────────────────

def assign_event_ids(rows: list) -> list:
    """
    card_id별로 origin_event_code에 순번을 붙여 event_id 부여.
    형식: {card_id}_E{NNNN}  (예: ME4_E0001)
    같은 (card_id, origin_event_code) 행은 동일한 event_id 공유.
    """
    # card_id → {event_code → event_id} 매핑
    card_event_map: dict[str, dict[str, str]] = {}

    for row in rows:
        cid  = row["card_id"]
        code = row["origin_event_code"]
        if cid not in card_event_map:
            card_event_map[cid] = {}
        if code not in card_event_map[cid]:
            seq = len(card_event_map[cid]) + 1
            card_event_map[cid][code] = f"{cid}_E{seq:04d}"

    for row in rows:
        row["event_id"] = card_event_map[row["card_id"]][row["origin_event_code"]]

    return rows


# ─────────────────────────────────────────────
# CSV upsert
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# 단독 실행
# ─────────────────────────────────────────────

async def main():
    if not os.path.exists(EVENTS_JSON):
        print(f"[오류] {EVENTS_JSON} 없음. hd_collect_event_urls.py 먼저 실행하세요.")
        return

    with open(EVENTS_JSON, encoding="utf-8") as f:
        events = json.load(f)

    card_meta = load_card_meta()

    print("=" * 60)
    print(f"현대카드 이벤트 상세 파싱 시작 ({len(events)}개 이벤트)")
    print(f"카드 메타: {len(card_meta)}개 로드")
    print("=" * 60)

    all_rows = await crawl_events(events, card_meta)
    all_rows = assign_event_ids(all_rows)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print()
    print("=" * 60)
    print(f"[완료] {OUTPUT_CSV} -> {len(all_rows)}행")
    print(f"       이벤트 {len(events)}개 처리")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
