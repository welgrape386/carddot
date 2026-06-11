import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from bs4 import BeautifulSoup

from kb_parser_base import (
    CARDS_JSON, OUTPUT_DIR, COMPANY,
    INFO_FIELDS, BENEFIT_FIELDS, NOTICE_FIELDS,
    HTML_OUT_DIR, now_str,
    upsert_csv, reset_token_usage, print_token_summary, _token_usage,
)
from kb_parser_html import extract_sections_from_kb_html, extract_notice_from_kb_html
from kb_parser_benefit import parse_info, parse_benefit_section

_PARSER_OUTPUT_DIR = os.path.join(_HERE, "output")


# ─────────────────────────────────────────────
# 카드 1개 전체 파싱
# ─────────────────────────────────────────────
def process_card(card_id: str, card_meta: dict,
                 benefit_only: bool = False,
                 info_only: bool = False,
                 **kwargs) -> tuple:
    html_path = None
    for candidate in [
        os.path.join(HTML_OUT_DIR, f"{card_id}_main.html"),
        os.path.join(HTML_OUT_DIR, f"kb_{card_id}_main.html"),
    ]:
        if os.path.exists(candidate):
            html_path = candidate
            break

    if not html_path:
        raise FileNotFoundError(f"HTML 없음: {card_id}")

    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    print(f"  [HTML] HTML 로드: {html_path} ({len(html):,}자)")

    reset_token_usage()
    import time; t0 = time.time()

    if benefit_only:
        info = {"card_id": card_id, "company": COMPANY,
                "card_name": card_meta.get("card_name", card_id),
                "card_type": card_meta.get("card_type", "신용"),
                "updated_at": now_str()}
        print("  [1] card_info 스킵 (--benefit_only)")
    else:
        print("  [1] card_info 파싱...")
        info = parse_info(html, card_id, card_meta)
        print(f"      {info.get('card_name','?')} | 연회비: {info.get('annual_fee_for_basic','?')}원")

    if kwargs.get("notice_only"):
        print("  [1/3/4] info/benefit 스킵 (--notice_only)")
        notice_sections = extract_notice_from_kb_html(html)
        notice_rows = []
        if notice_sections:
            content = "\n\n".join(s["content"] for s in notice_sections)
            notice_rows = [{"notice_id": f"{card_id}_N0001", "card_id": card_id,
                            "notice_content": content, "updated_at": now_str()}]
        print(f"      {len(notice_rows)}행 생성")
        elapsed = time.time() - t0
        print(f"  [TIME]  {elapsed:.1f}초")
        reset_token_usage()
        return {"card_id": card_id}, [], notice_rows

    if info_only:
        print("  [2~4] 혜택/유의사항 스킵 (--info_only)")
        elapsed = time.time() - t0
        print(f"  [TIME]  {elapsed:.1f}초")
        print_token_summary()
        return info, [], []

    print("  [2] 혜택 섹션 분리...")
    sections = extract_sections_from_kb_html(html)
    print(f"      총 {len(sections)}개 섹션")
    for s in sections:
        print(f"      - [{s['group']}] > {s['title'][:40]}")

    print("  [3] 혜택 파싱...")
    benefit_rows, seq_ref = [], [1]
    for sec in sections:
        label = f"{sec['group']} > {sec['title'][:30]}"
        print(f"      -> [{label}]")
        rows = parse_benefit_section(sec, card_id, seq_ref)
        benefit_rows.extend(rows)
        print(f"         {len(rows)}행 생성")

    info["has_cashback"] = any(r.get("benefit_type") in ("캐시백","할인") for r in benefit_rows)

    if benefit_only:
        notice_rows = []
        print("  [4] 유의사항 스킵 (--benefit_only)")
    else:
        print("  [4] 유의사항 파싱...")
        notice_sections = extract_notice_from_kb_html(html)
        notice_rows = []
        if notice_sections:
            content = "\n\n".join(s["content"] for s in notice_sections)
            notice_rows = [{"notice_id": f"{card_id}_N0001", "card_id": card_id,
                            "notice_content": content, "updated_at": now_str()}]
        print(f"      {len(notice_rows)}행 생성")

    perf_mins = [
        int(r["performance_min"]) for r in benefit_rows
        if str(r.get("performance_min", "")).isdigit() and int(r["performance_min"]) > 0
    ]
    if perf_mins:
        info["min_performance"] = min(perf_mins)

    elapsed = time.time() - t0
    print(f"  [TIME]  {elapsed:.1f}초")
    print_token_summary()

    return info, benefit_rows, notice_rows


