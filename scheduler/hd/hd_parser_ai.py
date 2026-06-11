import os
import re
import sys
import asyncio
import argparse

# parser/ 폴더를 기준으로 import 경로 확보
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

_PARSER_OUTPUT_DIR = os.path.join(_HERE, "output")

from bs4 import BeautifulSoup

from hd_parser_base import (
    CARDS_JSON, HTML_OUT_DIR, OUTPUT_DIR, COMPANY,
    INFO_FIELDS, BENEFIT_FIELDS, NOTICE_FIELDS,
    now_str, now_date, load_cards_json, upsert_csv,
)
from hd_parser_html import extract_sections_from_html, extract_notice_from_html
from hd_parser_llm import call_claude, parse_json_response, reset_token_usage, print_token_summary, INFO_SYSTEM, INFO_PROMPT
from hd_parser_benefit import parse_benefit_section


# ─────────────────────────────────────────────
# 카드 기본정보 파싱
# ─────────────────────────────────────────────
def parse_info(html: str, card_id: str, card_meta: dict) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    fee_el = soup.find(class_="box_cont_wrap")
    fee_content = ""
    if fee_el:
        lines = []
        for li in fee_el.find_all("li"):
            cls = li.get("class", [])
            txt = li.get_text(" ", strip=True)
            if "main-txt" in cls:
                lines.append(f"[주요] {txt}")
            elif "sub-txt" in cls:
                p_tags = li.find_all("p")
                direct_texts = [
                    t.strip() for t in li.find_all(string=True, recursive=False)
                    if t.strip() and not t.strip().startswith("·")
                ]
                if direct_texts:
                    for dt in direct_texts:
                        lines.append(f"  {dt}")
                if p_tags:
                    for p in p_tags:
                        p_txt = p.get_text(" ", strip=True)
                        if p_txt and not p_txt.startswith("·"):
                            lines.append(f"  {p_txt}")
                elif not direct_texts and txt:
                    lines.append(f"  {txt}")
        fee_content = "\n".join(lines)

    summary_list = []
    h4m = soup.find("ul", class_="h4_m")
    if h4m:
        for li in h4m.find_all("li"):
            txt = li.get_text(" ", strip=True)
            if txt:
                summary_list.append(txt)
    summary_raw = " / ".join(summary_list)

    h2 = soup.find("h2", class_=re.compile("h0_eb"))
    card_name_html = h2.get_text(strip=True) if h2 else card_meta.get("card_name", "")

    _info_parts = INFO_PROMPT.split("---\n\n", 1)
    _info_static = _info_parts[1] if len(_info_parts) > 1 else ""
    _info_system_cached = INFO_SYSTEM + "\n\n---\n\n" + _info_static
    _info_user = (
        f"# 입력\n"
        f"**card_id**: {card_id}\n"
        f"**card_name**: {card_name_html}\n\n"
        f"**연회비 섹션**:\n{fee_content[:2000]}\n\n"
        f"**카드 주요혜택 요약**:\n{summary_raw}"
    )
    resp = call_claude(_info_system_cached, _info_user)

    try:
        rows = parse_json_response(resp)
        info = rows[0] if rows else {}
    except Exception as e:
        print(f"    ! info JSON 파싱 실패: {e}")
        info = {}

    for f in ["annual_fee_dom_basic", "annual_fee_dom_premium",
              "annual_fee_for_basic", "annual_fee_for_premium", "min_performance"]:
        if not info.get(f) and info.get(f) != 0:
            info[f] = 0

    info["card_id"]    = card_id
    info["company"]    = COMPANY
    info["card_name"]  = info.get("card_name") or card_name_html
    info["card_type"]  = card_meta.get("card_type", "신용")
    info["image_url"]  = card_meta.get("image_url", "")
    info["link_url"]   = card_meta.get("url", "")
    info["has_transport"] = card_meta.get("has_transport", False)
    info["fee_content"]   = ""
    info["updated_at"]    = now_str()

    return info


# ─────────────────────────────────────────────
# 유의사항 파싱
# ─────────────────────────────────────────────
def parse_notice_from_sections(notice_sections: list, card_id: str) -> list:
    if not notice_sections:
        return []

    parts = []
    for s in notice_sections:
        content = s["content"].strip()
        if not content or len(content) < 10:
            continue
        parts.append(content)

    if not parts:
        return []

    notice_content = "\n\n".join(parts)

    return [{
        "notice_id":      f"{card_id}_N0001",
        "card_id":        card_id,
        "notice_content": notice_content,
        "updated_at":     now_str(),
    }]


