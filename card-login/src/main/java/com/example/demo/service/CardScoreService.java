package com.example.demo.service;

import com.example.demo.common.PersonaWeight;
import com.example.demo.dto.CardScoreResponse;
import com.example.demo.entity.Benefit;
import com.example.demo.entity.Card;
import com.example.demo.repository.BenefitRepository;
import com.example.demo.repository.CardRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
public class CardScoreService {

    private final CardRepository cardRepository;
    private final BenefitRepository benefitRepository;

    // 생성자
    public CardScoreService(CardRepository cardRepository, BenefitRepository benefitRepository) {
        this.cardRepository = cardRepository;
        this.benefitRepository = benefitRepository;
    }

    public CardScoreResponse getCardScores(String cardId, String personaType) {
        Card card = cardRepository.findById(cardId)
                .orElseThrow(() -> new IllegalArgumentException("카드를 찾을 수 없습니다."));
        
        List<Benefit> benefits = benefitRepository.findByCardId(cardId);

        // 직접 생성자에 값 넣어서 객체 생성
        return new CardScoreResponse(
                calculatePracticality(benefits, personaType),
                calculateAnnualFeeScore(card.getAnnualFeeDomBasic()),
                calculatePerformanceScore(card.getMinPerformance()),
                calculateDiversityScore(benefits),
                calculateLimitScore(benefits)
        );
    }

    // 1. 페르소나
    // 표준화 후 수정 예정
    private int calculatePracticality(List<Benefit> benefits, String personaType) {
        Map<Long, Double> weights = PersonaWeight.getWeightsByPersona(personaType);
        double totalScore = 0;

        for (Benefit b : benefits) {
            // 카테고리가 아예 없거나 혜택 수치가 없는 경우 제외
            if (b.getCategories() == null || b.getCategories().isEmpty() || b.getBenefitValue() == null) continue;

            // 하나의 혜택이 여러 카테고리에 속할 수 있으므로, 그 중 가장 높은 가중치를 적용
            double maxWeight = 0.0125;
            for (com.example.demo.entity.Category cat : b.getCategories()) {
                double weight = weights.getOrDefault(cat.getCategoryId(), 0.0125);
                if (weight > maxWeight) {
                    maxWeight = weight;
                }
            }
            
            double benefitRate = b.getBenefitValue().doubleValue();
            double normalizedValue = Math.min(100.0, (benefitRate / 15.0) * 100);

            totalScore += (normalizedValue * maxWeight);
        }
        return (int) Math.min(100, Math.round(totalScore));
    }

    // 2. 연회비 역배점 (기준: 국내 기본 연회비 50,000원)
    private int calculateAnnualFeeScore(int fee) {
        if (fee == 0) return 100; // 체크카드나 연회비 면제 카드는 100점 만점
        return Math.max(0, 100 - (fee * 100 / 50000));
    }

    // 3. 전월 실적 역배점 (기준: 1,000,000원)
    private int calculatePerformanceScore(int performance) {
        if (performance == 0) return 100; // 무조건 혜택 카드(실적 조건 없음)는 100점 만점
        return Math.max(0, 100 - (performance * 100 / 1000000));
    }

    // 4. 혜택 다양성 (기준: 커버하는 카테고리 종류 12개 이상이면 100점)
    private int calculateDiversityScore(List<Benefit> benefits) {
        long uniqueCategoryCount = benefits.stream()
        		.filter(b -> b.getCategories() != null)
                .flatMap(b -> b.getCategories().stream()) // 리스트 안의 카테고리들을 모두 꺼내서 펼침
                .map(cat -> cat.getCategoryId())
                .distinct()
                .count();
        
        return (int) Math.min(100, (uniqueCategoryCount * 100) / 12);
    }

    // 5. 할인 한도 (기준: 월 누적 한도 50,000원)
    // 표준화 후 수정 예정
    private int calculateLimitScore(List<Benefit> benefits) {
        // 한도가 null(제한 없음)이면서, 실제 혜택률이 존재하는 무제한 카드는 100점 처리
        boolean hasUnlimited = benefits.stream()
                .anyMatch(b -> b.getMaxLimit() == null && b.getBenefitValue() != null);
        if (hasUnlimited) return 100;

        double totalLimit = benefits.stream()
                .filter(b -> b.getMaxLimit() != null)
                .mapToDouble(Benefit::getMaxLimit)
                .sum();
                
        return (int) Math.min(100, Math.round((totalLimit * 100) / 50000));
    }
}