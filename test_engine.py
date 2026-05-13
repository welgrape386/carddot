"""
카드 혜택 비교 알고리즘 (benefit_engine.py)
───────────────────────────────────────────
카드 ID를 넣으면 카테고리별 전체 혜택 행을 반환한다.

사용법:
    engine = BenefitEngine("samsung_benefit.csv", "samsung_info.csv")
    benefits = engine.get_card_benefits("AAP1731")
    print(benefits)
"""

import re
import pandas as pd
from typing import Optional


# ──────────────────────────────────────────────
# 필터링 기준
# ──────────────────────────────────────────────

SKIP_TITLES = {
    "이용조건", "대상점", "서비스안내", "서비스 안내", "할인기준", "적립기준",
    "할인 제외 대상", "적립 제외 대상", "마일리지 적립 제외 대상", "캐시백 제외 대상",
    "캐시백기준", "제공기준", "대상업종", "이용방법", "알아두면 유용한 정보",
    "전월 이용금액대별 할인율 및 통합 월 할인한도",
    "Q. 전월 이용금액 채울 때 기억할 점은?",
    "전월 이용금액 산정기준", "전월 이용금액 산정 기준", "전월 이용금액 기준",
    "모든 서비스 공통 제외", "국제브랜드사 서비스 공통사항 안내", "국내 브랜드사 서비스 공통사항 안내",
    "서비스별 월 통합 적립한도", "월 통합 적립 한도(일상 생활비 적립 서비스)",
    "서비스 적용 기준", "캐시백 적용 기준",
    "국내·해외 이용 더하기 서비스 유의사항", "해외 이용 수수료 빼기 서비스, 해외 이용 더하기 서비스 유의사항",
    "해외 가맹점 이용 할인 프로모션 공통사항",
    "국제 브랜드 수수료(1%)/해외 서비스 수수료(0.2%) 면제",
    "해외 ATM 이용 인출 수수료 및 국제브랜드 수수료 면제",
    "해외 ATM 이용 인출 수수료(건당 $3) 및 국제 브랜드 수수료(1%) 면제",
}

SKIP_TITLE_KEYWORDS = ["유의사항", "공통사항", "제외 대상", "산정기준", "산정 기준"]

CATEGORY_ALIAS = {
    "커피제과/카페/베이커리": "커피/카페/베이커리",
    "커피제과": "커피/카페/베이커리",
}


# ──────────────────────────────────────────────
# 포인트/마일리지 환산 상수
# ──────────────────────────────────────────────

POINT_RATE: dict[str, float] = {
    "포인트": 1.0,   # 1포인트 = 1원
    "마일리지": 25.0, # 1마일 ≈ 25원 (업계 평균)
}


# ──────────────────────────────────────────────
# benefit_value 파싱
# ──────────────────────────────────────────────

VALUE_PATTERNS = [
    (r"최대\s*([\d,]+(?:\.\d+)?)\s*(%|원|포인트)", 1, 2),
    (r"([\d,]+(?:\.\d+)?)\s*(%)\s*(?:할인|적립|캐시백|포인트)", 1, 2),
    (r"([\d,]+)\s*(원)\s*(?:할인|적립|캐시백)", 1, 2),
    (r"([\d,]+(?:\.\d+)?)\s*(%)", 1, 2),
    (r"([\d,]+)\s*(원)", 1, 2),
]


def _parse_value(row: pd.Series) -> tuple[float, str]:
    raw_val  = row.get("benefit_value", "")
    raw_unit = str(row.get("benefit_unit") or "").strip()

    if pd.notna(raw_val) and str(raw_val).strip() not in ("", "nan"):
        try:
            return float(str(raw_val).replace(",", "")), raw_unit
        except ValueError:
            pass

    content = str(row.get("benefit_content") or "")
    for pattern, vg, ug in VALUE_PATTERNS:
        m = re.search(pattern, content)
        if m:
            try:
                return float(m.group(vg).replace(",", "")), m.group(ug)
            except (ValueError, IndexError):
                continue

    return 0.0, raw_unit


# ──────────────────────────────────────────────
# 실질할인율 환산
# ──────────────────────────────────────────────

# 2순위: benefit_content에서 "N원(당/이상) M원/포인트" 패턴 파싱
_CONTENT_RATIO_PATTERNS = [
    # "1만원당 100원", "1,000원당 10포인트"
    (r"([\d,]+)\s*원\s*당\s*([\d,]+)\s*(?:원|포인트)", 2, 1),
    # "3만원 이상 결제 시 3,000원 할인"
    (r"([\d,]+)\s*원\s*이상.*?([\d,]+)\s*원\s*(?:할인|캐시백|적립)", 2, 1),
    # "30,000원 결제 시 3,000원"
    (r"([\d,]+)\s*원\s*결제\s*시\s*([\d,]+)\s*원", 2, 1),
]

