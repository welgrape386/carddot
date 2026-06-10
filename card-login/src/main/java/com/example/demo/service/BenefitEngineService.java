package com.example.demo.service;

import com.example.demo.dto.CalculationResult;
import com.example.demo.entity.Benefit;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class BenefitEngineService {

    // 상수 정의
    private static final double MILEAGE_RATE = 17.0;
    private static final double MR_POINT_RATE = 10.0;
    private static final double POINT_RATE_DEFAULT = 1.0;

    private static final Map<String, Double> POINT_RATE_BY_COMPANY = Map.of(
            "삼성", 1.0,
            "신한", 1.0,
            "국민", 1.0,
            "현대", 0.67
    );

    private static final Map<String, Double> CATEGORY_BASE_AMOUNT = Map.ofEntries(
            Map.entry("슈퍼마켓/생활잡화", 255800.0),
            Map.entry("편의점", 49200.0),
            Map.entry("패션/뷰티", 83000.0),
            Map.entry("온라인쇼핑", 207000.0),
            Map.entry("백화점/아울렛/면세점", 100000.0),
            Map.entry("생활비", 420000.0),
            Map.entry("의료", 134000.0),
            Map.entry("대중교통/택시", 95000.0),
            Map.entry("자동차/주유", 226000.0),
            Map.entry("구독/스트리밍", 32000.0),
            Map.entry("문화/엔터", 42000.0),
            Map.entry("레저/스포츠", 32000.0),
            Map.entry("교육/육아", 28000.0),
            Map.entry("외식", 224000.0),
            Map.entry("배달", 122000.0),
            Map.entry("카페/베이커리", 46000.0),
            Map.entry("여행/숙박", 96000.0),
            Map.entry("항공", 165000.0),
            Map.entry("페이/간편결제", 182000.0),
            Map.entry("반려동물", 121000.0),
            Map.entry("해외", 165000.0)
    );

    // 정규식 패턴
    private static final Pattern PATTERN_OVER = Pattern.compile(
            "([\\d,]+(?:\\.\\d+)?(?:만|천)?)\\s*원\\s*이상\\s*(?:결제|이용|자동납부)\\s*시\\s*(?:최대\\s*)?" +
            "([\\d,]+(?:\\.\\d+)?(?:만|천)?)\\s*(원|포인트|마일리지|마일)");
    private static final Pattern PATTERN_PER = Pattern.compile(
            "([\\d,]+(?:\\.\\d+)?(?:만|천)?)\\s*원\\s*당\\s*(?:최대\\s*)?" +
            "([\\d,]+(?:\\.\\d+)?(?:만|천)?)\\s*(원|포인트|마일리지|마일)");

    // 유틸 메서드
    private double getPointRate(String company) {
        if (company == null) return POINT_RATE_DEFAULT;
        for (Map.Entry<String, Double> entry : POINT_RATE_BY_COMPANY.entrySet()) {
            if (company.contains(entry.getKey())) return entry.getValue();
        }
        return POINT_RATE_DEFAULT;
    }

    private double toNum(String s) {
        if (s == null) return 0.0;
        String clean = s.replace(",", "").trim();
        try {
            if (clean.contains("만")) return Double.parseDouble(clean.replace("만", "")) * 10000;
            if (clean.contains("천")) return Double.parseDouble(clean.replace("천", "")) * 1000;
            return Double.parseDouble(clean);
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }

    private double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }

    private double safeDouble(Integer v) {
        return v != null ? v.doubleValue() : 0.0;
    }

    private String safeStr(String s) {
        return (s != null && !s.trim().equals("null")) ? s.trim() : "";
    }

    // 텍스트 비율 파싱 (2순위)
    private CalculationResult parseContentRatio(String content, double ptRate) {
        if (content == null || content.trim().isEmpty()) return new CalculationResult(0.0, "");

        String clean = content.replace(" ", "");
        Matcher[] matchers = {PATTERN_OVER.matcher(clean), PATTERN_PER.matcher(clean)};

        for (Matcher m : matchers) {
            if (m.find()) {
                double base   = toNum(m.group(1));
                double reward = toNum(m.group(2));
                String unit   = m.group(3);

                if (base <= 0) continue;

                double krw;
                String label;

                if (unit.contains("마일리지") || unit.contains("마일")) {
                    krw   = reward * MILEAGE_RATE;
                    label = "마일리지 1마일 = 17원 기준으로 환산된 적립률입니다.";
                } else if (unit.equals("포인트")) {
                    krw   = reward * ptRate;
                    label = "포인트 1P = " + ptRate + "원 기준으로 환산된 적립률입니다.";
                } else {
                    krw   = reward;
                    label = "전월 최소 실적 달성 시 적용되는 할인율 기준으로 산출되었습니다.";
                }

                double rate = round2(krw / base * 100);
                if (rate > 0) return new CalculationResult(rate, label);
            }
        }
        return new CalculationResult(0.0, "");
    }

    // 핵심 계산 메서드
    // Benefit 엔티티에 아래 getter가 있어야 합니다:
    //   getBenefitGroup(), getBenefitType(), getUiContent(),
    //   getMaxLimitUnit(), getUnitAmount()
    public CalculationResult calculateEffectiveRate(Benefit benefit, String companyName) {
        CalculationResult result = calculateEffectiveRateInternal(benefit, companyName);
        if (result.getRate().doubleValue() >= 100) {
            return new CalculationResult(0.0, "할인율 환산이 어렵습니다.");
        }
        return result;
    }

    private CalculationResult calculateEffectiveRateInternal(Benefit benefit, String companyName) {
        double ptRate = getPointRate(companyName);

        String benefitGroup = safeStr(benefit.getBenefitGroup());
        String uiContent    = safeStr(benefit.getUiContent());

        // 포인트 사용처 행은 할인 혜택이 아니므로 환산 불가
        if (benefitGroup.contains("포인트 사용")) {
            return new CalculationResult(0.0, "할인율 환산이 어렵습니다.");
        }

        // 연간 이용금액 기준 혜택은 월 단위 비교 불가
        if (uiContent.contains("연간 이용금액")) {
            return new CalculationResult(0.0, "연간 이용금액 기준 혜택으로 월 단위 환산이 어렵습니다.");
        }

        double value       = benefit.getBenefitValue() != null ? benefit.getBenefitValue().doubleValue() : 0.0;
        String unit        = safeStr(benefit.getBenefitUnit());
        String benefitType = safeStr(benefit.getBenefitType());

        String category = "기타";
        if (benefit.getCategories() != null && !benefit.getCategories().isEmpty()) {
            category = benefit.getCategories().get(0).getCategoryName();
        }

        double perfMin  = safeDouble(benefit.getPerformanceMin());
        double perfMax  = safeDouble(benefit.getPerformanceMax());
        double maxLimit = safeDouble(benefit.getMaxLimit());
        double unitAmt  = safeDouble(benefit.getUnitAmount());
        String mlUnit   = safeStr(benefit.getMaxLimitUnit());

        double perf    = perfMin > 0 ? perfMin : perfMax;
        double baseAmt = CATEGORY_BASE_AMOUNT.getOrDefault(category, 0.0);

        // 1순위: % 명시
        if (unit.equals("%") && value > 0) {
            boolean isMPoint = benefitType.equals("포인트")
                    && ptRate != 1.0
                    && !benefitGroup.contains("네이버페이");
            double effectivePct = round2(isMPoint ? value * ptRate : value);

            // max_limit 있으면 카테고리 기준 지출 대비 실질 상한 재계산
            if (maxLimit > 0 && baseAmt > 0) {
                double mlWon;
                if (mlUnit.equals("원") || mlUnit.isEmpty()) {
                    mlWon = maxLimit;
                } else if (mlUnit.contains("네이버페이 포인트")) {
                    mlWon = maxLimit;
                } else if (mlUnit.equals("포인트")) {
                    mlWon = maxLimit * ptRate;
                } else {
                    mlWon = 0;
                }
                if (mlWon > 0) {
                    double capped = round2(mlWon / baseAmt * 100);
                    if (capped < effectivePct) {
                        String limitUnit = mlUnit.isEmpty() ? "원" : mlUnit;
                        String label = isMPoint
                                ? String.format("포인트 %.0f%%→M포인트 환산, 월 최대 %,.0f%s 한도 기준 실질할인율입니다.", value, maxLimit, limitUnit)
                                : String.format("명시 할인율 %.0f%%이나 월 최대 %,.0f%s 한도 기준 실질할인율입니다.", value, maxLimit, limitUnit);
                        return new CalculationResult(capped, label);
                    }
                }
            }

            if (isMPoint) {
                return new CalculationResult(effectivePct,
                        String.format("포인트 적립률 %.0f%%에 현대카드 M포인트 환산율(%.2f원/P)을 적용한 실질할인율입니다.", value, ptRate));
            }
            return new CalculationResult(effectivePct, "카드사가 명시한 할인율입니다.");
        }

        // 2순위: content 텍스트 파싱
        CalculationResult contentResult = parseContentRatio(uiContent, ptRate);
        if (contentResult.getRate().doubleValue() > 0) {
            return contentResult;
        }

        // 3순위: maxLimit ÷ performance
        if (maxLimit > 0 && perf > 0) {
            return new CalculationResult(round2(maxLimit / perf * 100),
                    "전월 최소 실적 달성 시 적용되는 할인율 기준으로 산출되었습니다.");
        }

        // 4순위: 블루멤버스 포인트 (이미 % 적립률로 표기)
        if (unit.contains("블루멤버스 포인트") && value > 0) {
            return new CalculationResult(round2(value), "블루멤버스 포인트 1P = 1원 기준 적립률입니다.");
        }

        // 4순위: 포인트 환산
        if ((unit.equals("포인트") || unit.equals("P")) && value > 0) {
            double base = unitAmt > 0 ? unitAmt : (perf > 0 ? perf : baseAmt);
            if (base > 0) {
                String label;
                if (unitAmt > 0) {
                    label = String.format("포인트 1P = 1원 기준, %,.0f원당 %.0fP 적립률입니다.", unitAmt, value);
                } else if (perf > 0) {
                    label = "포인트 1P = 1원 기준으로 환산된 적립률입니다.";
                } else {
                    label = "포인트 1P = 1원 기준, 해당 카테고리 월평균 지출액 대비 적립률입니다.";
                }
                return new CalculationResult(round2(value * ptRate / base * 100), label);
            }
        }

        // 4순위: 마일리지 환산
        if (unit.contains("마일") && value > 0) {
            double base = unitAmt > 0 ? unitAmt : (perf > 0 ? perf : baseAmt);
            if (base > 0) {
                String label = unitAmt > 0
                        ? String.format("마일리지 1마일 = 17원 기준, %,.0f원당 %.0f마일 적립률입니다.", base, value)
                        : "마일리지 1마일 = 17원 기준으로 환산된 적립률입니다.";
                return new CalculationResult(round2(value * MILEAGE_RATE / base * 100), label);
            }
        }

        // 4순위: MR포인트 환산
        if ((unit.equals("MR") || unit.equals("MR포인트")) && value > 0) {
            double base = unitAmt > 0 ? unitAmt : (perf > 0 ? perf : baseAmt);
            if (base > 0) {
                return new CalculationResult(round2(value * MR_POINT_RATE / base * 100),
                        "MR포인트 1MR = 10원 기준으로 환산된 적립률입니다.");
            }
        }

        // 5순위: 원화 고정액 ÷ 기준금액
        if (unit.equals("원") && value > 0) {
            double base = unitAmt > 0 ? unitAmt : (perf > 0 ? perf : baseAmt);
            if (base > 0) {
                String label;
                if (unitAmt > 0) {
                    label = String.format("%,.0f원당 %.0f원 할인율입니다.", unitAmt, value);
                } else if (perf > 0) {
                    label = "전월 최소 실적 달성 시 적용되는 할인율 기준으로 산출되었습니다.";
                } else {
                    label = "월평균 지출액 대비 할인 비율로 산출되었습니다. (실제 이용금액에 따라 다를 수 있습니다)";
                }
                return new CalculationResult(round2(value / base * 100), label);
            }
        }

        return new CalculationResult(0.0, "할인율 환산이 어렵습니다.");
    }
}