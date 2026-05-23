package com.example.demo.dto;

import java.util.List;

public class CardCompareResponse {
    // 기본 비교 항목
    private String cardId;
    private String company;
    private String cardName;
    private String cardType;
    private String network;
    private int minPerformance;
    private String imageUrl; // 프론트 화면 표시용
    
    // 종합 점수
    private CardScoreResponse scores; 
    
    // 혜택 리스트
    private List<BenefitCompareDto> benefits;

    public CardCompareResponse(String cardId, String company, String cardName, String cardType, 
                               String network, int minPerformance, String imageUrl, 
                               CardScoreResponse scores, List<BenefitCompareDto> benefits) {
        this.cardId = cardId;
        this.company = company;
        this.cardName = cardName;
        this.cardType = cardType;
        this.network = network;
        this.minPerformance = minPerformance;
        this.imageUrl = imageUrl;
        this.scores = scores;
        this.benefits = benefits;
    }

    // Getter
    public String getCardId() { return cardId; }
    public String getCompany() { return company; }
    public String getCardName() { return cardName; }
    public String getCardType() { return cardType; }
    public String getNetwork() { return network; }
    public int getMinPerformance() { return minPerformance; }
    public String getImageUrl() { return imageUrl; }
    public CardScoreResponse getScores() { return scores; }
    public List<BenefitCompareDto> getBenefits() { return benefits; }
}