def _to_float(s: str) -> float:
    """콤마 제거 후 float 변환. 실패 시 0.0 반환."""
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0

def _get_performance(row: pd.Series) -> float:
    """
    performance_min → performance_max 순으로 양수값 반환.
    없으면 0.0.
    """
    for col in ("performance_min", "performance_max"):
        v = _to_float(row.get(col, 0))
        if v > 0:
            return v
    return 0.0

def _clean_unit(raw) -> str:
    """nan 문자열·None·공백을 모두 빈 문자열로 정규화."""
    s = str(raw or "").strip()
    return "" if s in ("nan", "None") else s

def _calc_effective_rate(row: pd.Series) -> tuple[Optional[float], str]:
    """
    실질할인율(%)과 환산근거 문자열을 반환.

    반환값:
        (rate, basis)
        rate  : float(%) 또는 None(환산불가)
        basis : 어떤 방법으로 계산됐는지 설명 문자열
    """
    value = row["_value"]
    unit  = _clean_unit(row.get("benefit_unit")) or _clean_unit(row.get("_unit"))

    # ── 1순위: 단위가 % ─────────────────────────────────────────
    if unit == "%":
        return value, "직접%"

    # ── 2순위: benefit_content 텍스트에서 비율 파싱 ───────────────
    content = str(row.get("benefit_content") or "")
    for pattern, mg, dg in _CONTENT_RATIO_PATTERNS:
        m = re.search(pattern, content.replace(" ", ""))
        if m:
            numerator   = _to_float(m.group(mg))   # 혜택 금액
            denominator = _to_float(m.group(dg))   # 기준 금액
            if denominator > 0 and numerator > 0:
                rate = round(numerator / denominator * 100, 2)
                return rate, f"콘텐츠파싱({int(numerator)}원/{int(denominator)}원)"

    # ── 3순위: max_limit ÷ performance ────────────────────────────
    max_limit = _to_float(row.get("max_limit", 0))
    perf      = _get_performance(row)

    if max_limit > 0 and perf > 0:
        rate  = round(max_limit / perf * 100, 2)
        basis = (
            f"max_limit({int(max_limit)}원)÷"
            f"{'performance_min' if _to_float(row.get('performance_min', 0)) > 0 else 'performance_max'}"
            f"({int(perf)}원)"
        )
        return rate, basis

    # ── 4순위: 포인트/마일리지 환산율 적용 ───────────────────────
    if unit in POINT_RATE and value > 0 and perf > 0:
        krw_per_unit = POINT_RATE[unit]
        krw_value    = value * krw_per_unit
        rate         = round(krw_value / perf * 100, 2)
        basis        = (
            f"{unit}×{krw_per_unit}원 가정, "
            f"{int(value)}{unit}÷{int(perf)}원"
        )
        return rate, basis

    # ── 환산 불가 ─────────────────────────────────────────────────
    return None, "환산불가"


def _fmt_rate(rate: Optional[float]) -> str:
    if rate is None:
        return "-"
    return f"{rate:g}%"


# ──────────────────────────────────────────────
# 표시값 포맷 (기존 유지)
# ──────────────────────────────────────────────

def _fmt_value(value: float, unit: str) -> str:
    unit = _clean_unit(unit)
    if value == 0 or not unit:
        return "-"
    if unit == "%":
        return f"{value:g}%"
    if unit in ("원", "포인트", "마일리지"):
        return f"{int(value):,}{unit}"
    return f"{value:g}{unit}"


def _fmt_limit(max_limit, unit: str) -> str:
    try:
        v = float(str(max_limit).replace(",", "")) if pd.notna(max_limit) else 0
    except (ValueError, TypeError):
        v = 0
    if v <= 0:
        return "제한없음"
    u = str(unit or "").strip()
    u = u if u and u != "nan" else "원"
    return f"{int(v):,}{u}/월"


def _fmt_performance(row: pd.Series) -> str:
    level = str(row.get("performance_level") or "").strip()
    if level and level not in ("nan", ""):
        return level

    def to_int(v) -> Optional[int]:
        try:
            f = float(str(v).replace(",", ""))
            return int(f) if f > 0 else None
        except (ValueError, TypeError):
            return None

    mn = to_int(row.get("performance_min"))
    mx = to_int(row.get("performance_max"))

    if mn and mx:
        return f"전월 {mn:,}원 ~ {mx:,}원"
    if mn:
        return f"전월 {mn:,}원 이상"
    if mx:
        return f"전월 {mx:,}원 이하"
    return "제한없음"


def _fmt_merchants(row: pd.Series) -> str:
    raw = str(row.get("target_merchants") or "").strip()

    if not raw or raw == "nan":
        content = str(row.get("benefit_content") or "")
        m = re.search(r"(?:할인|적립)\s*대상\s*:\s*([^\|\n]+)", content)
        return m.group(1).strip() if m else "-"

    GENERIC = {"커피", "배달", "페이", "간편결제", "스트리밍",
               "해외", "대중교통", "택시", "온라인", "슈퍼마켓"}
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    specific = [p for p in parts if p not in GENERIC]
    return ", ".join(specific) if specific else ", ".join(parts)