# ─────────────────────────────────────────────
# 카드 1개 전체 파싱
# ─────────────────────────────────────────────
def process_card(card_id: str, card_meta: dict) -> tuple[dict, list, list]:
    html_path = None
    for candidate in [
        f"{HTML_OUT_DIR}/{card_id}_main.html",
        f"{HTML_OUT_DIR}/hd_{card_id}_main.html",
        f"output/html/{card_id}_main.html",
    ]:
        if os.path.exists(candidate):
            html_path = candidate
            break

    if not html_path:
        raise FileNotFoundError(f"HTML 파일 없음: {HTML_OUT_DIR}/{card_id}_main.html")

    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    print(f"  HTML 로드: {html_path} ({len(html):,}자)")

    reset_token_usage()
    import time
    t0 = time.time()

    print(f"  [1] card_info 파싱...")
    info = parse_info(html, card_id, card_meta)
    print(f"      {info.get('card_name', '?')} | 연회비: {info.get('annual_fee_for_basic', '?')}원")

    print(f"  [2] 혜택 섹션 분리...")
    sections = extract_sections_from_html(html)
    benefit_sections = [s for s in sections if not s["is_notice"]]
    print(f"      총 {len(benefit_sections)}개 섹션")
    for s in benefit_sections:
        print(f"      - [{s['group']}] > [{s['title'] or '(title없음)'}]")

    print(f"  [3] 혜택 파싱 (섹션별 Claude 호출)...")
    benefit_rows = []
    seq_ref = [1]
    for sec in benefit_sections:
        label = f"{sec['group']} > {sec['title']}" if sec['title'] else sec['group']
        print(f"      -> [{label}]")
        rows = parse_benefit_section(sec, card_id, seq_ref)
        benefit_rows.extend(rows)
        print(f"         {len(rows)}행 생성")

    info["has_cashback"] = any(
        r.get("benefit_type") in ("캐시백", "할인")
        for r in benefit_rows
    )
    print(f"      has_cashback={info['has_cashback']}")

    if not info.get("min_performance"):
        perf_mins = [
            int(r["performance_min"])
            for r in benefit_rows
            if r.get("row_type") == "주요혜택"
            and str(r.get("performance_min", "")).isdigit()
            and int(r["performance_min"]) > 0
        ]
        if perf_mins:
            info["min_performance"] = min(perf_mins)
            print(f"      min_performance 역추출: {info['min_performance']}")

    print(f"  [4] 유의사항 파싱...")
    notice_sections = extract_notice_from_html(html)
    notice_rows = parse_notice_from_sections(notice_sections, card_id)
    print(f"      {len(notice_rows)}행 생성")

    elapsed = time.time() - t0
    print(f"  소요시간: {elapsed:.1f}초")
    print_token_summary()

    return info, benefit_rows, notice_rows


# ─────────────────────────────────────────────
# CSV 저장
# ─────────────────────────────────────────────
def save_card_data(card_id: str, info: dict, benefits: list, notices: list,
                   output_dir: str = OUTPUT_DIR, prefix: str = "hyundai"):
    upsert_csv(f"{output_dir}/{prefix}_info.csv",    [info],    INFO_FIELDS)
    upsert_csv(f"{output_dir}/{prefix}_benefit.csv", benefits,  BENEFIT_FIELDS, key_col="card_id")
    upsert_csv(f"{output_dir}/{prefix}_notices.csv",  notices,   NOTICE_FIELDS,  key_col="card_id")


# ─────────────────────────────────────────────
# CLI 진입점
# ─────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="현대카드 AI 파싱")
    parser.add_argument("--card_id",    default=None,
                        help="파싱할 카드 ID (콤마 구분 가능, 예: ME4,ZROE3,XPE4)")
    parser.add_argument("--recrawl",    action="store_true", help="크롤링 후 파싱")
    parser.add_argument("--output_dir", default=_PARSER_OUTPUT_DIR)
    return parser.parse_args()


async def main():
    args  = parse_args()
    cards = load_cards_json()

    if args.card_id:
        target_ids = [cid.strip() for cid in args.card_id.split(",") if cid.strip()]
        cards = [c for c in cards if c["card_id"] in target_ids]
        found_ids = {c["card_id"] for c in cards}
        for tid in target_ids:
            if tid not in found_ids:
                print(f"[WARN] card_id '{tid}' 없음 (hd_cards.json 확인)")
        if not cards:
            print("[ERROR] 파싱할 카드 없음")
            return

    if args.recrawl:
        from hd_crawl4ai import crawl_card, BROWSER_CFG
        from crawl4ai import AsyncWebCrawler
        print(f"[재크롤링] {len(cards)}개...")
        async with AsyncWebCrawler(config=BROWSER_CFG) as crawler:
            for card in cards:
                await crawl_card(crawler, card)

    print("=" * 60)
    print(f"현대카드 AI 파싱 시작 ({len(cards)}개)")
    print("=" * 60)

    success, fail = 0, 0
    for card in cards:
        cid  = card["card_id"]
        name = card.get("card_name", cid)
        print(f"\n[{cid}] {name}")
        try:
            info, benefits, notices = process_card(cid, card)
            save_card_data(cid, info, benefits, notices, args.output_dir)
            print(f"  [완료] 혜택 {len(benefits)}행 / 유의사항 {len(notices)}행")
            success += 1
        except Exception as e:
            print(f"  [실패] {e}")
            fail += 1

    print("\n" + "=" * 60)
    print(f"완료 | 성공: {success} / 실패: {fail}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
