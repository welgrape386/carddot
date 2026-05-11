"""
saver.py - KB국민카드 크롤링 결과 CSV 저장 및 후처리

포함:
  - save_rows_to_csv  : rows를 CSV에 append 저장 (삼성카드 saver.py와 동일 인터페이스)
  - save_results      : crawl_kb_card 결과를 card_info/benefit/notices/events CSV로 저장
"""

import re
import csv
import os
from datetime import datetime

from config import (
    CARD_COMPANY, CARD_NAME_DEFAULT, CARD_PAGE_CODE,
    INFO_FIELDS, BENEFIT_FIELDS, NOTICE_FIELDS, EVENT_FIELDS,
    ON_OFF_MAP, LOCATION_MAP,
)
from classifier import (
    get_category, get_category_id, classify_benefit_type,
    classify_merchants_with_llm, filter_brands,
    extract_number, extract_min_amount, extract_max_count, extract_max_limit,
)


# ── 전역 ID 카운터 ────────────────────────────────────────────
_benefit_id_counter = 0
_notice_id_counter  = 0


# ── 공통 CSV 저장 (삼성카드 saver.py와 동일 인터페이스) ──────

def save_rows_to_csv(rows: list[dict], filename: str):
    """rows를 CSV에 append 저장 (헤더는 파일이 없을 때만 작성)"""
    if not rows:
        return
    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
    print(f"  저장 완료: {filename} ({len(rows)}행)")


