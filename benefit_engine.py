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

# 안내/제외/기준 설명 행 — 실제 혜택이 아닌 것들
SKIP_TITLES = {
    # 삼성
    "이용조건", "대상점", "서비스안내", "서비스 안내", "할인기준", "적립기준",
    "할인 제외 대상", "적립 제외 대상", "마일리지 적립 제외 대상", "캐시백 제외 대상",
    "캐시백기준", "제공기준", "대상업종", "이용방법", "알아두면 유용한 정보",
    "전월 이용금액대별 할인율 및 통합 월 할인한도",
    "Q. 전월 이용금액 채울 때 기억할 점은?",
    # 신한
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

# benefit_title에 이 문자열이 포함되면 제외
SKIP_TITLE_KEYWORDS = ["유의사항", "공통사항", "제외 대상", "산정기준", "산정 기준"]

# 카테고리 표기 통일 (삼성 ↔ 신한 차이)
CATEGORY_ALIAS = {
    "커피제과/카페/베이커리": "커피/카페/베이커리",
    "커피제과": "커피/카페/베이커리",
}

# ──────────────────────────────────────────────
# 실질할인율 환산 로직
# ──────────────────────────────────────────────

POINT_RATE = {
    "포인트": 1.0,    # 1포인트 = 1원
    "마일리지": 20.0, # 1마일 ≈ 20원 (업계 평균)
}

# 카테고리별 월 평균 지출 기준 금액 (performance 없을 때 fallback)
CATEGORY_BASE_AMOUNT: dict[str, float] = {
    "커피/카페/베이커리":    30_000,
    "외식":               120_000,
    "배달":                60_000,
    "편의점":              30_000,
    "슈퍼마켓/생활잡화":    80_000,
    "온라인쇼핑":          100_000,
    "백화점/아울렛/면세점": 150_000,
    "패션/뷰티":           80_000,
    "대중교통/택시":        60_000,
    "자동차/주유":         100_000,
    "구독/스트리밍":        30_000,
    "생활비":             150_000,
    "의료":               50_000,
    "문화/엔터":           40_000,
    "레저/스포츠":         50_000,
    "여행/숙박":          200_000,
    "항공":              300_000,
    "해외":              200_000,
    "페이/간편결제":       100_000,
}

# benefit_content에서 "N원당 M포인트/원" 또는 "N원 이상 M원 할인" 패턴 파싱
_RATIO_PATTERNS = [
    # "1,000원당 2 마일리지" / "1,000원당 10포인트"
    (r"([\d,]+(?:\.\d+)?)\s*만?원당\s*(?:스카이패스\s*)?([\d,]+(?:\.\d+)?)\s*(마일리지|포인트|원|%)", "ratio"),
    # "2만원당 1천 포인트"
    (r"([\d,]+(?:\.\d+)?)\s*만?원당\s*([\d,]+(?:\.\d+)?)\s*(마일리지|포인트|원|%)", "ratio"),
    # "3만원 이상 결제 시 3,000원 할인"
    (r"([\d,]+(?:\.\d+)?)\s*만?원\s*이상\s*결제\s*시\s*([\d,]+(?:\.\d+)?)\s*(마일리지|포인트|원|%)", "ratio"),
    # "건당 적립률: 1.5%" / "N% 적립"
    (r"적립률\s*:\s*([\d.]+)\s*%", "pct"),
    # "N% 할인" / "N% 캐시백"
    (r"([\d.]+)\s*%\s*(?:할인|캐시백|적립)", "pct"),
]

def _to_num(s: str) -> float:
    """'1,000' '3만' '30,000' → float"""
    s = s.replace(",", "").strip()
    if "만" in s:
        s = s.replace("만", "")
        return float(s) * 10000
    return float(s)


def calc_effective_rate(row: pd.Series) -> tuple[float, str]:
    """
    실질할인율(%) 계산. 반환: (rate, 근거문자열)
    계산 불가 시 (0.0, "환산불가") 반환.

    우선순위:
      1) benefit_unit == "%" → _value 그대로
      2) benefit_content 패턴 파싱
      3) max_limit ÷ performance_min
      4) 포인트/마일리지 환산율 × _value ÷ performance_min
    """
    value = row.get("_value", 0.0)
    unit  = str(row.get("benefit_unit") or row.get("_unit") or "").strip()
    content = str(row.get("benefit_content") or "")
    try:
        perf_min = float(str(row.get("performance_min") or "0").replace(",", ""))
    except (ValueError, TypeError):
        perf_min = 0.0
    try:
        perf_max = float(str(row.get("performance_max") or "0").replace(",", ""))
    except (ValueError, TypeError):
        perf_max = 0.0
    try:
        max_limit = float(str(row.get("max_limit") or "0").replace(",", ""))
    except (ValueError, TypeError):
        max_limit = 0.0

    perf = perf_min if perf_min > 0 else perf_max

    # ── 1순위: unit == % ──────────────────────────
    if unit == "%" and value > 0:
        return round(value, 2), "직접%"

    # ── 2순위: content 패턴 파싱 ──────────────────
    for pattern, kind in _RATIO_PATTERNS:
        import re as _re
        m = _re.search(pattern, content)
        if not m:
            continue
        try:
            if kind == "pct":
                rate = float(m.group(1))
                if rate > 0:
                    return round(rate, 2), "content파싱"
            elif kind == "ratio":
                base  = _to_num(m.group(1))
                reward = _to_num(m.group(2))
                reward_unit = m.group(3)
                if base > 0:
                    # 포인트/원 → 원화 환산
                    reward_krw = reward * POINT_RATE.get(reward_unit, 1.0)
                    rate = reward_krw / base * 100
                    if rate > 0:
                        return round(rate, 2), "content파싱"
        except (ValueError, IndexError):
            continue

    # ── 3순위: max_limit ÷ performance ────────────
    if max_limit > 0 and perf > 0:
        rate = max_limit / perf * 100
        return round(rate, 2), "한도÷실적"

    # ── 4순위: 포인트/마일리지 환산 ────────────────
    if unit in POINT_RATE and value > 0:
        # performance 없으면 카테고리 기준 금액 사용
        category = str(row.get("category") or "").strip()
        base = perf if perf > 0 else CATEGORY_BASE_AMOUNT.get(category, 0)
        if base > 0:
            krw   = value * POINT_RATE[unit]
            rate  = krw / base * 100
            label = ("포인트×1원" if unit == "포인트" else "마일×25원")
            if perf <= 0:
                label += "/카테고리기준"
            return round(rate, 2), label

    # ── 5순위: 원화 고정액 ÷ 카테고리 기준 금액 ─────
    if unit == "원" and value > 0:
        category = str(row.get("category") or "").strip()
        base = perf if perf > 0 else CATEGORY_BASE_AMOUNT.get(category, 0)
        if base > 0:
            rate  = value / base * 100
            label = "고정액÷실적" if perf > 0 else "고정액÷카테고리기준"
            return round(rate, 2), label

    return 0.0, "환산불가"


# benefit_content에서 수치 추출 패턴 (우선순위 순)
VALUE_PATTERNS = [
    (r"최대\s*([\d,]+(?:\.\d+)?)\s*(%|원|포인트)", 1, 2),
    (r"([\d,]+(?:\.\d+)?)\s*(%)\s*(?:할인|적립|캐시백|포인트)", 1, 2),
    (r"([\d,]+)\s*(원)\s*(?:할인|적립|캐시백)", 1, 2),
    (r"([\d,]+(?:\.\d+)?)\s*(%)", 1, 2),
    (r"([\d,]+)\s*(원)", 1, 2),
]


def _parse_value(row: pd.Series) -> tuple[float, str]:
    """
    benefit_value 컬럼 우선 사용.
    비어있으면 benefit_content에서 정규식으로 추출.
    단, benefit_title이 "대상점"이면 benefit_value가 한도값이므로 content에서 파싱.
    """
    raw_val  = row.get("benefit_value", "")
    raw_unit = str(row.get("benefit_unit") or "").strip()
    title    = str(row.get("benefit_title") or "").strip()

    # benefit_value가 있는 경우 (대상점 행 제외 — 한도값이 들어있음)
    if title != "대상점" and pd.notna(raw_val) and str(raw_val).strip() not in ("", "nan"):
        try:
            return float(str(raw_val).replace(",", "")), raw_unit
        except ValueError:
            pass

    # benefit_content에서 추출
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
# 표시값 포맷
# ──────────────────────────────────────────────

def _fmt_value(value: float, unit: str) -> str:
    unit = unit if unit and unit != "nan" else ""
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
    """target_merchants 정리. 없으면 benefit_content에서 탐색."""
    raw = str(row.get("target_merchants") or "").strip()

    if not raw or raw == "nan":
        content = str(row.get("benefit_content") or "")
        m = re.search(r"(?:할인|적립)\s*대상\s*:\s*([^\|\n]+)", content)
        return m.group(1).strip() if m else "-"

    # 콤마 구분 → 일반 키워드 제거하고 실제 가맹점만
    GENERIC = {"커피", "배달", "페이", "간편결제", "스트리밍",
               "해외", "대중교통", "택시", "온라인", "슈퍼마켓"}
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    specific = [p for p in parts if p not in GENERIC]
    return ", ".join(specific) if specific else ", ".join(parts)


# ──────────────────────────────────────────────
# 핵심 엔진
# ──────────────────────────────────────────────

class BenefitEngine:
    """
    CSV를 로드하고, 카드 ID를 받아 카테고리별 전체 혜택 행을 반환한다.
    """

    def __init__(self, benefit_csv: str, info_csv: str):
        self.raw_benefits = pd.read_csv(benefit_csv, dtype=str)
        self.raw_info     = pd.read_csv(info_csv,    dtype=str)

        # benefit_csv의 card_id가 숫자형("1228407_2207")이고
        # info_csv가 "SHC_" 접두사를 가진 경우 자동으로 맞춰줌
        info_ids = set(self.raw_info["card_id"].dropna())
        benefit_ids = set(self.raw_benefits["card_id"].dropna())
        if info_ids and benefit_ids:
            sample_info    = next(iter(info_ids))
            sample_benefit = next(iter(benefit_ids))
            if sample_info.startswith("SHC_") and not sample_benefit.startswith("SHC_"):
                self.raw_benefits["card_id"] = "SHC_" + self.raw_benefits["card_id"].astype(str)

        self.benefits = self._preprocess()

    def _preprocess(self) -> pd.DataFrame:
        df = self.raw_benefits.copy()

        # 1) 상세혜택 행만 사용
        df = df[df["row_type"].str.strip() == "상세혜택"].copy()

        # 2) 실질 혜택 행 판별: category 또는 benefit_type 중 하나라도 있어야 함
        #    title 기준 필터 제거 — 삼성은 "서비스안내", "이용조건" 같은 안내성 title에
        #    실제 혜택 수치가 담겨 있어서 title로 걸러내면 데이터가 통째로 사라짐
        has_category = df["category"].notna() & (df["category"].str.strip() != "") & (df["category"].str.strip() != "nan")
        has_type     = df["benefit_type"].notna() & (df["benefit_type"].str.strip() != "") & (df["benefit_type"].str.strip() != "nan")
        df = df[has_category | has_type].copy()

        # 제외 대상 설명 행 제거 ("할인 제외 대상", "모든 서비스 공통 제외" 등)
        EXCLUDE_KEYWORDS = ["제외 대상", "공통 제외", "추가 제외"]
        df = df[~df["benefit_title"].str.contains("|".join(EXCLUDE_KEYWORDS), na=False)].copy()

        # 3) benefit_value 파싱
        parsed        = df.apply(_parse_value, axis=1)
        df["_value"]  = [p[0] for p in parsed]
        df["_unit"]   = [p[1] for p in parsed]

        # benefit_unit 보완
        mask = df["benefit_unit"].isna() | (df["benefit_unit"].str.strip() == "")
        df.loc[mask, "benefit_unit"] = df.loc[mask, "_unit"]

        # 4) benefit_type NaN 보완 (benefit_unit 기반 추론)
        def infer_type(row):
            t = str(row.get("benefit_type") or "").strip()
            if t and t != "nan":
                return t
            u = str(row.get("benefit_unit") or row.get("_unit") or "").strip()
            if u == "마일리지":  return "마일리지"
            if u == "포인트":   return "포인트"
            if u == "%":        return "할인"
            if u == "원":       return "캐시백"
            return "기타"

        df["benefit_type"] = df.apply(infer_type, axis=1)

        # 5) 대상점 행 적립률 보완 (value 필터 전에 먼저 보완)
        #    같은 카드의 서비스안내/적립기준 행에서 "N원당 M마일리지/포인트" 패턴 추출 후
        #    대상점 행의 benefit_value/unit을 교체
        import re as _re

        def _extract_rate_from_content(text: str):
            """'N원당 M마일리지/포인트' 패턴 → (base, reward, unit) 또는 None"""
            m = _re.search(
                r"([\d,]+)\s*원당\s*(?:스카이패스\s*)?([\d,]+)\s*(마일리지|포인트)",
                str(text)
            )
            if m:
                try:
                    return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", "")), m.group(3)
                except ValueError:
                    pass
            return None

        # card_id별 대표 적립률 추출 (가장 높은 값)
        rate_map = {}  # card_id → (base, reward, unit)
        for card_id, grp in df.groupby("card_id"):
            best = None
            for _, row in grp.iterrows():
                result = _extract_rate_from_content(row.get("benefit_content", ""))
                if result:
                    base, reward, unit = result
                    if best is None or (reward / base) > (best[1] / best[0]):
                        best = result
            if best:
                rate_map[card_id] = best

        # 대상점 행에 적립률 적용
        # "1,000원당 2마일" → _value=rate(%), _unit="%"로 직접 변환
        mask_daesang = df["benefit_title"].str.strip() == "대상점"
        for idx in df[mask_daesang].index:
            card_id = df.at[idx, "card_id"]
            if card_id in rate_map:
                base, reward, unit = rate_map[card_id]
                point_rate = POINT_RATE.get(unit, 1.0)
                rate_pct = round(reward * point_rate / base * 100, 2)
                df.at[idx, "benefit_value"] = str(rate_pct)
                df.at[idx, "benefit_unit"]  = "%"
                df.at[idx, "_value"] = rate_pct
                df.at[idx, "_unit"]  = "%"

        # 6) benefit_value도 없고 서비스도 아닌 행만 제거 (최대한 보존)
        has_value   = df["_value"] > 0
        is_service  = df["benefit_type"].str.strip() == "서비스"
        has_content = df["benefit_content"].notna() & (df["benefit_content"].str.strip() != "")
        df = df[has_value | is_service | has_content].copy()

        # 7) category 없는 행 → "기타"로 채우기
        df["category"] = df["category"].fillna("기타")
        df.loc[df["category"].str.strip().isin(["", "nan"]), "category"] = "기타"

        # 8) 복합 카테고리 분리 ("커피/카페/베이커리, 배달" → 2개 행)
        rows = []
        for _, row in df.iterrows():
            cats = [CATEGORY_ALIAS.get(c.strip(), c.strip())
                    for c in str(row["category"]).split(",")]
            for cat in cats:
                r = row.copy()
                r["category"] = cat.strip()
                rows.append(r)

        return pd.DataFrame(rows).reset_index(drop=True)

    def get_card_benefits(self, card_id: str) -> pd.DataFrame:
        """
        카드 ID를 받아 카테고리별 전체 혜택을 DataFrame으로 반환.

        반환 컬럼:
            카테고리 | 혜택 제목 | 혜택 종류 | 적용 가맹점 | 혜택값 | 월 최대 | 이용 조건
        """
        df = self.benefits[self.benefits["card_id"] == card_id].copy()

        if df.empty:
            raise ValueError(f"카드 ID '{card_id}' 에 해당하는 혜택 데이터가 없습니다.")

        result_rows = []
        for _, row in df.iterrows():
            merchants = _fmt_merchants(row)

            # 적용 가맹점 없으면 전 가맹점으로 표시
            if merchants == "-":
                merchants = "전 가맹점"

            eff_rate, eff_basis = calc_effective_rate(row)
            if eff_rate >= 100:
                eff_rate, eff_basis = 0.0, "환산불가(이상값)"
            # 서비스 타입이면 서비스 내용 추출
            benefit_type = str(row.get("benefit_type") or "").strip()
            if benefit_type == "서비스":
                title = str(row.get("benefit_title") or "").strip()
                content = str(row.get("benefit_content") or "").strip()
                service_desc = title if title and title != "nan" else content[:50]
            else:
                service_desc = ""

            result_rows.append({
                "카테고리":          row["category"],
                "혜택 종류":         benefit_type,
                "적용 가맹점/혜택 내용": merchants,
                "할인율":           _fmt_value(row["_value"], str(row.get("benefit_unit") or row["_unit"])),
                "실질할인율(%)":     f"{eff_rate}%" if eff_rate > 0 else "-",
                "환산근거":          eff_basis,
                "월 최대":          _fmt_limit(row.get("max_limit"), str(row.get("max_limit_unit") or "")),
                "이용 조건":         _fmt_performance(row),
                "서비스 내용":       service_desc,
                "원본 content":     str(row.get("benefit_content") or "").strip(),
            })

        result = pd.DataFrame(result_rows)

        # 카테고리 가나다 정렬
        result = result.sort_values("카테고리").reset_index(drop=True)

        return result

    def get_card_summary(self, card_id: str) -> pd.DataFrame:
        """
        카테고리별 최고 실질할인율 1행씩 반환 (상단 요약 카드용)

        반환 컬럼:
            카테고리 | 혜택 종류 | 실질할인율(%)
        """
        df = self.get_card_benefits(card_id)
        if df.empty:
            return pd.DataFrame(columns=["카테고리", "혜택 종류", "실질할인율(%)"])

        def parse_rate(val):
            try:
                return float(str(val).replace("%", ""))
            except (ValueError, TypeError):
                return 0.0

        df["_rate_num"] = df["실질할인율(%)"].apply(parse_rate)

        # 카테고리별 최고 실질할인율 행 선택
        summary_rows = []
        for cat, grp in df.groupby("카테고리"):
            best = grp.loc[grp["_rate_num"].idxmax()]
            summary_rows.append({
                "카테고리":      cat,
                "혜택 종류":     best["혜택 종류"],
                "실질할인율(%)": best["실질할인율(%)"],
            })

        result = pd.DataFrame(summary_rows).sort_values("카테고리").reset_index(drop=True)
        return result

    def get_card_info(self, card_id: str) -> Optional[pd.Series]:
        """카드 기본 정보 (연회비, 전월실적 등)."""
        rows = self.raw_info[self.raw_info["card_id"] == card_id]
        return rows.iloc[0] if not rows.empty else None

    def list_cards(self) -> pd.DataFrame:
        """전체 카드 목록."""
        cols = ["card_id", "company", "card_name", "card_type",
                "annual_fee_dom_basic", "min_performance"]
        return self.raw_info[[c for c in cols if c in self.raw_info.columns]].copy()