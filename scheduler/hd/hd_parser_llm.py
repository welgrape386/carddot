import re
import json
import os

import anthropic

from hd_parser_base import MODEL, MAX_TOKENS

# ─────────────────────────────────────────────
# Claude 클라이언트
# ─────────────────────────────────────────────
_client = None

def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


_token_usage = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0, "calls": 0}

def call_claude(system: str, user: str, max_tokens: int = MAX_TOKENS) -> str:
    for attempt in range(3):
        resp = get_client().messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text.strip()

        if resp.usage:
            _token_usage["input"]       += resp.usage.input_tokens
            _token_usage["output"]      += resp.usage.output_tokens
            _token_usage["cache_write"] += getattr(resp.usage, "cache_creation_input_tokens", 0)
            _token_usage["cache_read"]  += getattr(resp.usage, "cache_read_input_tokens", 0)
            _token_usage["calls"]       += 1

        if resp.stop_reason == "max_tokens":
            print(f"    ! 응답 잘림 (attempt {attempt+1}), max_tokens {max_tokens} -> {min(max_tokens*2, 16000)}")
            max_tokens = min(max_tokens * 2, 16000)
            continue
        return text
    return text


def print_token_summary():
    i     = _token_usage["input"]
    o     = _token_usage["output"]
    cw    = _token_usage["cache_write"]
    cr    = _token_usage["cache_read"]
    calls = _token_usage["calls"]
    if "haiku" in MODEL:
        cost = (i * 0.0000008) + (o * 0.000004) + (cw * 0.000001) + (cr * 0.00000008)
    else:
        cost = (i * 0.000003) + (o * 0.000015) + (cw * 0.00000375) + (cr * 0.0000003)
    cache_info = f" | 캐시쓰기 {cw:,}tok / 캐시읽기 {cr:,}tok" if (cw + cr) else ""
    print(f"  [토큰] Claude 호출: {calls}회 | 입력 {i:,}tok | 출력 {o:,}tok{cache_info} | 예상 비용: ${cost:.4f} ({cost*1400:.1f}원)")

def reset_token_usage():
    _token_usage["input"] = _token_usage["output"] = 0
    _token_usage["cache_write"] = _token_usage["cache_read"] = _token_usage["calls"] = 0


def parse_json_response(text: str) -> list:
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    for attempt in [
        lambda t: json.loads(t),
        lambda t: json.loads(re.search(r"\[.*\]", t, re.DOTALL).group(0)),
        lambda t: json.loads(re.search(r"\{.*\}", t, re.DOTALL).group(0)),
    ]:
        try:
            result = attempt(text)
            return result if isinstance(result, list) else [result]
        except Exception:
            pass

    objs, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    objs.append(json.loads(text[start:i+1]))
                except Exception:
                    pass
                start = None
    if objs:
        return objs

    raise ValueError(f"JSON 파싱 실패: {text[:200]}")


# ─────────────────────────────────────────────
# 프롬프트
# ─────────────────────────────────────────────
INFO_SYSTEM = "너는 현대카드 기본정보 파싱 전문가야. JSON 객체만 출력해. 마크다운 코드블록 금지."

