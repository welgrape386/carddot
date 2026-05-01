package com.example.demo.service;

import com.example.demo.dto.CardDetailResponse;
import com.example.demo.dto.CardListResponse;
import com.example.demo.entity.Benefit;
import com.example.demo.entity.Card;
import com.example.demo.repository.BenefitRepository;
import com.example.demo.repository.CardRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class CardService {

    private final CardRepository cardRepository;
    private final BenefitRepository benefitRepository; // 새로 추가한 조수 ㅎㅎ

    // 생성자를 통해 2명의 조수(Repository)를 모두 주입받음
    public CardService(CardRepository cardRepository, BenefitRepository benefitRepository) {
        this.cardRepository = cardRepository;
        this.benefitRepository = benefitRepository;
    }

    // [기존 업무] 1. 전체 카드 조회
    @Transactional(readOnly = true)
    public List<CardListResponse> getAllCards() {
        List<Card> cards = cardRepository.findAll();
        return cards.stream()
                .map(card -> new CardListResponse(
                        card.getCardId(), card.getCompany(), card.getCardName(),
                        card.getCardType(), card.getAnnualFeeDomBasic(), 
                        card.getMinPerformance(), card.getTotalMaxBenefit(),
                        card.getSummary(), card.isHasCashback()
                ))
                .collect(Collectors.toList());
    }

    // [새로운 업무] 2. 특정 카드 상세 조회
    @Transactional(readOnly = true)
    public CardDetailResponse getCardDetail(String cardId) {
        // 1. 카드 기본 정보 가져오기 (없으면 에러 던짐)
        Card card = cardRepository.findById(cardId)
                .orElseThrow(() -> new IllegalArgumentException("해당 카드를 찾을 수 없습니다."));

        // 2. 이 카드에 속한 혜택 목록 가져오기
        List<Benefit> benefits = benefitRepository.findByCardId(cardId);

        // 3. 혜택 엔티티(Entity)를 혜택 DTO로 변환
        List<CardDetailResponse.BenefitDetailDto> benefitDtos = benefits.stream()
                .map(b -> {
                    // 카테고리가 NULL일 경우 예외처리 ("기타"로 묶음)
                    String categoryName = (b.getCategory() != null) ? b.getCategory().getCategoryName() : "기타";
                    
                    // 수치(10)와 단위(%)를 합쳐서 "10%" 형태의 텍스트로 만듦
                    String valueText = (b.getBenefitValue() != null ? b.getBenefitValue().toString() : "") 
                                     + (b.getBenefitUnit() != null ? b.getBenefitUnit() : "");

                    return new CardDetailResponse.BenefitDetailDto(
                            categoryName,
                            b.getBenefitTitle(),
                            b.getBenefitContent(),
                            valueText,
                            b.getMaxLimit()
                    );
                }).collect(Collectors.toList());

        // 4. 거대한 하나의 상세 응답 DTO로 조립해서 반환
        return new CardDetailResponse(
                card.getCardId(), card.getCardName(), card.getCompany(),
                card.getCardType(), card.getNetwork(), card.getAnnualFeeDomBasic(),
                card.getAnnualFeeForBasic(), card.getMinPerformance(),
                card.getTotalMaxBenefit(), benefitDtos
        );
    }
}