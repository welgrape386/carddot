package com.example.demo.service;

import com.example.demo.dto.CalculationResult;
import com.example.demo.entity.Benefit;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class BenefitEngineService {

    // 1. 상수 정의
    private static final double MILEAGE_RATE = 17.0;
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

    // 2. 정규식 패턴 컴파일 (텍스트 파싱용)
    private static final Pattern PATTERN_OVER = Pattern.compile("([\\d,]+(?:\\.\\d+)?(?:만|천)?)\\s*원\\s*이상\\s*(?:결제|이용|자동납부)\\s*시\\s*(?:최대\\s*)?([\\d,]+(?:\\.\\d+)?(?:만|천)?)\\s*(원|포인트|마일리지|마일)");
    private static final Pattern PATTERN_PER = Pattern.compile("([\\d,]+(?:\\.\\d+)?(?:만|천)?)\\s*원\\s*당\\s*(?:최대\\s*)?([\\d,]+(?:\\.\\d+)?(?:만|천)?)\\s*(원|포인트|마일리지|마일)");

    // --- 유틸 메서드 ---
    private double getPointRate(String company) {
        if (company == null) return POINT_RATE_DEFAULT;
        for (Map.Entry<String, Double> entry : POINT_RATE_BY_COMPANY.entrySet()) {
            if (company.contains(entry.getKey())) {
                return entry.getValue();
            }
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

    // --- 텍스트 비율 파싱 ---
    private CalculationResult parseContentRatio(String content, double ptRate) {
        if (content == null || content.trim().isEmpty()) return new CalculationResult(0.0, "");
        
        String cleanContent = content.replace(" ", ""); // 공백 제거 후 검사
        Matcher[] matchers = { PATTERN_OVER.matcher(cleanContent), PATTERN_PER.matcher(cleanContent) };

        for (Matcher m : matchers) {
            if (m.find()) {
                double base = toNum(m.group(1));
                double reward = toNum(m.group(2));
                String unit = m.group(3);

                if (base <= 0) continue;

                double krw;
                String label;

                if (unit.contains("마일")) {
                    krw = reward * MILEAGE_RATE;
                    label = "마일리지 1마일 = 17원 기준으로 환산된 적립률입니다.";
                } else if (unit.equals("포인트")) {
                    krw = reward * ptRate;
                    label = "포인트 1P = " + ptRate + "원 기준으로 환산된 적립률입니다.";
                } else {
                    krw = reward;
                    label = "텍스트 명시 조건 기준으로 산출되었습니다.";
                }

                double rate = (krw / base) * 100;
                if (rate > 0) return new CalculationResult(rate, label);
            }
        }
        return new CalculationResult(0.0, "");
    }

    // 💡 핵심 계산 메서드 (외부에서 호출)
    public CalculationResult calculateEffectiveRate(Benefit benefit, String companyName) {
        double ptRate = getPointRate(companyName);
        
        // 혜택 엔티티에서 값 추출 (Null 처리 포함)
        double value = benefit.getBenefitValue() != null ? benefit.getBenefitValue().doubleValue() : 0.0;
        String unit = benefit.getBenefitUnit() != null ? benefit.getBenefitUnit().trim() : "";
        
        // 카테고리 추출 (첫 번째 카테고리 기준)
        String category = "기타";
        if (benefit.getCategories() != null && !benefit.getCategories().isEmpty()) {
            category = benefit.getCategories().get(0).getCategoryName();
        }

        double perfMin = benefit.getPerformanceMin() != null ? benefit.getPerformanceMin() : 0;
        double perfMax = benefit.getPerformanceMax() != null ? benefit.getPerformanceMax() : 0;
        double maxLimit = benefit.getMaxLimit() != null ? benefit.getMaxLimit() : 0;

        double perf = perfMin > 0 ? perfMin : perfMax;
        double baseAmt = CATEGORY_BASE_AMOUNT.getOrDefault(category, 0.0);

        // 1순위: % 명시
        if (unit.equals("%") && value > 0) {
            return new CalculationResult(value, "카드사가 명시한 할인율입니다.");
        }

        // 2순위: content 텍스트 파싱
        CalculationResult contentResult = parseContentRatio(benefit.getUiContent(), ptRate);
        if (contentResult.getRate().doubleValue() > 0) {
            return contentResult;
        }

        // 3순위: maxLimit ÷ performance
        if (maxLimit > 0 && perf > 0) {
            return new CalculationResult((maxLimit / perf) * 100, "전월 최소 실적 달성 시 적용되는 할인율 기준으로 산출되었습니다.");
        }

        // 4순위: 포인트/마일리지 환산
        if ((unit.equals("포인트") || unit.equals("P")) && value > 0) {
            double base = perf > 0 ? perf : baseAmt;
            if (base > 0) {
                String label = perf > 0 ? "포인트 1P = 1원 기준으로 환산된 적립률입니다." 
                                        : "포인트 1P = 1원 기준, 해당 카테고리 월평균 지출액 대비 적립률입니다.";
                return new CalculationResult((value * ptRate / base) * 100, label);
            }
        }

        if ((unit.contains("마일")) && value > 0) {
            double base = perf > 0 ? perf : baseAmt;
            if (base > 0) {
                return new CalculationResult((value * MILEAGE_RATE / base) * 100, "마일리지 1마일 = 17원 기준으로 환산된 적립률입니다.");
            }
        }

        // 5순위: 원화 고정액 ÷ 기준금액
        if (unit.equals("원") && value > 0) {
            double base = perf > 0 ? perf : baseAmt;
            if (base > 0) {
                String label = perf > 0 ? "전월 최소 실적 달성 시 적용되는 할인율 기준으로 산출되었습니다." 
                                        : "월평균 지출액 대비 할인 비율로 산출되었습니다.";
                return new CalculationResult((value / base) * 100, label);
            }
        }

        // 모든 조건 불일치
        return new CalculationResult(0.0, "할인율 환산이 어렵습니다.");
    }
}