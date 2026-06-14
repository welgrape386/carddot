package com.example.demo.service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;

import com.example.demo.common.PersonaWeight;
import com.example.demo.dto.CalculationResult;
import com.example.demo.dto.CardScoreResponse;
import com.example.demo.entity.Benefit;
import com.example.demo.entity.Card;
import com.example.demo.entity.Category;
import com.example.demo.repository.BenefitRepository;

@Service
public class CardScoreService {

    private final BenefitRepository benefitRepository;
    private final BenefitEngineService benefitEngineService;
    
    // BenefitEngineService와 동일한 카테고리 기준 지출액
    private static final Map<String, Double> CATEGORY_BASE_AMOUNT = Map.ofEntries(
            Map.entry("슈퍼마켓/생활잡화", 255800.0), Map.entry("편의점", 49200.0),
            Map.entry("패션/뷰티", 83000.0), Map.entry("온라인쇼핑", 207000.0),
            Map.entry("백화점/아울렛/면세점", 100000.0), Map.entry("생활비", 420000.0),
            Map.entry("의료", 134000.0), Map.entry("대중교통/택시", 95000.0),
            Map.entry("자동차/주유", 226000.0), Map.entry("구독/스트리밍", 32000.0),
            Map.entry("문화/엔터", 42000.0), Map.entry("레저/스포츠", 32000.0),
            Map.entry("교육/육아", 28000.0), Map.entry("외식", 224000.0),
            Map.entry("배달", 122000.0), Map.entry("카페/베이커리", 46000.0),
            Map.entry("여행/숙박", 96000.0), Map.entry("항공", 165000.0),
            Map.entry("페이/간편결제", 182000.0), Map.entry("반려동물", 121000.0),
            Map.entry("해외", 165000.0)
    );

    // 생성자
    public CardScoreService(BenefitRepository benefitRepository,
    		BenefitEngineService benefitEngineService) {
        this.benefitRepository = benefitRepository;
        this.benefitEngineService = benefitEngineService;
    }

    public CardScoreResponse getCardScores(Card card, String personaType) {
    	// 이미 카드 객체 받았으니 혜택 목록만 가져오기
        List<Benefit> allBenefits = benefitRepository.findByCardId(card.getCardId());
        
        // 실적 구간에 맞는 혜택만 필터링
        int targetPerformance = card.getMinPerformance();
        
        List<Benefit> validBenefits = allBenefits.stream()
            .filter(b -> {
                // Benefit 엔티티의 최소/최대 실적 값 가져오기 (null 처리)
                int min = (b.getPerformanceMin() != null) ? b.getPerformanceMin() : 0;
                // 최대 실적이 없거나 0이면 상한 없는 것으로 간주(Integer.MAX_VALUE)
                int max = (b.getPerformanceMax() != null && b.getPerformanceMax() > 0) 
                          ? b.getPerformanceMax() : Integer.MAX_VALUE;
                
                // 타겟 실적이 해당 구간 안에 포함되는지 확인
                return targetPerformance >= min && targetPerformance <= max; 
            })
            .toList();
        
        Integer domFee = card.getAnnualFeeDomBasic();
        Integer forFee = card.getAnnualFeeForBasic();
        int targetFee = (domFee != null && domFee > 0) ? domFee : ((forFee != null && forFee > 0) ? forFee : 0);
        
        // 메서드 호출 시 Card 객체 전체 넘겨줌
        int personaScore = calculatePersonaScore(card, validBenefits, personaType);
        int annualFeeScore = calculateAnnualFeeScore(targetFee);
        int performanceScore = calculatePerformanceScore(card.getMinPerformance());
        int diversityScore = calculateDiversityScore(validBenefits);
        int limitScore = calculateLimitScore(card, validBenefits);

        int totalScore = (int) Math.round(
        		(personaScore * 0.40) +
        		(limitScore * 0.30) +
        		(annualFeeScore * 0.10) +
        		(performanceScore * 0.10) +
        		(diversityScore * 0.10)
        		);

        return new CardScoreResponse(totalScore, personaScore, annualFeeScore, performanceScore, diversityScore, limitScore);
    }

