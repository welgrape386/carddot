"""
utils.py - 공통 유틸 함수
모든 숫자는 콤마 없이 저장
"""

import re


def clean(text: str) -> str:
    """연속 공백 압축 + strip"""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def remove_comma(text: str) -> str:
    """텍스트 내 숫자 천단위 콤마 제거: 10,000 → 10000"""
    return re.sub(r"(\d),(\d)", r"\1\2", text)


def parse_fee(text: str) -> int:
    """
    '본인 30,000원' / '30,000원' / '30000' → 30000
    콤마 제거 후 숫자만 추출
    """
    if not text:
        return 0
    digits = re.sub(r"[^\d]", "", text.replace(",", ""))
    return int(digits) if digits else 0


def parse_networks(raw_list: list) -> list:
    """
    ['Visa/Amex', '국내전용'] → ['Visa', 'Amex']
    국내전용은 네트워크 브랜드가 아니므로 제외
    """
    brand_keywords = ["Visa", "Amex", "Master", "Mastercard", "JCB", "UnionPay"]
    result = []
    for raw in raw_list:
        parts = re.split(r"[/\s]+", raw)
        for part in parts:
            for kw in brand_keywords:
                if kw.lower() in part.lower() and kw not in result:
                    result.append(kw)
    return result


def extract_number(text: str) -> int | None:
    """
    '40만' → 400000 / '3천' → 3000 / '30000' → 30000
    단위 없는 7자리 이상 숫자는 날짜/코드로 간주해 무시
    콤마 제거 후 처리
    """
    if not text:
        return None

    text = remove_comma(text)

    m = re.search(r"([\d.]+)\s*만", text)
    if m:
        return int(float(m.group(1)) * 10000)

    m = re.search(r"([\d.]+)\s*천", text)
    if m:
        return int(float(m.group(1)) * 1000)

    m = re.search(r"\d+", text)
    if m:
        val = int(m.group(0))
        if val >= 10_000_000:
            return None
        return val

    return None


def parse_condition(text: str) -> dict:
    """
    전월실적·최대한도 파싱
    반환: {
        performance_min, performance_max,
        max_limit, max_limit_unit
    }
    """
    result = {
        "performance_min": None,
        "performance_max": None,
        "max_limit":       None,
        "max_limit_unit":  None,
    }
    if not text:
        return result

    text = remove_comma(text)

    # 전월실적: '전월 이용 금액 50만원'
    perfs = []
    for m in re.findall(r"전월\s*(?:이용\s*금액\s*)?([\d.]+)\s*만원", text):
        val = int(float(m) * 10000)
        if 10_000 <= val <= 10_000_000:
            perfs.append(val)
    if perfs:
        result["performance_min"] = min(perfs)
        if len(perfs) > 1:
            result["performance_max"] = max(perfs)

    # 최대한도: '월 1만 M포인트 한도'
    m = re.search(r"월\s*([\d.]+)\s*만\s*(M포인트|포인트|원|마일)", text)
    if m:
        val = int(float(m.group(1)) * 10000)
        if 1 <= val <= 99_999_999:
            result["max_limit"]      = val
            result["max_limit_unit"] = m.group(2).replace("M", "")

    return result