# ─────────────────────────────────────────────
# CSV 저장
# ─────────────────────────────────────────────
def save_card_data(card_id, info, benefits, notices,
                   output_dir=None, prefix="kb",
                   benefit_only: bool = False,
                   info_only: bool = False,
                   notice_only: bool = False):
    if output_dir is None:
        output_dir = _PARSER_OUTPUT_DIR
    if not benefit_only and not notice_only:
        upsert_csv(os.path.join(output_dir, f"{prefix}_info.csv"),   [info],   INFO_FIELDS)
    if not benefit_only and not info_only:
        upsert_csv(os.path.join(output_dir, f"{prefix}_notices.csv"), notices,  NOTICE_FIELDS, key_col="card_id")
    if not info_only and not notice_only:
        upsert_csv(os.path.join(output_dir, f"{prefix}_benefit.csv"), benefits, BENEFIT_FIELDS, key_col="card_id")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="KB국민카드 AI 파싱")
    p.add_argument("--card_id",      default=None)
    p.add_argument("--output_dir",   default=_PARSER_OUTPUT_DIR)
    p.add_argument("--benefit_only", action="store_true")
    p.add_argument("--info_only",    action="store_true")
    p.add_argument("--notice_only",  action="store_true")
    return p.parse_args()


def main():
    args = parse_args()

    with open(CARDS_JSON, encoding="utf-8") as f:
        cards = json.load(f)

    if args.card_id:
        target_ids = [c.strip() for c in args.card_id.split(",")]
        cards = [c for c in cards if c["card_id"] in target_ids]
        if not cards:
            print(f"[ERR] card_id '{args.card_id}' 없음")
            return

    print("=" * 60)
    print(f"KB국민카드 AI 파싱 시작 ({len(cards)}개)")
    print("=" * 60)

    import time as _time
    success, fail = 0, 0
    total_cost = 0.0
    t_total = _time.time()

    for card in cards:
        cid  = card["card_id"]
        name = card.get("card_name", cid)
        print(f"\n[{cid}] {name}")
        try:
            info, benefits, notices = process_card(
                cid, card,
                benefit_only=args.benefit_only,
                info_only=args.info_only,
                notice_only=args.notice_only,
            )
            save_card_data(
                cid, info, benefits, notices, args.output_dir,
                benefit_only=args.benefit_only,
                info_only=args.info_only,
                notice_only=args.notice_only,
            )
            i  = _token_usage["input"]
            o  = _token_usage["output"]
            cw = _token_usage["cache_write"]
            cr = _token_usage["cache_read"]
            card_cost = (i*0.0000008) + (o*0.000004) + (cw*0.000001) + (cr*0.00000008)
            total_cost += card_cost
            elapsed = _time.time() - t_total
            print(f"  [OK] 완료 | 혜택 {len(benefits)}행 | ${card_cost:.4f} | 누적 ${total_cost:.4f} ({elapsed:.0f}초)")
            success += 1
        except Exception as e:
            print(f"  [ERR] 실패: {e}")
            fail += 1

    total_elapsed = _time.time() - t_total
    print("\n" + "=" * 60)
    print(f"완료 | 성공: {success} / 실패: {fail}")
    print(f"총 소요시간: {total_elapsed:.1f}초  |  총 비용: ${total_cost:.4f} ({total_cost*1400:.0f}원)")
    print("=" * 60)


if __name__ == "__main__":
    main()