    // 1. 페르소나
    private int calculatePersonaScore(Card card, List<Benefit> benefits, String personaType) {
        Map<Long, Double> weights = PersonaWeight.getWeightsByPersona(personaType);
        
        // 카테고리별 누적 '실질 혜택 금액(원)' 저장
        Map<Long, Double> categoryKrwBenefits = new HashMap<>();

        for (Benefit b : benefits) {
            if (b.getCategories() == null || b.getCategories().isEmpty()) continue;
            
            double expectedKrw = 0.0;
            
            if ("서비스".equals(b.getBenefitType())) {
                expectedKrw = 10000.0; // 프리미엄 서비스 혜택은 월 1만원 가치로 고정
            } else {
                // 엔진에서 산출된 비율(%)을 다시 체감 금액(원)으로 복원
                CalculationResult calcResult = benefitEngineService.calculateEffectiveRate(b, card.getCompany());
                double effectiveRate = calcResult.getRate().doubleValue();
                
                String catName = b.getCategories().get(0).getCategoryName();
                double baseAmt = CATEGORY_BASE_AMOUNT.getOrDefault(catName, 0.0);
                double expectedBenefit = baseAmt * (effectiveRate / 100.0);
                
                // 엔진의 비율과 카드 개별 한도(원화 환산) 중 작은 값을 실제 혜택 금액으로 결정
                double cardLimit = (b.getMaxLimit() != null && b.getMaxLimit() > 0) 
                        ? convertLimitToKrw(b.getMaxLimit(), b.getMaxLimitUnit(), card.getCompany()) 
                        : Double.MAX_VALUE;
                
                expectedKrw = Math.min(expectedBenefit, cardLimit);
            }
            
            // 동일 카테고리에 속한 혜택 금액 합산 (여러 가맹점 혜택을 더하는 Sum 로직의 장점 유지)
            for (Category cat : b.getCategories()) {
                Long catId = cat.getCategoryId();
                double currentSum = categoryKrwBenefits.getOrDefault(catId, 0.0);
                categoryKrwBenefits.put(catId, currentSum + expectedKrw);
            }
        }
        
        double totalWeightedScore = 0;
        
        // 누적된 혜택 금액을 카테고리 단위로 순회하며 최종 점수 계산
        for (Map.Entry<Long, Double> entry : categoryKrwBenefits.entrySet()) {
            Long catId = entry.getKey();
            Double totalKrw = entry.getValue(); 

            double weight = weights.getOrDefault(catId, 0.0125);
            
            // 한 카테고리에서 '월 10,000원' 혜택 달성 시 해당 카테고리 100점
            // 이렇게 하면 편의점 1만원과 주유 1만원이 동등한 100점으로 취급되어 페르소나의 왜곡 사라짐
            double normalizedValue = Math.min(100.0, (totalKrw / 10000.0) * 100);

            totalWeightedScore += (normalizedValue * weight);
        }
        
        // 가중치 총합(0.8) 스케일업
        return (int) Math.min(100, Math.round(totalWeightedScore / 0.8));
    }

    // 2. 연회비 역배점 (기준: 국내/해외 기본 연회비 50,000원)
    private int calculateAnnualFeeScore(Integer fee) {
        if (fee == null || fee == 0) return 100; // 연회비 없는 카드는 100점 만점
        return Math.max(0, 100 - (fee * 100 / 50000));
    }

    // 3. 전월 실적 역배점 (기준: 1,000,000원)
    private int calculatePerformanceScore(Integer performance) {
        if (performance == null || performance == 0) return 100; // 무조건 혜택 카드(실적 조건 없음)는 100점 만점
        return Math.max(0, 100 - (performance * 100 / 1000000));
    }

    // 4. 혜택 다양성 (기준: 커버하는 카테고리 종류 7개 이상이면 100점)
    private int calculateDiversityScore(List<Benefit> benefits) {
        long uniqueCategoryCount = benefits.stream()
        		.filter(b -> b.getCategories() != null)
                .flatMap(b -> b.getCategories().stream()) // 리스트 안의 카테고리들 모두 꺼내서 펼침
                .map(Category::getCategoryId)
                .distinct()
                .count();
        
        return (int) Math.min(100, (uniqueCategoryCount * 100) / 7);
    }