# ──────────────────────────────────────────────
# 핵심 엔진
# ──────────────────────────────────────────────

class BenefitEngine:

    def __init__(self, benefit_csv: str, info_csv: str):
        self.raw_benefits = pd.read_csv(benefit_csv, dtype=str)
        self.raw_info     = pd.read_csv(info_csv,    dtype=str)
        self.benefits     = self._preprocess()

    def _preprocess(self) -> pd.DataFrame:
        df = self.raw_benefits.copy()

        df = df[df["row_type"].str.strip() == "상세혜택"].copy()

        has_category = df["category"].notna() & (df["category"].str.strip() != "") & (df["category"].str.strip() != "nan")
        has_type     = df["benefit_type"].notna() & (df["benefit_type"].str.strip() != "") & (df["benefit_type"].str.strip() != "nan")
        df = df[has_category | has_type].copy()

        EXCLUDE_KEYWORDS = ["제외 대상", "공통 제외", "추가 제외"]
        df = df[~df["benefit_title"].str.contains("|".join(EXCLUDE_KEYWORDS), na=False)].copy()

        parsed        = df.apply(_parse_value, axis=1)
        df["_value"]  = [p[0] for p in parsed]
        df["_unit"]   = [p[1] for p in parsed]

        # benefit_unit이 비어있거나 "nan" 문자열이면 _unit으로 보완
        mask = (
            df["benefit_unit"].isna() |
            (df["benefit_unit"].str.strip() == "") |
            (df["benefit_unit"].str.strip() == "nan")
        )
        df.loc[mask, "benefit_unit"] = df.loc[mask, "_unit"]

        df = df[df["_value"] > 0].copy()
        df = df[df["category"].notna() & (df["category"].str.strip() != "") & (df["category"].str.strip() != "nan")].copy()

        # 실질할인율 & 환산근거 컬럼 추가
        effective = df.apply(_calc_effective_rate, axis=1)
        df["_eff_rate"]  = [e[0] for e in effective]
        df["_eff_basis"] = [e[1] for e in effective]

        rows = []
        for _, row in df.iterrows():
            cats = [CATEGORY_ALIAS.get(c.strip(), c.strip())
                    for c in str(row["category"]).split(",")]
            for cat in cats:
                r = row.copy()
                r["category"] = cat.strip()
                rows.append(r)

        df_result = pd.DataFrame(rows).drop_duplicates(
            subset=["card_id", "category", "benefit_type", "benefit_value",
                    "benefit_unit", "target_merchants", "performance_level", "max_limit"]
        ).reset_index(drop=True)

        return df_result

    def get_card_benefits(self, card_id: str) -> pd.DataFrame:
        """
        카드 ID를 받아 카테고리별 전체 혜택을 DataFrame으로 반환.

        반환 컬럼:
            카테고리 | 혜택 종류 | 적용 가맹점/혜택 내용 | 할인율 | 실질할인율(%) | 환산근거 | 월 최대 | 이용 조건
        """
        df = self.benefits[self.benefits["card_id"] == card_id].copy()

        if df.empty:
            raise ValueError(f"카드 ID '{card_id}' 에 해당하는 혜택 데이터가 없습니다.")

        result_rows = []
        for _, row in df.iterrows():
            merchants = _fmt_merchants(row)
            if merchants == "-":
                merchants = "전 가맹점"

            result_rows.append({
                "카테고리":      row["category"],
                "혜택 종류":     _clean_unit(row.get("benefit_type")),
                "적용 가맹점":   merchants if merchants != "전 가맹점" else "-",
                "할인율":        _fmt_value(row["_value"], str(row.get("benefit_unit") or row["_unit"])),
                "실질할인율(%)": _fmt_rate(row["_eff_rate"]),
                "환산근거":      row["_eff_basis"],
                "월 최대":       _fmt_limit(row.get("max_limit"), str(row.get("max_limit_unit") or "")),
                "이용 조건":     _fmt_performance(row),
                "혜택 내용":     str(row.get("benefit_content") or "").strip(),
            })

        result = pd.DataFrame(result_rows)
        result = result.sort_values("카테고리").reset_index(drop=True)
        return result

    def get_card_info(self, card_id: str) -> Optional[pd.Series]:
        rows = self.raw_info[self.raw_info["card_id"] == card_id]
        return rows.iloc[0] if not rows.empty else None

    def list_cards(self) -> pd.DataFrame:
        cols = ["card_id", "company", "card_name", "card_type",
                "annual_fee_dom_basic", "min_performance"]
        return self.raw_info[[c for c in cols if c in self.raw_info.columns]].copy()