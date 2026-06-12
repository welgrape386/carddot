package com.example.demo.service;

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
        List<Benefit> benefits = benefitRepository.findByCardId(card.getCardId());

        // 메서드 호출 시 Card 객체 전체 넘겨줌
        int personaScore = calculatePersonaScore(card, benefits, personaType);
        int annualFeeScore = calculateAnnualFeeScore(card.getAnnualFeeDomBasic());
        int performanceScore = calculatePerformanceScore(card.getMinPerformance());
        int diversityScore = calculateDiversityScore(benefits);
        int limitScore = calculateLimitScore(card, benefits);

        int totalScore = (personaScore + annualFeeScore + performanceScore + diversityScore + limitScore) / 5;

        return new CardScoreResponse(totalScore, personaScore, annualFeeScore, performanceScore, diversityScore, limitScore);
    }

    // 1. 페르소나
    private int calculatePersonaScore(Card card, List<Benefit> benefits, String personaType) {
        Map<Long, Double> weights = PersonaWeight.getWeightsByPersona(personaType);
        double totalScore = 0;

        for (Benefit b : benefits) {
            // 카테고리가 아예 없거나 혜택 수치가 없는 경우 제외
            if (b.getCategories() == null || b.getCategories().isEmpty() || b.getBenefitValue() == null) continue;

            // 하나의 혜택이 여러 카테고리에 속할 수 있으므로, 그 중 가장 높은 가중치를 적용
            double maxWeight = 0.0125;
            for (Category cat : b.getCategories()) {
                double weight = weights.getOrDefault(cat.getCategoryId(), 0.0125);
                if (weight > maxWeight) {
                    maxWeight = weight;
                }
            }
            
            CalculationResult calcResult = benefitEngineService.calculateEffectiveRate(b, card.getCompany());
            double effectiveRate = calcResult.getRate().doubleValue();
            
            double normalizedValue = Math.min(100.0, (effectiveRate / 10.0) * 100); // 15에서 10으로 수정

            totalScore += (normalizedValue * maxWeight);
        }
        return (int) Math.min(100, Math.round(totalScore));
    }

    // 2. 연회비 역배점 (기준: 국내 기본 연회비 50,000원)
    private int calculateAnnualFeeScore(Integer fee) {
        if (fee == null || fee == 0) return 100; // 체크카드나 연회비 면제 카드는 100점 만점
        return Math.max(0, 100 - (fee * 100 / 50000));
    }

    // 3. 전월 실적 역배점 (기준: 1,000,000원)
    private int calculatePerformanceScore(Integer performance) {
        if (performance == null || performance == 0) return 100; // 무조건 혜택 카드(실적 조건 없음)는 100점 만점
        return Math.max(0, 100 - (performance * 100 / 1000000));
    }

    // 4. 혜택 다양성 (기준: 커버하는 카테고리 종류 12개 이상이면 100점)
    private int calculateDiversityScore(List<Benefit> benefits) {
        long uniqueCategoryCount = benefits.stream()
        		.filter(b -> b.getCategories() != null)
                .flatMap(b -> b.getCategories().stream()) // 리스트 안의 카테고리들을 모두 꺼내서 펼침
                .map(Category::getCategoryId)
                .distinct()
                .count();
        
        return (int) Math.min(100, (uniqueCategoryCount * 100) / 12);
    }

    // 5. 할인 한도 (기준: 월 누적 한도 50,000원)
    private int calculateLimitScore(Card card, List<Benefit> benefits) {
    	double totalExpectedBenefit = 0;
        
    	for (Benefit b : benefits) {
            if (b.getCategories() == null || b.getCategories().isEmpty()) continue;

            String categoryName = b.getCategories().get(0).getCategoryName();
            CalculationResult calcResult = benefitEngineService.calculateEffectiveRate(b, card.getCompany());
            double effectiveRate = calcResult.getRate().doubleValue();

            double baseAmt = CATEGORY_BASE_AMOUNT.getOrDefault(categoryName, 0.0);

            // 해당 혜택으로 한 달에 체감할 수 있는 실제 혜택 금액
            double expectedBenefit = baseAmt * (effectiveRate / 100.0);
            totalExpectedBenefit += expectedBenefit;
        }
        
    	// 월 50,000원 이상 실제 혜택을 볼 수 있다면 100점 만점
        return (int) Math.min(100, Math.round((totalExpectedBenefit / 50000.0) * 100));
    }
}