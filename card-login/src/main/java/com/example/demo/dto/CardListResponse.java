package com.example.demo.dto;

import java.util.List;

public class CardListResponse {
    private String cardId;
    private String cardName;
    private String company;
    private String cardType;
    private boolean hasTransport;
    private int annualFeeDomBasic;
    private int annualFeeDomPremium;
    private int annualFeeForBasic;
    private int annualFeeForPremium;
    private int minPerformance;
    private String summary;
    private String imageUrl;
    private List<String> categoryNames;

    // 생성자 (새로운 스키마 요구사항에 정확히 맞춤)
    public CardListResponse(String cardId, String cardName, String company, String cardType, 
                            boolean hasTransport, int annualFeeDomBasic, int annualFeeDomPremium, 
                            int annualFeeForBasic, int annualFeeForPremium, int minPerformance, 
                            String summary, String imageUrl, List<String> categoryNames) {
        this.cardId = cardId;
        this.cardName = cardName;
        this.company = company;
        this.cardType = cardType;
        this.hasTransport = hasTransport;
        this.annualFeeDomBasic = annualFeeDomBasic;
        this.annualFeeDomPremium = annualFeeDomPremium;
        this.annualFeeForBasic = annualFeeForBasic;
        this.annualFeeForPremium = annualFeeForPremium;
        this.minPerformance = minPerformance;
        this.summary = summary;
        this.imageUrl = imageUrl;
        this.categoryNames = categoryNames;
    }

    // Getters
    public String getCardId() { return cardId; }
    public String getCardName() { return cardName; }
    public String getCompany() { return company; }
    public String getCardType() { return cardType; }
    public boolean isHasTransport() { return hasTransport; }
    public int getAnnualFeeDomBasic() { return annualFeeDomBasic; }
    public int getAnnualFeeDomPremium() { return annualFeeDomPremium; }
    public int getAnnualFeeForBasic() { return annualFeeForBasic; }
    public int getAnnualFeeForPremium() { return annualFeeForPremium; }
    public int getMinPerformance() { return minPerformance; }
    public String getSummary() { return summary; }
    public String getImageUrl() { return imageUrl; }
    public List<String> getCategoryNames() { return categoryNames; }
}