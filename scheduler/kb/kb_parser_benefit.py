import re
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from bs4 import BeautifulSoup

from kb_parser_base import (
    CATEGORY_KEYWORD_MAP, CATEGORY_ID_MAP,
    call_claude, parse_json_response, now_str, now_date,
)
from kb_parser_html import (
    build_ui_content,
    extract_card_image, extract_network,
    extract_annual_fee_notes, extract_annual_fees_rule,
    extract_fee_content, _extract_card_summary,
)


# ─────────────────────────────────────────────
# 후처리 함수
# ─────────────────────────────────────────────
def build_ui_title(row: dict) -> str:
    category     = row.get("category", "")
    benefit_type = row.get("benefit_type", "")
    benefit_value = str(row.get("benefit_value", "")).strip()
    benefit_unit  = str(row.get("benefit_unit", "")).strip()
    ai_title      = str(row.get("ui_title", "")).strip()

    bad_patterns = [r"^0\s*%", r"^0\s*원", r"^\[.*\]$"]
    ai_title_clean = ai_title
    for pat in bad_patterns:
        if re.match(pat, ai_title_clean):
            ai_title_clean = ""
            break

    benefit_title = str(row.get("benefit_title", "")).strip()
    display_cat = benefit_title if category in ("기타", "", "22") and benefit_title else category

    if benefit_type == "서비스":
        if ai_title_clean and not re.match(r"^\[.*\]$", ai_title_clean):
            return ai_title_clean
        return f"{display_cat} 서비스" if display_cat else "서비스"

    if benefit_value and benefit_value not in ("", "0", "null", "None"):
        type_label = {"할인": "할인", "캐시백": "캐시백", "포인트": "적립",
                      "마일리지": "마일리지 적립"}.get(benefit_type, benefit_type)
        unit = benefit_unit if benefit_unit else ""
        return f"{display_cat} {benefit_value}{unit} {type_label}".strip()

    if ai_title_clean and not re.match(r"^\[.*\]$", ai_title_clean):
        return ai_title_clean

    return f"{display_cat} {benefit_type}".strip() if display_cat else benefit_type


def correct_category(row: dict) -> dict:
    current_cat = row.get("category", "기타")
    is_other = current_cat in ("기타", "", "22")

    merchants = str(row.get("target_merchants", ""))

    if is_other:
        text = merchants + " " + str(row.get("benefit_title", ""))
    else:
        text = merchants

    if not text.strip():
        return row

    COEXIST_SKIP = {
        "외식":    ["편의점", "배달", "카페/베이커리"],
        "편의점":  ["외식", "배달"],
        "배달":    ["외식", "편의점"],
        "카페/베이커리": ["외식"],
    }
    skip_cats = set() if is_other else set(COEXIST_SKIP.get(current_cat, []))

    for cat_name, keywords in CATEGORY_KEYWORD_MAP:
        if cat_name in skip_cats:
            continue
        if any(kw in text for kw in keywords):
            row["category"] = cat_name
            row["category_id"] = str(CATEGORY_ID_MAP.get(cat_name, 22))
            return row
    return row


# ─────────────────────────────────────────────
# 프롬프트
# ─────────────────────────────────────────────
INFO_SYSTEM = "너는 KB국민카드 기본정보 파싱 전문가야. JSON 객체만 출력해. 마크다운 코드블록 금지."

INFO_PROMPT = """# KB국민카드 기본정보 추출

## 입력
card_id: {card_id}
card_name: {card_name}
HTML 텍스트:
{page_text}

## 출력 스키마 (JSON 객체)
- card_name: 카드 전체 이름
- annual_fee_dom_basic: 국내전용(Local) 일반 연회비 합계 (원, 정수, 없으면 0)
- annual_fee_for_basic: 국내외겸용(VISA/Mastercard/AMEX/JCB 등) 일반 연회비 합계 (원, 정수, 없으면 0). 국내외겸용 브랜드가 여러 개면 그 중 하나의 금액을 대표값으로 사용
- min_performance: 가장 낮은 전월실적 조건 (원, 없으면 0)
- summary: 카드 주요혜택 한줄 요약 (3개 이내, "/" 구분)
- has_cashback: 할인/캐시백 혜택 존재 여부 (true/false)

※ network/image_url/annual_fee_notes/fee_content는 규칙 기반으로 별도 추출하므로 출력 불필요.
JSON만 출력."""