INFO_PROMPT = """# 역할
현대카드 HTML 텍스트에서 카드 기본정보를 추출해줘.

# 입력
**card_id**: {card_id}
**card_name**: {card_name}

**연회비 섹션** ([주요] = 연회비 금액 / 들여쓰기 = 세부 내용):
{fee_content}

**카드 주요혜택 요약** (ul.h4_m 직접 추출):
{summary_raw}

---

# 추출 스키마

| 필드 | 설명 | 예시 |
|------|------|------|
| card_name | 카드 전체 이름 | "현대카드M" |
| network | 브랜드 (대소문자 엄격 준수) | "VISA,AMEX" |
| is_domestic_foreign | 국내외겸용 여부 | true |
| annual_fee_dom_basic | 국내전용 연회비 (원, 정수) | 30000 |
| annual_fee_for_basic | 국내외겸용 연회비 (원, 정수) | 30000 |
| annual_fee_notes | 연회비 세부 내용 (기본연회비+제휴연회비 분리, 가족카드 금액) | "(기본연회비 10,000원 + 제휴연회비 20,000원) 가족카드 10,000원" |
| min_performance | 기본 혜택 전월실적 최솟값 (원) | 500000 |
| summary | 카드 주요혜택 요약 | "국내외 가맹점 1.5% 적립 / 온라인쇼핑·외식·해외 5% 적립" |
| has_cashback | 캐시백/할인 혜택 여부 (자동 처리, "" 입력) | "" |

---

# 추출 순서 (반드시 이 순서로)

## 1단계. card_name / network / is_domestic_foreign
- card_name: 입력된 card_name 그대로 사용
- network: 연회비 섹션의 [주요] 항목에서 브랜드 판별. **대소문자 엄격 준수**
  - 브랜드명 표기 규칙: VISA / AMEX / Mastercard / Local
  - "국내외겸용(Visa Platinum/Amex Platinum)" → network="VISA,AMEX", is_domestic_foreign=true
  - "국내외겸용(Visa Platinum)" → network="VISA", is_domestic_foreign=true
  - "국내외겸용(Mastercard)" → network="Mastercard", is_domestic_foreign=true
  - "국내전용"만 있으면 → network="Local", is_domestic_foreign=false
  - 여러 브랜드는 쉼표로 구분: "VISA,AMEX"

## 2단계. annual_fee_dom_basic / annual_fee_for_basic
- [주요] 항목에서 금액 숫자 추출 (콤마 제거 후 정수)
- "국내외겸용(Visa Platinum/Amex Platinum) 30,000원" → annual_fee_for_basic=30000
- "국내전용 30,000원" → annual_fee_dom_basic=30000
- 두 금액이 같으면 동일하게 입력
- 무료 / 없으면 → 0

## 3단계. annual_fee_notes ★ 중요
- [주요] 항목의 바로 아래 들여쓰기(sub-txt) 내용을 순서대로 합치기
- **규칙**: 첫 번째 줄(기본연회비+제휴연회비 분리) + \\n + 두 번째 줄(가족카드 금액 상세)
- 가족카드 금액 뒤에 괄호로 기본연회비+제휴연회비 상세가 있으면 반드시 포함
- 형식 예시:
  - 입력 sub-txt:
      (기본연회비 10,000원 + 제휴연회비 10,000원)
      가족 카드 5,000원(기본연회비 0원 + 제휴연회비 5,000원)
    → annual_fee_notes = "(기본연회비 10,000원 + 제휴연회비 10,000원)\\n가족 카드 5,000원(기본연회비 0원 + 제휴연회비 5,000원)"
  - 입력 sub-txt:
      (기본연회비 50,000원 + 제휴연회비 150,000원)
      가족카드 50,000원(기본연회비 0원 + 제휴연회비 50,000원)
    → annual_fee_notes = "(기본연회비 50,000원 + 제휴연회비 150,000원)\\n가족카드 50,000원(기본연회비 0원 + 제휴연회비 50,000원)"
  - 가족카드 상세 괄호 없는 경우: "(기본연회비 0원 + 제휴연회비 2,000원)"
- 국내외겸용 기준 sub-txt 내용 사용 (국내전용과 동일하면 1번만)
- ★ 줄바꿈(\\n) 반드시 보존 — 한 줄로 합치지 말 것

## 4단계. summary ★ 중요
- **입력된 "카드 주요혜택 요약" 텍스트를 그대로 사용** (수정/요약 금지)
- "/" 로 구분된 형태 유지
- 예시:
  입력: "국내외 가맹점 1.5% 적립 / 온라인쇼핑·외식·해외 5% 적립 / 최대 50만 M포인트 긴급적립 / (선지급 포인트 서비스)"
  출력: "국내외 가맹점 1.5% 적립 / 온라인쇼핑·외식·해외 5% 적립 / 최대 50만 M포인트 긴급적립 / (선지급 포인트 서비스)"
- 주요혜택 요약이 비어있으면 연회비 섹션 앞부분에서 혜택 3개 이내로 생성

## 5단계. min_performance
- 혜택 섹션 텍스트에서 "전월 이용 금액 N만원 이상" 패턴 추출
- 가장 낮은 구간의 값 (기본 혜택 조건)
- 예: "전월 이용 금액 50만원 이상" → 500000

## 6단계. has_cashback
- "" 입력 (benefit 파싱 완료 후 Python이 자동 판단)

---

# 출력
JSON 객체만. 설명/코드블록 없이.

예시 출력:
{{
  "card_name": "현대카드M",
  "network": "VISA,AMEX",
  "is_domestic_foreign": true,
  "annual_fee_dom_basic": 30000,
  "annual_fee_for_basic": 30000,
  "annual_fee_notes": "(기본연회비 10,000원 + 제휴연회비 20,000원)\n가족카드 10,000원(기본연회비 0원 + 제휴연회비 10,000원)",
  "min_performance": 500000,
  "summary": "국내외 가맹점 1.5% 적립 / 온라인쇼핑·외식·해외 5% 적립 / 최대 50만 M포인트 긴급적립 / (선지급 포인트 서비스)",
  "has_cashback": false
}}"""

BENEFIT_SYSTEM = "너는 현대카드 혜택 데이터 파싱 전문가야. JSON 배열만 출력해. 마크다운 코드블록 금지. 반드시 영문 키 사용. 한글 키 절대 금지."

USAGE_PLACE_SYSTEM = "너는 현대카드 사용처 카테고리 분류 전문가야. JSON 배열만 출력해. 마크다운 코드블록 금지."

USAGE_PLACE_PROMPT = """# 역할
현대카드 M포인트 사용처 텍스트에서 카테고리별로 행 분리해줘.

# 입력
{section_content}

# 카테고리 매핑표
| ID | 카테고리 | 키워드 |
|----|---------|--------|
| 1 | 온라인쇼핑 | 쇼핑, M몰, 온라인 쇼핑몰 |
| 2 | 패션/뷰티 | 패션, 뷰티 |
| 3 | 슈퍼마켓/생활잡화 | 마트, 편의점/마트 |
| 6 | 자동차/주유 | 자동차 |
| 7 | 반려동물 | 반려동물 |
| 9 | 레저/스포츠 | 레저/테마파크 |
| 11 | 문화/엔터 | 영화/음악 |
| 12 | 생활비 | 보험/금융 |
| 14 | 카페/베이커리 | 커피/베이커리 |
| 15 | 배달 | 배달/간편식 |
| 16 | 외식 | 외식 |
| 17 | 여행/숙박 | 여행/면세점 |
| 20 | 교육/육아 | 교육/도서 |

# 규칙
- 사용처 나열 텍스트에서 카테고리별로 행 분리
- category, category_id, target_merchants 3개 필드만 출력 (benefit_content 출력 금지)

# 출력
JSON 배열만. 설명/코드블록 없이.

[
  {{"category": "카테고리명", "category_id": 숫자, "target_merchants": "대상 사용처"}},
  ...
]"""