def _append_csv(filepath: str, fieldnames: list, rows: list):
    """내부 저장 헬퍼 (fieldnames 명시)"""
    file_exists = os.path.isfile(filepath)
    with open(filepath, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


# ── 결제네트워크 정규화 ───────────────────────────────────────

def _normalize_network(raw: str) -> str:
    _NORMALIZE = [
        (re.compile(r"MasterCard|Mastercard", re.I), "Master"),
        (re.compile(r"\bVisa\b", re.I), "VISA"),
        (re.compile(r"\bAmex\b|American Express", re.I), "AMEX"),
        (re.compile(r"\bJcb\b", re.I), "JCB"),
        (re.compile(r"UnionPay|Union Pay", re.I), "UnionPay"),
        (re.compile(r"국내전용|\bLocal\b", re.I), "Local"),
    ]
    if not raw or not raw.strip():
        return "Local"
    parts = [p.strip() for p in re.split(r"[,/]\s*", raw) if p.strip()]
    normalized = []
    for p in parts:
        replaced = p
        for pattern, canonical in _NORMALIZE:
            if pattern.search(p):
                replaced = canonical
                break
        if replaced not in normalized:
            normalized.append(replaced)
    if "Local" in normalized:
        normalized = ["Local"] + [b for b in normalized if b != "Local"]
    return ", ".join(normalized) if normalized else "Local"


# ── 해외수수료 2종 행 분리 ────────────────────────────────────

_OVERSEAS_FEE_RE = re.compile(
    r"(국제브랜드\s*수수료|브랜드\s*수수료)\s*([\d.]+)%\s*면제"
    r"[,\s]+"
    r"(해외\s*서비스\s*수수료|서비스\s*수수료)\s*([\d.]+)%\s*면제",
    re.IGNORECASE,
)
_OVERSEAS_FEE_PLUS_RE = re.compile(
    r"(국제브랜드\s*수수료|브랜드\s*수수료)\s*([\d.]+)%"
    r"\s*\+\s*"
    r"(해외\s*서비스\s*수수료|서비스\s*수수료)\s*([\d.]+)%\s*\|?\s*면제",
    re.IGNORECASE,
)

_GROUP_LABEL_PREFIX = re.compile(
    r"^(국내\s*혜택|해외\s*혜택|Global\s*혜택|일상\s*혜택|KB\s*Pay\s*혜택)\s*"
)
_PURE_GROUP_LABEL = re.compile(
    r"^(국내\s*혜택|해외\s*혜택|Global\s*혜택|일상\s*혜택|KB\s*Pay\s*혜택)$"
)
_COND_ONLY_RE = re.compile(
    r"^(최초\s*발급|실적유예|유예기간|전월\s*이용실적이?\s*[\d,만천]+원\s*(이상|미만)(?!.*할인한도))",
    re.IGNORECASE,
)


def _split_overseas_fee(content: str, base_row: dict) -> list | None:
    for pat in (_OVERSEAS_FEE_RE, _OVERSEAS_FEE_PLUS_RE):
        m = pat.search(content)
        if m:
            r1 = dict(base_row)
            r1["value"] = m.group(2)
            r1["unit"] = "%"
            r1["benefit_type"] = "서비스"
            r1["benefit_content"] = f"국제브랜드수수료 {m.group(2)}% 면제"
            r1["benefit_summary"] = f"국제브랜드수수료 {m.group(2)}% 면제"

            r2 = dict(base_row)
            r2["benefit_id"] = str(base_row.get("benefit_id", "")) + "_2"
            r2["value"] = m.group(4)
            r2["unit"] = "%"
            r2["benefit_type"] = "서비스"
            r2["benefit_content"] = f"해외서비스수수료 {m.group(4)}% 면제"
            r2["benefit_summary"] = f"해외서비스수수료 {m.group(4)}% 면제"
            return [r1, r2]
    return None


def _postprocess_benefit_rows(rows: list) -> list:
    """
    1) 해외수수료 2종 → 2행 분리
    2) benefit_summary의 그룹 접두사 제거
    3) 전월실적 조건 설명문 → value/unit/benefit_type 정리
    4) 복합 혜택(% 2개 이상) → value/unit 공란
    """
    _SHIMUI_RE = re.compile(r"여신금융협회\s*심의필|심의필\s*제\d+")

    def _extract_title_from_content(content: str, perf: str) -> str:
        if "|" not in content:
            return ""
        first = content.split("|")[0].strip()
        if re.match(r"^[\d.]+\s*[%원]?$", first):
            return ""
        if perf and perf.strip():
            try:
                perf_int = int(float(perf))
                if perf_int >= 10000:
                    return f"{first} ({perf_int//10000}만원 이상)"
            except ValueError:
                pass
        return first

    result = []
    for r in rows:
        content = str(r.get("benefit_content", "") or "")
        summary = str(r.get("benefit_summary", "") or "")

        if _SHIMUI_RE.search(content):
            continue

        split = _split_overseas_fee(content, r)
        if split:
            result.extend(split)
            continue

        if _GROUP_LABEL_PREFIX.match(summary):
            r = dict(r)
            r["benefit_summary"] = _GROUP_LABEL_PREFIX.sub("", summary).strip()
            summary = r["benefit_summary"]

        if _GROUP_LABEL_PREFIX.match(content):
            r = dict(r)
            r["benefit_content"] = _GROUP_LABEL_PREFIX.sub("", content).strip()
            content = r["benefit_content"]

        if _PURE_GROUP_LABEL.match(summary):
            r = dict(r)
            r["benefit_summary"] = ""

        title = str(r.get("benefit_title", "") or "")
        if title in ("상세혜택", "서비스 요약") and "|" in content:
            improved = _extract_title_from_content(content, str(r.get("performance_level", "") or ""))
            if improved:
                r = dict(r)
                r["benefit_title"] = improved[:80]

        if "/" in content and not r.get("value"):
            r = dict(r)
            r["benefit_content"] = content.split("/")[0].strip()
            content = r["benefit_content"]

        if _COND_ONLY_RE.search(content):
            r = dict(r)
            r["value"] = ""
            r["unit"] = ""
            r["benefit_type"] = "서비스"

        content_now = str(r.get("benefit_content", "") or "")
        summary_now = str(r.get("benefit_summary", "") or "")
        if (len(re.findall(r"\d+(?:\.\d+)?%", content_now)) >= 2 or
                len(re.findall(r"\d+(?:\.\d+)?%", summary_now)) >= 2):
            r = dict(r)
            r["value"] = ""
            r["unit"] = ""

        result.append(r)
    return result


# ── 메인 저장 함수 ────────────────────────────────────────────

def save_results(data: dict):
    """
    crawl_kb_card() 결과를 4개 CSV 파일에 저장.
      - card_info.csv
      - card_benefit.csv  (혜택 + 유의사항 + 연회비)
      - card_notices.csv  (이용전확인사항)
      - card_events.csv   (KB카드 미지원, 헤더만)
    """
    global _benefit_id_counter, _notice_id_counter

    card_code   = data["card_code"]
    target_url  = data["target_url"]
    info        = data["card_info"]
    tab_rows    = data["tab_rows"]
    fee_detail  = data["fee_detail"]
    notice_rows = data["notice_rows"]
    crawled_at  = data["crawled_at"]
    card_name   = data.get("card_name", CARD_NAME_DEFAULT)

    # ── card_info.csv ─────────────────────────────────────────
    is_transport = "True" if info.get("후불교통") else "False"
    결제네트워크 = _normalize_network(info.get("결제네트워크브랜드", ""))
    국내해외겸용 = "True" if any(
        b in 결제네트워크 for b in ["VISA", "Master", "UnionPay", "AMEX", "JCB"]
    ) else "False"

    카드대표혜택 = info.get("main_benefit", "")
    if not 카드대표혜택:
        카드대표혜택 = " / ".join(
            r.get("benefit_summary", r.get("혜택명", "")) for r in tab_rows
            if r.get("탭") in ("주요혜택", "상세혜택") and r.get("benefit_summary", r.get("혜택명", ""))
        )[:200]
    if not 카드대표혜택:
        카드대표혜택 = info.get("카드설명", "")

    실적_구간들 = sorted(set(
        int(n) for r in tab_rows
        if r.get("전월실적")
        for n in [extract_number(str(r.get("전월실적")))]
        if n and int(n) > 0
    ))
    기본전월실적 = str(실적_구간들[0]) if len(실적_구간들) >= 1 else ""
    추가전월실적 = str(실적_구간들[1]) if len(실적_구간들) >= 2 else ""

    _CASHBACK_KW = re.compile(
        r"캐시백|cashback|cash\s*back|연회비\s*(환급|반환|적립|면제|지원)", re.IGNORECASE
    )
    cashback_flag = any(
        _CASHBACK_KW.search(" ".join(str(v) for v in r.values()))
        for r in [*fee_detail, *tab_rows, info]
        if isinstance(r, dict)
    )

    fee_dom  = _fee_to_number(info.get("국내전용_일반", ""))
    fee_for  = _fee_to_number(info.get("해외겸용_일반", ""))
    fee_domp = _fee_to_number(info.get("국내전용_프리미엄", ""))
    fee_forp = _fee_to_number(info.get("해외겸용_프리미엄", ""))

    _append_csv("card_info.csv", INFO_FIELDS, [{
        "card_id":               card_code,
        "company":               CARD_COMPANY,
        "card_name":             card_name,
        "card_type":             info.get("card_type", "신용"),
        "network":               결제네트워크,
        "is_domestic_foreign":   국내해외겸용,
        "has_transport":         is_transport,
        "annual_fee_dom_basic":  fee_dom or 0,
        "annual_fee_dom_premium":fee_domp or 0,
        "annual_fee_for_basic":  fee_for or 0,
        "annual_fee_for_premium":fee_forp or 0,
        "annual_fee_notes":      info.get("연회비_비고", ""),
        "min_performance":       기본전월실적,
        "extra_performance":     추가전월실적,
        "summary":               카드대표혜택,
        "image_url":             info.get("image_url", ""),
        "link_url":              target_url,
        "has_cashback":          "TRUE" if cashback_flag else "FALSE",
        "updated_at":            crawled_at,
    }])
    print("[OK] card_info.csv")

    # ── card_benefit.csv ──────────────────────────────────────
    detail_out = []
    row_id = _benefit_id_counter + 1

    for r in tab_rows:
        if r.get("탭") == "확인사항":
            detail_out.append({
                "benefit_id":        row_id,
                "card_id":           card_code,
                "row_type":          "유의사항",
                "benefit_group":     "확인사항",
                "benefit_title":     r.get("benefit_title", ""),
                "benefit_summary":   r.get("benefit_summary", ""),
                "category": "", "category_id": "", "on_offline": "", "region": "",
                "benefit_type": "", "value": "", "unit": "",
                "target_merchants": "", "excluded_merchants": "",
                "min_amount": "",
                "performance_level": "", "max_count": "", "max_limit": "",
                "benefit_content":   r.get("content", ""),
                "updated_at":        crawled_at,
            })
            row_id += 1
            continue

        소분류 = r.get("benefit_title") or r.get("sub_category", "")
        내용   = r.get("content", "")
        혜택수치 = r.get("benefit_value", "")
        혜택단위 = r.get("benefit_unit", "")
        대상가맹점 = (r.get("적용가맹점", "") or "").strip()
        제외가맹점 = (r.get("excluded_merchants", "") or "").strip()
        요약 = (r.get("benefit_summary") or "").strip()

        cat    = get_category(소분류, 내용)
        on_off = ON_OFF_MAP.get(cat, "Both")
        loc    = LOCATION_MAP.get(cat, "국내")
        유형   = classify_benefit_type(소분류, 내용, 혜택단위)

        detail_out.append({
            "benefit_id":        row_id,
            "card_id":           card_code,
            "row_type":          "혜택",
            "benefit_group":     r.get("benefit_group", ""),
            "benefit_title":     r.get("benefit_title", ""),
            "benefit_summary":   요약[:120],
            "category":          cat,
            "category_id":       get_category_id(cat),
            "on_offline":        on_off,
            "region":            loc,
            "benefit_type":      유형,
            "value":             혜택수치,
            "unit":              혜택단위,
            "target_merchants":  대상가맹점,
            "excluded_merchants":제외가맹점,
            "min_amount":        extract_min_amount(내용),
            "performance_level": extract_number(r.get("전월실적", "")),
            "max_count":         extract_max_count(내용),
            "max_limit": (
                r.get("최대한도", "") or
                (lambda c: (
                    extract_number(m.group(1) + "원")
                    if (m := re.search(
                        r"(?:월\s*)?(?:할인한도|한도)\s*[:|]\s*월?\s*([\d,만천백]+)원",
                        c or ""
                    )) else ""
                ))(내용)
            ),
            "benefit_content":   내용,
            "updated_at":        crawled_at,
        })
        row_id += 1

    for r in fee_detail:
        수치 = r.get("benefit_value", "")
        단위 = r.get("benefit_unit", "")
        내용_txt = r.get("content", "")
        소제목 = r.get("benefit_title") or r.get("혜택명", "")

        row_type = "연회비" if (수치 or 단위) else "유의사항"
        detail_out.append({
            "benefit_id":        row_id,
            "card_id":           card_code,
            "row_type":          row_type,
            "benefit_group":     "연회비",
            "benefit_title":     소제목[:60],
            "benefit_summary":   "",
            "category": "", "category_id": "", "on_offline": "", "region": "",
            "benefit_type":      "",
            "value":             "", "unit": "",
            "target_merchants":  "", "excluded_merchants": "",
            "min_amount":        "",
            "performance_level": "", "max_count": "", "max_limit": "",
            "benefit_content":   내용_txt,
            "updated_at":        crawled_at,
        })
        row_id += 1

    _benefit_id_counter += len(detail_out)

    # LLM 브랜드 추출 + 카테고리 분류
    benefit_rows = [(i, r) for i, r in enumerate(detail_out) if r["row_type"] == "혜택"]

    from config import ANTHROPIC_API_KEY
    if benefit_rows and ANTHROPIC_API_KEY:
        print(f"  [LLM] 브랜드 추출 + 카테고리 분류 ({len(benefit_rows)}행)")
        llm_input = "\n".join(
            f"{idx}: {r.get('benefit_content', r.get('혜택명', ''))[:200]}"
            for idx, (_, r) in enumerate(benefit_rows)
        )
        llm_result = classify_merchants_with_llm(llm_input)

        for idx, (_, row) in enumerate(benefit_rows):
            entry = llm_result.get(str(idx))
            if not entry:
                continue
            brands = [b.strip() for b in entry.get("brands", []) if b.strip()]
            row["target_merchants"] = ", ".join(brands)
            llm_cat = entry.get("category", "").strip()
            if llm_cat and not row.get("category"):
                row["category"] = llm_cat
                row["category_id"] = get_category_id(llm_cat)
        print("  [LLM] 완료")
    elif benefit_rows:
        print("  [LLM 스킵] ANTHROPIC_API_KEY 없음 → 화이트리스트 fallback")
        for _, row in benefit_rows:
            raw = (row.get("target_merchants") or "").strip()
            if raw:
                row["target_merchants"] = ", ".join(
                    filter_brands([m.strip() for m in raw.split(",") if m.strip()])
                )
            if not row.get("target_merchants"):
                content = (row.get("benefit_content") or "").strip()
                if content and not re.search(r"이동통신.{0,10}보험|보험.{0,10}이동통신|통신/보험", content):
                    cut = re.sub(
                        r'\s*\d[\d,.]*\s*(?:만원\s*이상|%|원\s*할인|이상\s*시|회\s*할인).*$', '', content
                    ).strip()
                    cut = re.sub(r'^\[.*?\]\s*', '', cut).strip()
                    if "|" in cut:
                        parts_pipe = [p.strip() for p in cut.split("|") if p.strip()]
                        cut = ", ".join(parts_pipe[1:]) if len(parts_pipe) > 1 else parts_pipe[0]
                    candidates = [p.strip() for p in re.split(r'[,，/]', cut) if p.strip()]
                    candidates = [p for p in candidates if not p.endswith(('업종', '매장', '가맹점', '요금', '보험료'))]
                    found = filter_brands(candidates)
                    if found:
                        row["target_merchants"] = ", ".join(found)

    detail_out = _postprocess_benefit_rows(detail_out)

    # ID 재정비
    base_id = _benefit_id_counter - len(detail_out) + 1
    for i, row in enumerate(detail_out):
        row["benefit_id"] = base_id + i

    _append_csv("card_benefit.csv", BENEFIT_FIELDS, detail_out)
    혜택수 = sum(1 for r in detail_out if r["row_type"] == "혜택")
    유의사항수 = sum(1 for r in detail_out if r["row_type"] == "유의사항")
    연회비수 = sum(1 for r in detail_out if r["row_type"] == "연회비")
    print(f"[OK] card_benefit.csv ({len(detail_out)}행: 혜택 {혜택수}, 유의사항 {유의사항수}, 연회비 {연회비수})")

    # ── card_notices.csv ──────────────────────────────────────
    _SUB_NORMALIZE = {
        "이용 전 확인사항": "이용전확인사항",
        "이용전 확인사항":  "이용전확인사항",
        "이용전확인 사항":  "이용전확인사항",
        "이용 전확인사항":  "이용전확인사항",
    }

    notice_out = []
    nid = _notice_id_counter + 1
    for 분류, 소분류, 내용 in notice_rows:
        sub = _SUB_NORMALIZE.get((소분류 or "").strip(), (소분류 or "").strip())
        notice_out.append({
            "notice_id":       nid,
            "card_id":         card_code,
            "notice_category": 분류,
            "sub_category":    sub,
            "notice_content":  내용,
            "updated_at":      crawled_at,
        })
        nid += 1
    _notice_id_counter += len(notice_out)
    _append_csv("card_notices.csv", NOTICE_FIELDS, notice_out)
    print(f"[OK] card_notices.csv ({len(notice_out)}행)")

    # ── card_events.csv (KB카드 미지원) ───────────────────────
    _append_csv("card_events.csv", EVENT_FIELDS, [])
    print("[OK] card_events.csv (KB카드 이벤트 없음)")

    # ── 요약 출력 ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f" {CARD_COMPANY} | {card_name} ({card_code})")
    print(f" 결제네트워크 : {결제네트워크}")
    print(f" 후불교통     : {is_transport}")
    print(f" 연회비 국내  : {fee_dom or 0}원")
    print(f" 연회비 해외  : {fee_for or 0}원")
    print(f" benefit      : 혜택 {혜택수}행 / 유의사항 {유의사항수}행 / 연회비 {연회비수}행")
    print(f" notices      : {len(notice_out)}행")
    print("=" * 60)


def _fee_to_number(s: str) -> str:
    if not s or s.strip() in ("-", ""):
        return ""
    s_clean = re.sub(r"\([^)]*\)", "", s).strip()
    total = 0
    for val, unit in re.findall(r"(\d+)(만|천|백)", s_clean):
        if unit == "만":   total += int(val) * 10000
        elif unit == "천": total += int(val) * 1000
        elif unit == "백": total += int(val) * 100
    if total:
        return str(total)
    m = re.search(r"[\d,]+", s_clean)
    return m.group(0).replace(",", "") if m else ""
