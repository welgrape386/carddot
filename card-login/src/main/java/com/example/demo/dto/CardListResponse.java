package com.example.demo.dto;

import java.util.List;

public class CardListResponse {
    private String cardId;
    private String company;
    private String cardName;
    private String cardType;
    private int annualFee;
    private int minPerformance;
    private Integer totalMaxBenefit;
    private String summary;
    private boolean hasEvent;
    
    // 사용자가 선택한 카테고리의 혜택 수치들 (["스타벅스 5%", "대중교통 10%"])
    private List<String> categoryBenefits;

    // 생성자 (기본 정보 초기화용)
    public CardListResponse(String cardId, String company, String cardName, String cardType, 
                            int annualFee, int minPerformance, Integer totalMaxBenefit, 
                            String summary, boolean hasEvent) {
        this.cardId = cardId;
        this.company = company;
        this.cardName = cardName;
        this.cardType = cardType;
        this.annualFee = annualFee;
        this.minPerformance = minPerformance;
        this.totalMaxBenefit = totalMaxBenefit;
        this.summary = summary;
        this.hasEvent = hasEvent;
    }

    // Getter 및 Setter (카테고리 혜택 세팅용)
    public String getCardId() { return cardId; }
    public String getCompany() { return company; }
    public String getCardName() { return cardName; }
    public String getCardType() { return cardType; }
    public int getAnnualFee() { return annualFee; }
    public int getMinPerformance() { return minPerformance; }
    public Integer getTotalMaxBenefit() { return totalMaxBenefit; }
    public String getSummary() { return summary; }
    public boolean isHasEvent() { return hasEvent; }
    
    public List<String> getCategoryBenefits() { return categoryBenefits; }
    public void setCategoryBenefits(List<String> categoryBenefits) { 
        this.categoryBenefits = categoryBenefits; 
    }
}