    // 5. 할인 한도 (기준: 월 누적 한도 50,000원)
    private int calculateLimitScore(Card card, List<Benefit> benefits) {
        double ungroupedExpectedBenefit = 0;
        
        // 그룹별 예상 혜택 합산 및 그룹 최대 한도(원화 환산) 저장용 Map
        Map<String, Double> groupExpectedBenefits = new HashMap<>();
        Map<String, Double> groupLimitsInKrw = new HashMap<>();
        
        for (Benefit b : benefits) {
            if (b.getCategories() == null || b.getCategories().isEmpty()) continue;

            // '서비스' 혜택은 실질 금액(예: 월 10,000원)으로 고정 평가 후 통합 한도 열외
            if ("서비스".equals(b.getBenefitType())) {
                ungroupedExpectedBenefit += 10000.0;
                continue;
            }

            String categoryName = b.getCategories().get(0).getCategoryName();
            CalculationResult calcResult = benefitEngineService.calculateEffectiveRate(b, card.getCompany());
            double effectiveRate = calcResult.getRate().doubleValue();

            double baseAmt = CATEGORY_BASE_AMOUNT.getOrDefault(categoryName, 0.0);
            double expectedBenefit = baseAmt * (effectiveRate / 100.0);
            
            // 개별 한도(max_limit) 원화 환산 및 적용
            double cardLimit = (b.getMaxLimit() != null && b.getMaxLimit() > 0) 
                    ? convertLimitToKrw(b.getMaxLimit(), b.getMaxLimitUnit(), card.getCompany()) 
                    : Double.MAX_VALUE;
            
            double realBenefit = Math.min(expectedBenefit, cardLimit);
            
            // 그룹(통합) 한도 판별
            String groupName = b.getBenefitGroup();
            Number groupMaxLimit = b.getGroupMaxLimit();
            
            if (groupName != null && !groupName.isEmpty() && groupMaxLimit != null && groupMaxLimit.doubleValue() > 0) {
                // 그룹 예상 혜택 누적
                double currentSum = groupExpectedBenefits.getOrDefault(groupName, 0.0);
                groupExpectedBenefits.put(groupName, currentSum + realBenefit);
                
                // 그룹 최대 한도 원화 환산 후 저장 (한 번만 저장하면 됨)
                if (!groupLimitsInKrw.containsKey(groupName)) {
                    double convertedGroupLimit = convertLimitToKrw(groupMaxLimit, b.getGroupMaxLimitUnit(), card.getCompany());
                    groupLimitsInKrw.put(groupName, convertedGroupLimit);
                }
            } else {
                ungroupedExpectedBenefit += realBenefit;
            }
        }
        
        // 그룹별 혜택 총합 계산 (원화로 환산된 통합 한도 적용)
        double totalExpectedBenefit = ungroupedExpectedBenefit;
        for (String group : groupExpectedBenefits.keySet()) {
            double groupSum = groupExpectedBenefits.get(group);
            double groupLimit = groupLimitsInKrw.get(group);
            
            totalExpectedBenefit += Math.min(groupSum, groupLimit);
        }
        
        return (int) Math.min(100, Math.round((totalExpectedBenefit / 50000.0) * 100));
    }

    // 한도 금액 단위(Unit)를 원화로 표준화
    private double convertLimitToKrw(Number limit, String unit, String companyName) {
        if (limit == null || limit.doubleValue() <= 0) return Double.MAX_VALUE;
        
        // 어떤 타입이든 double로 변환 후 계산
        double limitVal = limit.doubleValue();
        
        if (unit == null || unit.isEmpty() || "원".equals(unit)) return limitVal;

        if (unit.contains("마일")) return limitVal * 17.0; // 대한항공/아시아나 마일리지
        if ("MR".equals(unit) || "MR포인트".equals(unit)) return limitVal * 10.0; // 아멕스 MR

        // 포인트 환산 (현대카드 M포인트 1P = 0.67원)
        if (unit.contains("포인트") || "P".equals(unit)) {
            double pointRate = 1.0;
            if (companyName != null && companyName.contains("현대")) {
                if (!unit.contains("블루멤버스") && !unit.contains("네이버페이")) {
                    pointRate = 0.67;
                }
            }
            return limitVal * pointRate;
        }

        return limitVal; // 기타 알 수 없는 단위는 1:1 처리
    }
}