BENEFIT_SYSTEM = """너는 KB국민카드 혜택 파싱 전문가야. JSON 배열만 출력해. 마크다운 코드블록 금지. 반드시 영문 키만 사용.

---

## 1. 출력 스키마
| 필드 | 설명 |
|------|------|
| card_id | 입력값 그대로 |
| row_type | 주요혜택 / 안내 |
| benefit_group | 입력된 benefit_group 그대로 |
| benefit_title | 소제목 (간결하게, 30자 이내) |
| category | 카테고리명 (아래 매핑표 기준, 단일값) |
| category_id | 카테고리 ID |
| on_offline | Online / Offline / Both (영문) |
| benefit_type | 할인 / 캐시백 / 포인트 / 마일리지 / 서비스 |
| benefit_value | 혜택 수치 (**숫자만**, 단위·원·% 절대 포함 금지). 한국식 금액 변환 필수: "2,000원"→2000 / "2천원"→2000 / "1만원"→10000. ✗ "10000원 할인"→틀림 / ✓ benefit_value=10000, benefit_unit="원". 범위(N~M)이면 최댓값 M만 사용 |
| benefit_unit | % / 원 / 포인트 / 마일리지 |
| target_merchants | 대상 가맹점/업종 (50자 이내). ★ 카테고리 분리 시 각 행에는 **해당 카테고리에 속하는 대상만** 넣을 것 — 다른 카테고리 대상을 섞지 말 것. 예) 음식점+편의점 섹션 → 외식 행: "음식점(한식,일식…)", 편의점 행: "GS25, CU" |
| performance_level | "전월 실적 N만원 이상" 형식 |
| performance_min | 전월실적 최솟값 (원, 숫자만, 없으면 0) |
| performance_max | 전월실적 최댓값 — 다음 구간 시작값 정수. 30만~80만 구간→800000, 40만~80만→800000. 상한 없으면 "". ★ 799999·299999 등 금지, 반드시 딱 떨어지는 값 |
| min_amount | 건당 최소 결제금액 (원). "건당 N원 이상 이용 시" → min_amount=N. 한국식 변환 필수: "건당 7만원"→70000, "건당 1만원"→10000, "건당 20만원"→200000 |
| max_count | 최대 횟수. ★ 우선순위: 월 > 연 > 일. "월 3회, 연 12회" → max_count="월 3회" (월 우선). "연 2회"만 있으면 "연 2회". "연 N만원" = 금액한도 → 빈값 |
| max_limit | 이 행 단독 월 한도 (숫자만) |
| max_limit_unit | 값 있으면 반드시 "원" |
| group_max_limit | 여러 행 공유 월 한도 (숫자만) |
| group_max_limit_unit | 값 있으면 반드시 "원" |
| unit_amount | N원당 M포인트/마일의 N (원) |
| ui_title | 서비스형만 직접 작성, 수치형은 "" |
| updated_at | 입력값 그대로 |

※ benefit_content, ui_content → 빈값("") 출력

---

## 2. 카테고리 매핑
1=온라인쇼핑 2=패션/뷰티 3=슈퍼마켓/생활잡화 4=백화점/아울렛/면세점 5=대중교통/택시
6=자동차/주유 7=반려동물 8=구독/스트리밍 9=레저/스포츠 10=페이/간편결제
11=문화/엔터 12=생활비 13=편의점 14=카페/베이커리 15=배달
16=외식 17=여행/숙박 18=항공 19=해외 20=교육/육아 21=의료 22=기타

### 카테고리 분류 규칙 ★
- 혜택 대상(어디서 쓰는지)으로 분류. 결제수단이 아님.
  - ✗ "온라인쇼핑 (KB Pay 결제 시)" → 페이/간편결제 (틀림)
  - ✓ "온라인쇼핑 (KB Pay 결제 시)" → 온라인쇼핑 (KB Pay는 결제수단일 뿐)
  - ✓ "KB Pay 결제 전체" → 페이/간편결제 (KB Pay 자체가 혜택 대상)
- 여러 업종 포함 시 대표 카테고리 1개 또는 행 분리:
  - 병원 + 약국 → 의료 1행 (같은 카테고리, target_merchants="병원, 약국")
  - 병원 + 약국 + 스포츠 → 의료 행 + 레저/스포츠 행 (다른 카테고리)
  - 주차장 + 세차장 → 자동차/주유 1행
  - 배달앱 + 커피 → 배달 행 + 카페/베이커리 행
- **쿠팡 카드 전용**: 쿠팡 + 쿠팡이츠 + 쿠팡플레이가 함께 나오면 **반드시 3행** 분리 (2행 절대 금지)
  - 쿠팡 → 온라인쇼핑
  - 쿠팡이츠 → 배달
  - 쿠팡플레이 → 구독/스트리밍
  - 세 행 모두 동일한 group_max_limit 사용
- 구체적 매핑:
  - 넷플릭스, 유튜브프리미엄, 웨이브, 티빙, 디즈니플러스 → 구독/스트리밍
  - CGV, 롯데시네마, 메가박스, 교보문고 → 문화/엔터
  - 에버랜드, 롯데월드, 골프장, 헬스장, 볼링장, 수영장, 스키장 → 레저/스포츠
  - SKT, KT, LGU+, Liiv M 통신요금 → 생활비
  - 수수료 면제, 이체 수수료 → 생활비
  - 택시(카카오택시 등) → 대중교통/택시
  - 주차장, 세차장, 주유소 → 자동차/주유

---

## 3. 행 분리 기준 ★
아래 중 하나라도 다르면 별도 행:
1. 전월실적 구간이 다를 때 (40만↔80만)
2. benefit_value(할인율)가 다를 때 (5%↔30%)
3. max_limit 또는 group_max_limit(월 한도)가 다를 때
4. 카테고리가 다를 때 (병원↔스포츠, 배달↔카페 등)

**같은 카테고리 = 행 1개로 합침:**
- 병원 + 약국 → 의료 1행, target_merchants="병원, 약국"
- 시내버스 + 지하철 + 고속버스 → 대중교통/택시 1행
- 주차장 + 세차장 → 자동차/주유 1행

**다른 카테고리가 나열된 경우 → 반드시 카테고리별 행 분리 ★**
```
예) 이마트II 생활업종: 학원, 약국, 패밀리레스토랑, 편의점, 주유, 미용실, 골프장
→ 각각 다른 카테고리이므로 카테고리별 행 분리:
  교육/육아(학원) / 의료(약국) / 외식(패밀리레스토랑) / 편의점 /
  자동차/주유(주유) / 패션/뷰티(미용실) / 레저/스포츠(골프장)
  모두 group_max_limit 공유

예) K-패스 생활서비스: 이동통신, 커피, 약국, 편의점, 영화, 패스트푸드 (rowspan=6)
→ 각각 다른 카테고리이므로 행 분리:
  생활비(이동통신) / 카페/베이커리(커피) / 의료(약국) / 편의점 / 문화/엔터(영화) / 외식(패스트푸드)
  모두 group_max_limit 공유
```

**전월실적 구간 + 할인율 동시에 다른 경우 → 반드시 별도 행:**
```
예) 이마트II 표:
  전월 이용실적 | 월 할인한도 | 할인율 | 제공기준
  50만원 이상   | 2만원       | 20%    | 건당 7만원 이상
  100만원 이상  | 4만원       | 30%    | 건당 7만원 이상
→ 2행: perf(50만,100만) + benefit_value(20,30) 모두 다름
  행1: performance_min=500000, performance_max=1000000, benefit_value=20, max_limit=20000, min_amount=70000
  행2: performance_min=1000000, benefit_value=30, max_limit=40000, min_amount=70000
```

**실적 유예기간 안내 → 행 생성 금지:**
- "최초 카드 사용등록일로부터 다음달 말일(실적 유예기간)까지 ... 미만 시 월 N원 한도" 문장은 신규 발급 임시 조건
- 이 문장으로 별도 행(perf:0~400000 등) 생성 절대 금지 → 표의 정식 구간만 행 생성

**[이용 조건] 없고 전월실적 구간 없으면 → 행 1개 (performance_min=0)**

**통합할인한도 표 → 완전 무시:**
"전월이용실적에 따른 통합할인한도" 표는 카드 전체 합산 상한 → 개별 혜택과 무관
→ 이 표로 행 분리 금지, group_max_limit에 사용 금지

---

## 4. max_limit vs group_max_limit ★ (하나만 사용, 절대 동시 사용 금지)

### 핵심 개념
- **max_limit**: 이 행 **혼자** 쓸 수 있는 단독 월 한도 — 다른 행과 완전히 무관
- **group_max_limit**: 여러 행이 **합산 공유**하는 월 한도 — 이 그룹 전체 합산이 N원을 넘을 수 없음

### ★★ 판단 우선순위 (위에서 아래로)

**[1순위] 표의 rowspan 구조 ← 가장 신뢰도 높음**
- 한도 셀이 rowspan ≥ 2로 여러 행을 커버 → 해당 행 모두 **group_max_limit**
- 각 행이 자신만의 독립적인 한도 셀 보유 → **max_limit**

```
예) K-패스체크카드 표:
  구분          | 세부 영역          | 건당조건(rowspan=7) | 적립율        | 월한도(적립한도)   | 전월실적(rowspan=8)
  대중교통 적립  | 버스, 지하철       | 건당 1만원 이상     | 10%           | [2천점] ← 독립    | 20만원
  생활서비스(rowspan=6) | 이동통신   | (carry)             | [1% rowspan=6]| [4천점 rowspan=6] | (carry)
  (carry)       | 커피 업종          | (carry)             | (carry)       | (carry)           | (carry)
  ...약국/편의점/영화/패스트푸드...
  KB Pay 추가적립| 생활서비스 KB Pay | (carry)             | 1%            | [4천점] ← 독립    | (carry)

→ 결과:
  대중교통(버스/지하철): max_limit=2000, perf_min=200000, min_amount=10000
  ★ 건당조건(rowspan=7) carry → 대중교통·생활서비스 6개·KB Pay 모두 min_amount=10000 적용
  생활서비스(이동통신,커피,약국,편의점,영화,패스트푸드): group_max_limit=4000 (rowspan=6 공유)
  KB Pay 추가적립: max_limit=4000 (독립 셀)
```

**[2순위] [이용 조건] 힌트**
- `(max_limit)` 힌트 → max_limit
- `(group_max_limit)` 힌트 → group_max_limit
- `* A / B : 월 할인한도 N원` (A/B가 슬래시로 연결) → 현재 섹션 행에 group_max_limit
- `* KEY : 월 할인한도 N원` (단일 KEY) + 이 섹션에서 여러 카테고리 생성 → 모두 group_max_limit

**[3순위] 표 없고 힌트도 없을 때 (기본 규칙)**
- 같은 한도값이 여러 카테고리에 동일하게 적용되고 할인율도 같으면 → **group_max_limit**
- 각 카테고리마다 한도값이 다르거나 할인율이 다르면 → **max_limit** (각자 독립)

### ★ group_max_limit 금지 케이스 (max_limit 사용할 것)
- 할인율(benefit_value)이 서로 다른 카테고리들 — 예) OTT 30% vs 편의점 5% vs 배달 5%
  → 이들의 한도가 같더라도 각자 독립적인 혜택이므로 **max_limit**
- 표에서 각 행이 자신만의 한도 셀을 가질 때

### [이용 조건] 블록 처리 ★
- `* A : 월 할인한도 N원 (max_limit)` → max_limit=N
- `* A / B : 월 할인한도 N원 (group_max_limit)` → A와 B 모두 group_max_limit=N
- `※ 현재 섹션만 행 생성할 것` → 이 섹션 카테고리 1행만 생성 (구간별로는 분리)
- `* KEY : 월 할인한도 N원` (슬래시 없음) + 이 섹션에서 배달+커피처럼 여러 카테고리 → 모두 group_max_limit=N
- performance_min → [이용 조건]의 전월실적 텍스트에서 추출

### 실전 예시

**독립 한도 (max_limit):**
```
두산베어스 생활영역 — OTT(30%)/편의점(5%)/배달(5%) 각각 다른 할인율 → 각자 max_limit
→ OTT 30만: max_limit=5000 / OTT 80만: max_limit=10000
→ 편의점 30만: max_limit=3000 / 편의점 80만: max_limit=5000
→ 배달 30만: max_limit=3000 / 배달 80만: max_limit=5000
```

**rowspan 공유 (group_max_limit):**
```
이동통신(rowspan=2, 3천원) + OTT(rowspan carry) → group_max_limit=3000 각 구간
→ 생활비 (이통): group_max_limit=3000, max_limit=""
→ 구독/스트리밍 (OTT): group_max_limit=3000, max_limit=""
```

*** KEY + 여러 카테고리 (group_max_limit):**
```
[이용 조건]: * 배달 : 월 할인한도 5,000원
혜택 내용: 배달앱(배달의 민족, 요기요), 커피(커피/음료전문점 업종)
→ 배달(배달 카테고리): group_max_limit=5000
→ 커피(카페/베이커리 카테고리): group_max_limit=5000
※ KEY가 "배달"이더라도 섹션에 커피도 포함되면 두 행 모두 group_max_limit
```

**단독 한도 (max_limit):**
```
[이용 조건]: * KB Pay : 월 할인한도 5,000원 (max_limit)
→ 페이/간편결제: max_limit=5000
```

**슬래시 그룹 (group_max_limit):**
```
[이용 조건]: * 음식점 / 편의점 : 월 할인한도 5,000원 (group_max_limit)
→ [음식점 섹션]: 외식: group_max_limit=5000
→ [편의점 섹션]: 편의점: group_max_limit=5000
```

---

## 5. benefit_value 추출 규칙 ★
- 혜택 수치(할인율/적립률)만 추출. 전월실적·한도 수치 절대 금지.
  - ✗ "전월 30만원 이상 시 5% 적립" → benefit_value=30 (틀림!)
  - ✓ "전월 30만원 이상 시 5% 적립" → benefit_value=5
- 소수점 보존: "0.5%" → value=0.5 (0으로 반올림 금지)
- "건당 최대 N원 할인" → benefit_value="", max_limit="" (건당 금액 ≠ 월 한도)
- 서비스형 → benefit_value="", benefit_unit=""
- **한국식 금액 → 반드시 정수 변환**: "2천원"=2000 / "5천원"=5000 / "1만원"=10000 / "1만5천원"=15000 / "2,000원"=2000
  - ✗ "2,000원" → benefit_value=2 (틀림! 쉼표 무시 금지)
  - ✓ "2,000원" → benefit_value=2000
- **혜택 없는 섹션 처리**: 수치(%, 원, 마일)가 전혀 없고 유의사항/약관/가족카드안내 등만 있으면 → 행 생성 금지, 빈 배열 [] 반환

## 5-1-1. 마일리지 적립 표 파싱 ★
- "N원당 M마일 적립" → benefit_type=마일리지, benefit_value=M, benefit_unit=마일리지, unit_amount=N
  - 예) "1천원당 1마일" → benefit_value=1, unit_amount=1000, benefit_unit=마일리지
  - 예) "1천원당 2마일 (해외)" → benefit_value=2, unit_amount=1000
- 마일리지 적립 한도(월 N마일): max_limit=N (단위는 마일리지)
  - max_limit_unit = "마일리지" (원 아님!)
- 행 분리: 국내(1마일)와 해외/면세점(2마일)은 benefit_value 다름 → 별도 행

## 5-1-2. 복잡한 2차원 표 처리 ★
표의 행과 열 모두 조건이 있는 경우(예: 실적×건당금액 조합):
```
예) CJ영화 표:
  실적\건당    | 8,500원 미만 | 8,500원 이상
  30만원 미만  | 2,000원      | 2,000원
  30만원 이상  | 3,000원      | 6,000원
```
→ 이런 표는 **최고값 기준 1행** 생성 (benefit_value=6000, benefit_unit=원)
→ max_count, min_amount 등 조건은 benefit_content에서 파악
→ performance_min=300000 (실적 30만원 이상 조건 있으므로)

---

## 5-1. max_limit / group_max_limit ★ 반드시 월(月) 기준
- **모든 한도 컬럼은 월 기준 금액** — 건당/회당 금액이 아님

### 할인 적용 범위 표현 방식별 파싱
- "N천원~M천원 할인" 범위형 → benefit_value=M(최댓값), benefit_unit="원", 행 분리 금지
  - 예) "CGV 2천원~6천원 청구할인" → benefit_value=6000, benefit_unit="원", 1행
- "월 N원까지 할인 적용 (최대 할인액 M원)" → max_limit=N, M원(건당)은 무시
  - 예) "교통이용금액 월 2만원까지 할인 적용 (최대 할인액 2,000원)" → max_limit=20000
- "건당 N원~M원까지 할인 적용" → min_amount=N, max_limit=M ★ 반드시 M값을 max_limit에 넣을 것
  - 예) "건당 1만원~2만원까지 할인 적용" → min_amount=10000, max_limit=**20000**
  - 예) "건당 3만원~5만원까지 할인 적용" → min_amount=30000, max_limit=**50000**
  - 예) "건당 2만원~5만원까지 할인 적용(1회 최대 할인금액 2,500원)" → min_amount=20000, max_limit=**50000** ← 괄호 안 계산값 무시, 앞의 M값 사용
  - "(1회 최대 할인금액 N원)" → 계산값이므로 완전 무시, max_limit에 절대 사용 금지
  - ★ "건당 N~M까지" 뒤에 "(1회 최대 할인금액 X원)"이 붙어도 max_limit=M 유지 (X원으로 덮어쓰기 금지)
- "5,000원 (건당 2,500원 한도)" → max_limit=5000 (건당 2,500원은 무시)
- "건당 최대 N원", "1회 최대 N원" 단독 표현 → max_limit에 절대 넣지 말 것
- 한도 없으면 max_limit="", group_max_limit=""

---

## 6. benefit_type 분류
- 할인: 결제 시 즉시 차감 (청구할인, 환급할인 포함)
- 캐시백: 결제 후 현금 환급
- 포인트: 포인트리 등 카드사 포인트 적립
- 마일리지: 항공 마일리지
- 서비스: 수치 표현 불가한 부가혜택 (수수료 면제, 이용권 제공, 무료이용 등)
  - benefit_value="", benefit_unit="", max_limit="", group_max_limit=""
  - 행 분리 금지 — 여러 서비스 나열돼도 행 1개
  - ui_title에 서비스 내용 간결 요약 (100자 이내, 예: "공항 라운지 연 2회 무료 이용")
  - category: 서비스 내용 기준 1개 필수 (수수료→생활비, 교통→대중교통/택시, 불명확→기타)
  - performance_level/performance_min: 전월실적 조건이 있으면 추출, 없으면 ""
  - ★ "Great 서비스", "Enjoy 서비스", "Basic 서비스" 등 이름에 "서비스"가 포함되어도
    실제 내용이 할인/캐시백/포인트이면 해당 benefit_type으로 파싱할 것 (이름≠타입)

---

## 7. performance_level 형식 ★ 아래 3가지 케이스만 허용
1. **조건 없음**: performance_level="" (빈값), performance_min=0
2. **하한만**: "전월 실적 N만원 이상" (앞에 "전월 실적 " 필수)
3. **구간**: "전월 실적 N만원 이상 M만원 미만"

이 외의 표현(예: "전월 실적 보전", "실적유예", "N만원 이상 M만원 이상" 등) → performance_level="" 로 출력

---

## 8. 기타 규칙
- on_offline: Online(앱/홈페이지 전용) / Offline(매장 전용) / Both(명시 없거나 전체)
- row_type="안내": 수치 파싱 없이 행 1개, ui_title=섹션 제목
- 수치 변환: 1천=1000, 1만=10000, 5만=50000, 100만=1000000
- unit_amount: "1,500원당 1마일"→1500, "1,000원당 1포인트"→1000, 없으면 ""
- ui_title: 서비스형(benefit_type=서비스)만 직접 작성. 수치형은 ""(Python이 생성)
- **100원/L 형태**: benefit_value=100, benefit_unit="원" (단위 /L 제외)
- **max_count 규칙**:
  - "월 N회" → max_count=N (숫자만)
  - "연 N회" → max_count="연 N회"
  - 금액 계산(연 6만원 ÷ 3만원 = 12 등)으로 유도 절대 금지
  - "월 N매", "N매 이내" → max_count=N
- **표의 "합 계" 행**: 무시할 것 (행 생성 금지)
- **표에서 rowspan으로 묶인 행 ★**: 한도 셀이 rowspan으로 여러 행을 커버하면 group_max_limit, 독립 행은 max_limit
  ```
  예) K-패스카드 표:
  대중교통 할인 | 버스,지하철 | 10% | 5천원     ← rowspan 없음 → max_limit=5000
  생활서비스(rowspan=6) | 이동통신 | 5% | 5천원  ← rowspan=6 → group_max_limit=5000
  생활서비스(carry) | 커피 업종  |    |           ← rowspan carry → group_max_limit=5000
  ...커피/약국/편의점/영화/패스트푸드 동일...
  KB Pay 추가할인 | ... | 5% | 5천원            ← rowspan 없음 → max_limit=5000
  합 계 | | | 1만5천원                           ← 무시
  → 결과: 대중교통=max_limit, 생활서비스6=group_max_limit, KB Pay=max_limit
  ```

JSON 배열만 출력."""