BENEFIT_PROMPT = """# 역할
현대카드 혜택 섹션 텍스트를 파싱해서 CSV 행으로 변환해줘.

# 입력
**card_id**: {card_id}
**섹션 제목**: {section_title}
**row_type**: {row_type}
**benefit_type 강제값**: {forced_benefit_type}

**혜택 내용**:
{section_content}

---

# 출력 스키마

| 필드 | 설명 |
|------|------|
| card_id | {card_id} |
| row_type | {row_type} |
| benefit_group | 상위 그룹명 (modal_pop 타이틀) |
| benefit_title | 소제목 텍스트 ([ ] 제거) |
| category | 카테고리명 (단일만, 매핑표 기준) |
| category_id | 카테고리 ID (단일만) |
| on_offline | Online / Offline / Both |
| benefit_type | 할인 / 캐시백 / 포인트 / 마일리지 / 서비스 |
| benefit_value | 혜택 수치 (숫자만, 단위 제외) |
| benefit_unit | % / 원 / 포인트 / 마일리지 |
| target_merchants | 대상 가맹점/업종명만 (50자 이내 짧게, 본문 설명 금지) |
| performance_level | 전월실적 조건 텍스트 — 구간 상한 있으면 "N만원 이상 N만원 미만", 상한 없으면 "N만원 이상", 조건 없으면 "" ★ "이상 시" 형태의 상위 조건 문구를 그대로 복사 금지 |
| performance_min | 전월실적 최솟값 (원, 숫자만) — 조건 없으면 0 |
| performance_max | 전월실적 최댓값 (원, 숫자만) — ★ 하위 구간이 명시된 경우 반드시 상한값 입력, 마지막(상한 없는) 구간만 "" |
| min_amount | 건당 최소 결제금액 |
| max_count | 최대 횟수 — 월 단위면 숫자만 (예: 1, 3), 연 단위면 텍스트 (예: "연 2회", "연 5회") |
| max_limit | 단일 행의 월 최대 혜택 한도 수치 (숫자만) — 행 분리된 통합 혜택이면 사용 금지 |
| max_limit_unit | 원 / 포인트 등 |
| group_max_limit | 행 분리된 통합 혜택의 공유 월 한도 수치 (숫자만) — 단일 행이면 사용 금지 |
| group_max_limit_unit | 원 / 포인트 등 |
| unit_amount | 적립 기준 금액 (예: 1500원당 1포인트 → 1500) |
| ui_title | 표시용 제목 |
| updated_at | {updated_at} |

※ benefit_content, ui_content, ui_table은 Python이 직접 채우므로 출력 금지.

---

# 파싱 규칙

## benefit_type 강제값 ★
- 입력의 **benefit_type 강제값**이 "내용 기반으로 판단"이 아니면 반드시 그 값 사용
- benefit_type 강제값이 "포인트"이면 → 모든 행 benefit_type=포인트
- benefit_type 강제값이 "서비스"이면 → 모든 행 benefit_type=서비스
- benefit_type 강제값이 "할인"이면 → 모든 행 benefit_type=할인

## 할인형 기본 혜택 파싱 규칙
benefit_type=할인이고 전월실적 조건이 없는 경우:
- performance_min = 0 (전월실적 조건 없음)
- performance_level = ""
- "이용 금액의 N% 청구 할인" → benefit_value=N, benefit_unit=%
- max_limit: 월 한도가 명시된 경우만 입력, 없으면 빈값
- on_offline: 국내외 가맹점 전체 → Both

## M포인트 사용 / M포인트 사용처 그룹 특수 규칙 ★
benefit_group이 "M포인트 사용처" 또는 "M포인트 사용"인 경우:
- benefit_type = 서비스 (강제) — 포인트 사용은 혜택이 아닌 서비스
- **benefit_value = "" (무조건 빈값)**
- **benefit_unit = "" (무조건 빈값)**
- performance_min = 0

섹션별 처리:
- M몰: category=온라인쇼핑(1), benefit_type=서비스, benefit_value="", ui_title="M몰 50~100% M포인트 결제 가능", target_merchants="M몰"
- 자동차 구매: category=자동차/주유(6), benefit_type=서비스, benefit_value="", ui_title="현대/기아 신차 구매 시 M포인트 최대 200만원 사용", target_merchants="현대자동차, 기아"
- M포인트 교환: category=기타(22), benefit_type=서비스, benefit_value="", ui_title="제휴사 마일리지·포인트 교환 및 H-Coin 전환", target_merchants="제휴사 마일리지·포인트, 상품권"

## row_type == "안내" ★
- benefit_type, benefit_value, benefit_unit, category, performance_min, max_limit 전부 빈값
- benefit_content = 입력 원문 그대로
- ui_title = 섹션 제목 그대로
- 수치 파싱 불필요, 행 1개만 생성

## benefit_type ★ 하나의 행에 하나만
- 포인트: M포인트 적립, 멤버십 리워즈(MR) 적립, 블루멤버스 포인트, 네이버페이 포인트, SSG MONEY, 스마일캐시, 올리브영 리워드, YES포인트, 크레딧 등 모든 포인트/리워드 적립
  → benefit_unit에 포인트명 기재 (예: "MR", "멤버십 리워즈", "블루멤버스 포인트", "네이버페이 포인트")
- 할인: 결제 시 즉시 차감 ("결제일 할인", "즉시 할인", "청구 할인", "N% 할인")
- 캐시백: 결제 후 현금 환급 ("캐시백", "환급")
- 마일리지: 항공 마일리지 적립
- 서비스: 수치로 표현 불가한 부가혜택 (라운지, 보험, 무이자할부, 플레이트, M 긴급적립, M포인트 사용처, 크레딧 제공·교환, 호텔 할인 서비스 등)
  - ★ benefit_title에 "서비스"가 명시된 항목 (예: "국내 특급호텔 할인 서비스") → 반드시 서비스 (할인 금지)
  - ★ 크레딧을 포인트로 교환하는 옵션 → 서비스 (포인트 적립이 아님)
- ★ 같은 혜택을 두 가지 타입으로 중복 파싱 금지
- ★ 하나의 행에 benefit_type 2개 이상 사용 금지
- ★ 수수료 면제(해외 가맹점 수수료, ATM 수수료 등)는 반드시 서비스

## benefit_type == "서비스" 처리 규칙 ★
- benefit_value = "" (수치 뽑지 않음)
- benefit_unit = ""
- performance_min = 0
- max_limit = ""
- **행 분리 절대 금지 — 반드시 행 1개만 생성**
- 내용에 표나 수치가 있어도 행 분리하지 말 것 (예시/설명용 수치임)
- benefit_content = 입력 원문 그대로
- **category: 서비스 내용과 가장 연관성 높은 카테고리 1개 필수 추출**
  - M 긴급적립, 포인트 선지급 → 기타(22)
  - 메탈 플레이트 제공 → 기타(22)
  - 공항 라운지 → 항공(18)
  - 자동차 구매 → 자동차/주유(6)
  - 여행 보험 → 여행/숙박(17)
  - M포인트 교환(마일리지) → 항공(18)
  - M포인트 사용처(일상) → 기타(22)
  - 매핑 불가 → 기타(22) (빈값 금지)

## benefit_value ★ 혜택 수치(할인율/적립율)만
- 전월실적·한도 수치 절대 금지
- X "전월 30만원 이상 시 5% 적립" → benefit_value=30 (틀림)
- O "전월 30만원 이상 시 5% 적립" → benefit_value=5
- X "1.5% M포인트 적립" → value=1.5, unit=M포인트 (틀림)
- O "1.5% M포인트 적립" → value=1.5, unit=%
- **소수점 퍼센트 반드시 보존**: "0.3%" → value=0.3 (0으로 반올림 금지), "0.5%" → value=0.5
- 서비스 행은 value="", unit=""

## 캐시백 benefit_value 규칙 ★
- % 캐시백: benefit_value=비율, benefit_unit=%
  - 예: "3% 캐시백" → benefit_value=3, benefit_unit=%
- 정액 캐시백(원): benefit_value=금액, benefit_unit=원
  - 예: "월 3천원 캐시백" → benefit_value=3000, benefit_unit=원
- 연간/월 최대 한도는 benefit_value가 아니라 max_limit에 넣을 것
- 예: "500만원당 2만원 캐시백, 연간 최대 10만원"
  → benefit_value=20000 (회당 2만원), benefit_unit=원
  → unit_amount=5000000, max_count="연 5회"
  → max_limit=100000, max_limit_unit=원
- X benefit_value=100000 (연간 한도를 benefit_value에 넣는 것 금지)

## M몰 benefit_value 규칙 ★
- "50~100% M포인트 사용" → benefit_value=50, benefit_unit=% (최솟값 기준)
- card_id 무관하게 M몰 섹션이면 동일하게 적용 (CCM·CCD·CCA 포함)

## performance_level / performance_min ★
- 전월실적 조건 있을 때:
  - performance_level = "전월 실적 N만원 이상" 형식 (예: "전월 실적 20만원 이상", "전월 실적 100만원 이상", "전월 실적 40만원 이상 80만원 미만")
  - ★ 반드시 앞에 "전월 실적 " 접두어를 붙일 것
  - performance_min = 하한값 (원, 숫자만)
  - performance_max = 상한값 (원, 숫자만) — 상한 없으면 ""
- 전월실적 조건 없을 때:
  - performance_level = "" (공백)
  - performance_min = 0
- 예: "전월 이용 금액 50만원 이상 시" → performance_level="전월 실적 50만원 이상", performance_min=500000
- 예: "전월 이용 금액 100만원 이상 시" → performance_level="전월 실적 100만원 이상", performance_min=1000000
- 예: "전월 이용 금액 40만원 이상 80만원 미만" → performance_level="전월 실적 40만원 이상 80만원 미만", performance_min=400000, performance_max=800000

### ★ 상위 조건 + 하위 구간 패턴 처리
"N만원 이상 시 X% 혜택\nA이상 B미만 : 월 N원\nB이상 : 월 M원" 형태이면:
- **"N만원 이상 시"는 공통 진입 조건**이지 실제 행의 performance_level이 아님
- 각 행의 performance_level/min/max는 **하위 구간 텍스트("A이상 B미만", "B이상")** 기준으로 파싱
- ★ 절대로 "N만원 이상 시" 문구를 performance_level에 그대로 쓰지 말 것

## max_limit vs group_max_limit ★ 절대 혼용 금지

### 핵심 개념
- **`max_limit`**: 해당 행 **단독**으로 적용되는 월 한도. 이 행의 혜택만 따로 카운트됨
- **`group_max_limit`**: 원본이 하나의 혜택인데 카테고리/수치 차이로 **행을 쪼갠 경우**, 쪼개진 행들의 한도가 **합산 적용**됨을 표현하는 통합 월 한도
  - 예: 온라인쇼핑·외식·해외 통합 월 1만 포인트 한도 → 행을 3개로 쪼개도 한도는 각각 1만이 아니라 **합쳐서 1만**
  - 이걸 `max_limit`에 넣으면 각 행마다 1만씩 총 3만으로 **오파싱**됨 → 반드시 `group_max_limit` 사용

### 판단 기준
- 원문에 아래 표현이 있으면 **무조건 `group_max_limit`** (행 분리 여부 무관하게 통합 표현이면 group):
  - "대상점 통합해 월 N한도" (N은 5천, 1만, 3만 등 어떤 금액이든)
  - "통합 월 N 한도"
  - "합산 기준 월 N 한도"
  - "대상점 통합해 월 N원 캐시백 한도"
  - "대상점 통합해 월 N포인트 적립 한도"
- 위 표현 없이 단일 카테고리 단독 한도 → `max_limit`
- 한도 없음 → 둘 다 빈값

### 행 분리(group_max_limit) 예시 ★
원문: "온라인쇼핑·외식·해외 가맹점 5% 적립, 대상점 통합해 월 1만 M포인트 적립 한도"
→ 행1(온라인쇼핑): max_limit="", max_limit_unit="", group_max_limit=10000, group_max_limit_unit=포인트
→ 행2(외식):       max_limit="", max_limit_unit="", group_max_limit=10000, group_max_limit_unit=포인트
→ 행3(해외):       max_limit="", max_limit_unit="", group_max_limit=10000, group_max_limit_unit=포인트
※ max_limit에 10000 넣으면 총 3만으로 오파싱 → 절대 금지

원문: "일반음식점, 배달 앱, 편의점, 대중교통, 대상점 통합해 월 5천원 캐시백 한도"
→ 행1(외식):        max_limit="", max_limit_unit="", group_max_limit=5000, group_max_limit_unit=원
→ 행2(배달):        max_limit="", max_limit_unit="", group_max_limit=5000, group_max_limit_unit=원
→ 행3(편의점):      max_limit="", max_limit_unit="", group_max_limit=5000, group_max_limit_unit=원
→ 행4(대중교통):    max_limit="", max_limit_unit="", group_max_limit=5000, group_max_limit_unit=원
※ "5천원"도 "1만"과 동일하게 group_max_limit 처리 — 금액 단위와 무관

원문: "일반음식점, 배달 앱, 편의점, 대중교통, 대상점 통합해 월 5천 M포인트 적립 한도"
→ 행1(외식):        max_limit="", max_limit_unit="", group_max_limit=5000, group_max_limit_unit=포인트
→ 행2(배달):        max_limit="", max_limit_unit="", group_max_limit=5000, group_max_limit_unit=포인트
→ 행3(편의점):      max_limit="", max_limit_unit="", group_max_limit=5000, group_max_limit_unit=포인트
→ 행4(대중교통):    max_limit="", max_limit_unit="", group_max_limit=5000, group_max_limit_unit=포인트

### 단일 행(max_limit) 예시
원문: "카페 이용 시 월 최대 3만원 할인" (카테고리 1개, 행 분리 없음)
→ max_limit=30000, max_limit_unit=원, group_max_limit="", group_max_limit_unit=""

## 금액 변환
- 1만=10000 / 10만=100000 / 50만=500000 / 100만=1000000
- 1만 2천=12000 / 5천=5000

## 카테고리 매핑표
단일 카테고리만. 행 분리로 처리됐으면 각 행은 1개만.

★ **"국내외 가맹점" 혜택은 무조건 기타(22)** — 특정 업종 구분 없이 전 가맹점 대상이므로

| ID | 카테고리 | 주요 키워드 |
|----|---------|------------|
| 1 | 온라인쇼핑 | 온라인 쇼핑몰, 네이버쇼핑, 쿠팡, G마켓, 지마켓, 옥션, 11번가, SSG.COM, 컬리, M몰, 롯데ON, W컨셉, 29CM, KREAM, 하이마트 온라인 |
| 2 | 패션/뷰티 | 올리브영, 패션, 뷰티, 무신사, 더한섬닷컴, H패션몰, MLB, 이랜드몰, 아모레몰, 이니스프리 |
| 3 | 슈퍼마켓/생활잡화 | 마트, 이마트, 홈플러스, 롯데마트, GS THE FRESH, 이마트 에브리데이, 노브랜드, 다이소 |
| 4 | 백화점/아울렛/면세점 | 백화점, 아울렛, 면세점, 신세계, 신라면세점, 롯데면세점, 현대면세점 |
| 5 | 대중교통/택시 | 버스, 지하철, 기차, 대중교통, 택시, KTX, SRT, 카카오택시, 티머니, 후불교통 |
| 6 | 자동차/주유 | 주유, 자동차, 하이패스, GS칼텍스, SK에너지, 오일뱅크, 현대자동차, 기아, 신차 구매, 블루핸즈, 타이어픽 |
| 7 | 반려동물 | 반려동물, 펫프렌즈, 어바웃펫, 강아지대통령, 고양이대통령 |
| 8 | 구독/스트리밍 | 구독, 스트리밍, 넷플릭스, 유튜브 프리미엄, 멜론, 스포티파이, 웨이브, 왓챠, 티빙, 지니뮤직 |
| 9 | 레저/스포츠 | 골프, 피트니스, 헬스장, 레저, 스포츠, 워터파크, 테마파크, 스키, 경기관람 |
| 10 | 페이/간편결제 | Apple Pay, 애플페이, 간편결제, 삼성페이, 카카오페이, 네이버페이, 제로페이, 페이코 |
| 11 | 문화/엔터 | 영화, 놀이공원, 공연, CGV, 메가박스, 롯데시네마, 에버랜드, 롯데월드, 콘서트, 아쿠아플라넷 |
| 12 | 생활비 | 통신, SKT, KT, LG유플러스, LGU+, 보험, 현대해상, 공과금, 도시가스, 렌탈, 자동납부, 아파트 관리비, ATM |
| 13 | 편의점 | 편의점, 세븐일레븐, GS25, CU, 이마트24, 미니스톱 |
| 14 | 카페/베이커리 | 커피전문점, 커피, 카페, 베이커리, 스타벅스, 투썸, 이디야, 메가커피, 빽다방, 할리스, 파리바게뜨, 뚜레쥬르, 배스킨라빈스, 공차 |
| 15 | 배달 | 배달, 배민, 배달의민족, 요기요, 쿠팡이츠, 땡겨요 |
| 16 | 외식 | 패스트푸드, 외식, 일반음식점, 음식점, 아웃백, 레스토랑, VIPS, 도미노피자, 파파존스, 피자헛, 롯데리아, 쉐이크쉑, 맥도날드, 버거킹, KFC, 맘스터치 |
| 17 | 여행/숙박 | 여행, 숙박, 호텔, 렌터카, 야놀자, 여기어때, 에어비앤비, 카모아, SK렌터카, PRIVIA 여행, KKday |
| 18 | 항공 | 공항라운지, 라운지, 항공, 대한항공, 아시아나, 마일리지, 발레파킹, 인천국제공항, 에어프레미아 |
| 19 | 해외 | 해외 가맹점, 해외이용, 해외결제, 외화, 해외직구, 해외 온·오프라인 |
| 20 | 교육/육아 | 학원, 서점, 육아, 교육, 유치원, 어린이집, 교보문고, 야나두 |
| 21 | 의료 | 병원, 약국, 의료, 치과, 한의원 |
| 22 | 기타 | 국내외 가맹점 전체 대상, 제휴사 마일리지·상품권 교환, M포인트 교환, H-Coin 전환, 위에 해당 없는 경우 |

## benefit_content 규칙 ★
- **benefit_content = 입력된 섹션 전체 원문** (줄바꿈 \\n 보존, 요약/수정 금지)
- 행 분리가 발생해도 **분리된 모든 행의 benefit_content는 완전히 동일한 원문** 복사
- ★ 행 분리 시 category/target_merchants만 다르고 나머지 필드는 전부 동일하게 복사
- 유의사항([M포인트 사용 기준] 등) 포함한 전체 원문을 그대로 복사할 것

## 행 분리 기준 ★
아래 중 하나라도 해당하면 별도 행:
1. 전월실적 구간이 다를 때
2. benefit_value가 다를 때
3. max_limit이 다를 때
4. 카테고리가 다를 때

### 전월실적 구간별 max_limit 분리 ★
전월실적 구간마다 한도(max_limit)가 다르면 구간별로 행 분리.

#### ★★ 상위 조건 아래 하위 구간 나열 패턴 (CCA 등) ★★
아래처럼 "N만원 이상 시 X% 혜택" 바로 다음에 "A이상 B미만 : 월 N원" 형태로 구간이 나열되면:
- 상위 조건("30만원 이상 시")은 **공통 조건**이고, 실제 행은 **하위 구간 개수만큼** 생성
- 상위 조건의 하한값이 곧 첫 번째 하위 구간의 시작점
- 각 하위 구간의 performance_level/performance_min/performance_max/max_limit을 정확히 파싱

```
전월 이용 금액 30만원 이상 시 10% 캐시백
30만원 이상 60만원 미만 : 월 5천원
60만원 이상 : 월 1만원
```
→ 행1: performance_level="전월 실적 30만원 이상 60만원 미만", performance_min=300000, **performance_max=600000**, max_limit=5000,  max_limit_unit=원
→ 행2: performance_level="전월 실적 60만원 이상",              performance_min=600000, **performance_max=""**,     max_limit=10000, max_limit_unit=원
※ benefit_value=10, benefit_unit=% 는 두 행 동일하게 복사

#### ★★ 절대 금지 패턴 ★★
- 행1에 performance_level="30만원 이상 시" (상위 조건 그대로 복사) → **금지**
- 행1에 performance_max="" (상위 조건만 있을 때 상한 누락) → **금지**
- 하위 구간이 명시된 경우 반드시 performance_max 채울 것 (상한 없는 마지막 구간 제외)

### 카테고리 분리 ★ 중요
`[대상점]` 아래 항목이 여러 카테고리에 걸치면 **반드시** 카테고리별 행 분리:

예시 1 - [대상점] 형식:
```
[대상점]
온라인 쇼핑몰 : 네이버쇼핑, 쿠팡, G마켓, 옥션, 11번가, SSG.COM, 컬리
일반음식점
해외 가맹점 : 해외 온·오프라인 가맹점
```
→ 행1: category=온라인쇼핑(1), target=온라인 쇼핑몰(네이버쇼핑, 쿠팡...)
→ 행2: category=외식(16), target=일반음식점
→ 행3: category=해외(19), target=해외 가맹점(해외 온·오프라인 가맹점)

예시 1-B - [대상점] 커피전문점/패스트푸드 형식 (현대카드 Teens 등):
```
[대상점]
편의점 : CU, GS25, 이마트24, 세븐일레븐
커피전문점 : 스타벅스, 투썸플레이스, 이디야커피, 빽다방
패스트푸드 : 맥도날드, 롯데리아, KFC, 버거킹, 맘스터치
대중교통 : 시내버스(시외/고속버스 제외), 지하철, 택시
```
→ 행1: category=편의점(13), target=편의점 : CU, GS25, 이마트24, 세븐일레븐
→ 행2: category=카페/베이커리(14), target=커피전문점 : 스타벅스, 투썸플레이스, 이디야커피, 빽다방
→ 행3: category=외식(16), target=패스트푸드 : 맥도날드, 롯데리아, KFC, 버거킹, 맘스터치
→ 행4: category=대중교통/택시(5), target=대중교통 : 시내버스(시외/고속버스 제외), 지하철, 택시
※ 패스트푸드 → category=외식(16), 커피전문점 → category=카페/베이커리(14) 매핑 필수

예시 1-C - 항공/여행/호텔/면세점 복합 대상점:
```
국내 항공사, 여행사, 특급호텔, 면세점
```
→ 행1: category=항공(18),               target=국내 항공사
→ 행2: category=여행/숙박(17),          target=여행사, 특급호텔
→ 행3: category=백화점/아울렛/면세점(4), target=면세점
※ 항공사·마일리지 → 항공(18), 여행사·호텔 → 여행/숙박(17), 면세점 → 백화점/아울렛/면세점(4) 구분 필수

예시 2 - 줄바꿈 나열 형식 (일상 사용처):
```
커피/베이커리, 외식, 배달/간편식, 편의점/마트
쇼핑, 패션, 뷰티
여행/면세점, 레저/테마파크, 영화/음악, 교육/도서
자동차, 보험/금융, 반려동물
```
→ 카테고리 매핑표 기반으로 각 업종별 행 분리:
→ 행1: category=카페/베이커리(14), target=커피/베이커리
→ 행2: category=외식(16), target=외식
→ 행3: category=배달(15), target=배달/간편식
→ 행4: category=슈퍼마켓/생활잡화(3), target=편의점/마트
→ 행5: category=온라인쇼핑(1), target=쇼핑
→ 행6: category=패션/뷰티(2), target=패션, 뷰티
→ 행7: category=여행/숙박(17), target=여행/면세점
→ 행8: category=레저/스포츠(9), target=레저/테마파크
→ 행9: category=문화/엔터(11), target=영화/음악
→ 행10: category=교육/육아(20), target=교육/도서
→ 행11: category=자동차/주유(6), target=자동차
→ 행12: category=생활비(12), target=보험/금융
→ 행13: category=반려동물(7), target=반려동물

예시 3 - 체크카드 추가 혜택 형식 (대상점 통합 한도 포함):
```
전월 이용 금액 30만원 이상 시 일반음식점, 배달 앱, 편의점, 대중교통 5% M포인트 적립
[대상점]
일반음식점
배달 앱 : 배달의민족, 쿠팡이츠, 요기요
편의점 : GS25, CU, 세븐일레븐, 이마트24
대중교통 : 시내버스, 지하철
대상점 통합해 월 5천 M포인트 적립 한도
```
→ 카테고리 4개 → 행 4개로 분리, 한도는 통합 5천 포인트 → group_max_limit
→ 행1: category=외식(16),        target=일반음식점,                    group_max_limit=5000, group_max_limit_unit=포인트
→ 행2: category=배달(15),        target=배달의민족, 쿠팡이츠, 요기요,  group_max_limit=5000, group_max_limit_unit=포인트
→ 행3: category=편의점(13),      target=GS25, CU, 세븐일레븐, 이마트24, group_max_limit=5000, group_max_limit_unit=포인트
→ 행4: category=대중교통/택시(5), target=시내버스, 지하철,              group_max_limit=5000, group_max_limit_unit=포인트
※ max_limit에 넣으면 각 행마다 5천씩 총 2만으로 오파싱 → 절대 금지
- benefit_content → **모든 행 동일하게 복사** (원문 전체)
- benefit_value, performance_min, max_limit → 동일하게 복사
- group_max_limit → 동일하게 복사 ("대상점 통합해 월 N만 한도"면 group_max_limit에 입력)
- category, target_merchants → 각 행별로 해당 카테고리만

## 표 파싱 규칙

### 표에서 수치 추출
- "전월 이용 금액 N만원 이상" → performance_min = N×10000
- "월 N만 M포인트 한도" → max_limit = N×10000, max_limit_unit=포인트
- "N만원 이상 이용 시 제공" → min_amount = N×10000
- "월 N회" → max_count = N (숫자만)
- "연간 N회" / "연 N회" / "(최대 N회)" 연간 문맥 → max_count = "연 N회" (텍스트)

### rowspan 표 파싱
rowspan 있는 표는 각 행을 독립적으로 파싱해서 행 분리:
예:
혜택 | 적립률 | 월 이용 금액 | 적립 M포인트(월)
기본 혜택 | 1.5% | rowspan 기준 | 80만원 | 1만 2천
추가 혜택 | 5%   | 20만원 | 1만
→ 행1: benefit_value=1.5, performance_min=800000, max_limit=12000, max_limit_unit=포인트
→ 행2: benefit_value=5, performance_min=200000, max_limit=10000, max_limit_unit=포인트

rowspan으로 공유된 셀 값은 각 행에 동일하게 복사해서 파싱.

## 서비스 행 ui_title ★ (현대카드 전용)
benefit_type == "서비스"인 행의 ui_title (100자 이내 요약):
- "최대 50만 M포인트 선지급 서비스" (M 긴급적립)
- "VISA 브랜드 메탈 플레이트 제공"
- "VISA/AMEX 플래티넘 기본서비스 제공"
- "M포인트 제휴사 마일리지·상품권 교환"
- "현대자동차·기아 신차 M포인트 사용"
- "일상 사용처 M포인트 사용"

## ui_title ★ (모든 행 필수)
benefit_type에 따라 형식 다름:

### 포인트/할인/캐시백
"{{카테고리}} {{수치}}{{단위}} {{타입}}" 형식
- 단위가 %인 경우: "온라인쇼핑 5% 적립" / "외식 3% 캐시백" / "국내외 가맹점 0.3% 캐시백"
- 단위가 원인 경우: 수치를 사람이 읽기 쉽게 변환 — 5000→"5천원", 10000→"1만원", 20000→"2만원"
  - 예: benefit_value=20000, unit=원 → "연간 2만원 캐시백"
- category=기타(22)면 카테고리명 대신 **benefit_title 또는 실제 대상 텍스트** 사용:
  - benefit_title이 "기본 혜택" 등 일반적인 경우 → 실제 대상 텍스트 사용
    - "국내외 가맹점 1.5% 적립" / "국내외 가맹점 0.8% 할인" / "국내외 가맹점 0.3% 캐시백"
    - Apple Pay 대상: "Apple Pay 이용 금액 10% 캐시백"
  - benefit_title이 구체적인 경우 → benefit_title 활용
- category가 기타가 아니면 반드시 카테고리명 사용 (가맹점명 직접 쓰지 말 것)
  - X "배달의민족, 쿠팡이츠, 요기요 5% 적립" → O "배달 5% 적립"
  - X "GS25, CU, 세븐일레븐 5% 적립" → O "편의점 5% 적립"
  - X "시내버스, 지하철 5% 적립" → O "대중교통 5% 적립"
- M포인트 사용처 그룹:
  - M몰: "M몰 50~100% M포인트 사용"
  - 자동차 구매: "현대자동차·기아 신차 M포인트 사용"
  - M포인트 교환: "M포인트 제휴사 마일리지·상품권 교환"
  - 일상 사용처: "{{카테고리}} M포인트 사용"

### 서비스 (benefit_type == "서비스")
서비스 내용을 간결하게 요약 (100자 이내):
- "공항 라운지 연 2회 무료 이용"
- "무이자할부 2~3개월"
- "여행자보험 최대 1억원 보장"
- "최대 50만 M포인트 선지급 서비스" (M 긴급적립)
- "최대 50만 긴급할인 서비스" (ZERO 긴급할인)
- "VISA 브랜드 메탈 플레이트 제공"
- "VISA/AMEX 플래티넘 기본서비스 제공"
- 수치가 있으면 수치 포함 ("연 5회", "최대 N만원" 등), 없으면 서비스 특성 중심으로 요약

---

# 출력
JSON 배열만. 설명/코드블록 없이."""


def _build_benefit_system() -> str:
    parts = BENEFIT_PROMPT.split("---\n\n", 1)
    static_rules = parts[1] if len(parts) > 1 else ""
    return BENEFIT_SYSTEM + "\n\n---\n\n" + static_rules


def _make_benefit_user(card_id: str, section_title: str, row_type: str,
                       forced_benefit_type: str, section_content: str,
                       updated_at: str) -> str:
    return (
        f"# 입력\n"
        f"**card_id**: {card_id}\n"
        f"**섹션 제목**: {section_title}\n"
        f"**row_type**: {row_type}\n"
        f"**benefit_type 강제값**: {forced_benefit_type}\n\n"
        f"**혜택 내용**:\n{section_content}\n\n"
        f"updated_at: {updated_at}"
    )
