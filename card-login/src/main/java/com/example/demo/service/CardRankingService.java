package com.example.demo.service;

import com.example.demo.dto.CardRankingResponse;
import com.example.demo.dto.RankingFilterRequest;
import com.example.demo.entity.VCardList;
import com.example.demo.repository.RankingSpecification;
import com.example.demo.repository.VCardListRepository;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class CardRankingService {

    private final VCardListRepository vCardListRepository;

    public CardRankingService(VCardListRepository vCardListRepository) {
        this.vCardListRepository = vCardListRepository;
    }

    public List<CardRankingResponse> getCardRanking(RankingFilterRequest request) {
        // 정렬 기준: totalScore(인기순)
        Sort sort = Sort.by(Sort.Direction.DESC, "totalScore");

        // 필터+정렬 한 번에 적용해 DB에서 뷰 가져오기
        List<VCardList> rawList = vCardListRepository.findAll(RankingSpecification.filterRanking(request), sort);

        // 프론트가 요구한 형식(Response DTO)으로 변환하면서 1등부터 순위 매김
        List<CardRankingResponse> rankingList = new ArrayList<>();
        int currentRank = 1;

        for (VCardList card : rawList) {
            rankingList.add(new CardRankingResponse(
                    currentRank++, // 1부터 순서대로 증가하며 순위 부여
                    card.getCardId(),
                    card.getCardName(),
                    card.getCompany(),
                    card.getCardType(),
                    card.getAnnualFeeDomBasic(),
                    card.getAnnualFeeDomPremium(),
                    card.getAnnualFeeForBasic(),
                    card.getAnnualFeeForPremium(),
                    card.getMinPerformance(),
                    card.getSummary(), // 주요 혜택
                    card.getDetailClick(),
                    card.getUrlClick(),
                    card.getTotalScore(),
                    card.getImageUrl()
            ));
        }

        return rankingList;
    }
}