BENEFIT_USER_TEMPLATE = """card_id: {card_id}
benefit_group: {group}
row_type: {row_type}

혜택 내용:
{content}

updated_at: {updated_at}"""


# ─────────────────────────────────────────────
# 파싱 함수
# ─────────────────────────────────────────────
def parse_info(html: str, card_id: str, card_meta: dict) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text("\n", strip=True)[:3000]
    card_name = card_meta.get("card_name", "")

    resp = call_claude(
        INFO_SYSTEM,
        INFO_PROMPT.format(card_id=card_id, card_name=card_name, page_text=page_text)
    )
    try:
        rows = parse_json_response(resp)
        info = rows[0] if rows else {}
    except Exception as e:
        print(f"    ! info 파싱 실패: {e}")
        info = {}

    for f in ["annual_fee_dom_basic", "annual_fee_dom_premium",
              "annual_fee_for_basic", "annual_fee_for_premium", "min_performance"]:
        if not info.get(f) and info.get(f) != 0:
            info[f] = 0

    network_str, is_foreign  = extract_network(soup)
    image_url                = extract_card_image(soup, card_id)
    fee_notes                = extract_annual_fee_notes(soup)
    fee_content              = extract_fee_content(soup)
    dom_fee, for_fee         = extract_annual_fees_rule(soup)
    rule_summary             = _extract_card_summary(soup)

    info["card_id"]             = card_id
    info["company"]             = "국민"
    info["card_name"]           = info.get("card_name") or card_name
    info["card_type"]           = card_meta.get("card_type", "신용")
    info["network"]             = network_str
    info["is_domestic_foreign"] = is_foreign
    info["image_url"]           = image_url
    info["link_url"]            = card_meta.get("link_url", card_meta.get("url", ""))
    info["has_transport"]       = card_meta.get("has_transport", False)
    info["annual_fee_notes"]    = fee_notes
    info["fee_content"]         = fee_content
    if dom_fee or for_fee:
        info["annual_fee_dom_basic"] = dom_fee
        info["annual_fee_for_basic"] = for_fee
    if rule_summary:
        info["summary"] = rule_summary
    info["updated_at"] = now_str()
    return info


def parse_benefit_section(section: dict, card_id: str, seq_ref: list) -> list:
    group     = section["group"]
    title     = section["title"]
    content   = section["content"]
    raw_html  = section.get("raw_html", "")
    is_notice = section["is_notice"]
    row_type  = "안내" if is_notice else "주요혜택"

    filter_lt = section.get("filter_limit_tables", True)
    ui_content_built = build_ui_content(raw_html, title, filter_limit_tables=filter_lt) if raw_html else content
    ui_condition = section.get("ui_condition_text", "")
    if ui_condition:
        ui_content_built += "\n\n[이용 조건]\n" + ui_condition

    user_msg = BENEFIT_USER_TEMPLATE.format(
        card_id=card_id,
        group=group,
        row_type=row_type,
        content=content[:4000],
        updated_at=now_date(),
    )
    resp = call_claude(BENEFIT_SYSTEM, user_msg)

    try:
        rows = parse_json_response(resp)
    except Exception as e:
        print(f"    ! [{title}] 파싱 실패: {e}")
        return []

    result = []
    for row in rows:
        row["benefit_id"]      = f"{card_id}_B{seq_ref[0]:04d}"
        row["card_id"]         = card_id
        row["row_type"]        = row_type
        row["benefit_group"]   = row.get("benefit_group") or group
        row["benefit_content"] = ui_content_built
        row["ui_content"]      = ui_content_built

        cat = str(row.get("category", ""))
        if cat.isdigit():
            _ID2CAT = {str(v): k for k, v in CATEGORY_ID_MAP.items()}
            row["category"] = _ID2CAT.get(cat, "기타")
        if not row.get("category"):
            row["category"] = "기타"
        row["category_id"] = str(CATEGORY_ID_MAP.get(row["category"], 22))

        row = correct_category(row)
        row["ui_title"] = build_ui_title(row)

        if "추첨" in content:
            row["benefit_type"]  = "서비스"
            row["benefit_value"] = ""
            row["benefit_unit"]  = ""
            row["row_type"]      = row_type

        pm = row.get("performance_min", "")
        if str(pm).isdigit() and int(pm) > 2000000:
            matches = re.findall(r'전월.*?(\d+)\s*만원\s*이상', content)
            row["performance_min"] = str(min(int(x)*10000 for x in matches)) if matches else str(int(pm)//10)

        pl = str(row.get("performance_level", "")).strip()
        if pl and not re.match(r'^전월\s*실적\s*\d+만원\s*이상(\s*\d+만원\s*미만)?$', pl):
            row["performance_level"] = ""

        bu = str(row.get("benefit_unit", ""))
        if re.search(r'원\s*/\s*[Ll리터]', bu):
            row["benefit_unit"] = "원"

        mc = str(row.get("max_count", "")).strip()
        if mc:
            m_year = re.match(r'^연\s*(\d+)\s*회?$', mc)
            m_month = re.match(r'^(\d+)\s*회?$', mc)
            if m_year:
                row["max_count"] = f"연 {m_year.group(1)}회"
            elif m_month:
                row["max_count"] = m_month.group(1)
            else:
                row["max_count"] = ""

        for f in ["benefit_value", "performance_min", "performance_max",
                  "min_amount", "max_count", "max_limit", "group_max_limit", "unit_amount"]:
            if row.get(f) in (None, "null", "None"):
                row[f] = ""

        row.setdefault("updated_at", now_date())
        seq_ref[0] += 1
        result.append(row)

    deduped = []
    key_to_idx = {}
    for row in result:
        key = (
            str(row.get("category", "")),
            str(row.get("benefit_value", "")),
            str(row.get("benefit_unit", "")),
            str(row.get("performance_min", "")),
        )
        if key in key_to_idx:
            existing = deduped[key_to_idx[key]]
            new_merchants = row.get("target_merchants", "")
            old_merchants = existing.get("target_merchants", "")
            if new_merchants and new_merchants not in old_merchants:
                existing["target_merchants"] = f"{old_merchants}, {new_merchants}".strip(", ")
            continue
        key_to_idx[key] = len(deduped)
        deduped.append(row)

    has_group_rows = any(
        str(r.get("group_max_limit", "")).strip() not in ("", "0") for r in deduped
    )
    if len(deduped) >= 2 and not has_group_rows:
        all_bv_set = {str(r.get("benefit_value", "")).strip() for r in deduped
                      if str(r.get("max_limit", "")).strip() not in ("", "0")}
        if len(all_bv_set) > 1:
            pass
        else:
            ml_rows = [r for r in deduped
                       if str(r.get("max_limit", "")).strip() not in ("", "0")
                       and not str(r.get("group_max_limit", "")).strip()]
            by_limit: dict[str, list] = {}
            for r in ml_rows:
                by_limit.setdefault(str(r["max_limit"]), []).append(r)
            for ml_val, grp in by_limit.items():
                if len(grp) >= 2 and len({r.get("category", "") for r in grp}) >= 2:
                    bv_set = {str(r.get("benefit_value", "")) for r in grp}
                    if len(bv_set) > 1:
                        continue
                    for r in grp:
                        r["group_max_limit"]      = r["max_limit"]
                        r["group_max_limit_unit"] = r.get("max_limit_unit") or "원"
                        r["max_limit"]            = ""
                        r["max_limit_unit"]       = ""

    return deduped
