package com.example.demo.dto;

public class CardRankingResponse {
    private int rank; // 랭킹 순위 (1, 2, 3...)
    private String cardId;
    private String cardName;
    private String company;
    private String cardType;
    private int annualFeeDomBasic;
    private int annualFeeDomPremium;
    private int annualFeeForBasic;
    private int annualFeeForPremium;
    private int minPerformance;
    private String summary;
    private int detailClick;
    private int urlClick;
    private int totalScore;
    private String imageUrl;

    public CardRankingResponse(int rank, String cardId, String cardName, String company, 
                               String cardType, int annualFeeDomBasic, int annualFeeDomPremium,
                               int annualFeeForBasic, int annualFeeForPremium, int minPerformance, 
                               String summary, int detailClick, int urlClick, int totalScore,
                               String imageUrl) {
        this.rank = rank;
        this.cardId = cardId;
        this.cardName = cardName;
        this.company = company;
        this.cardType = cardType;
        this.annualFeeDomBasic = annualFeeDomBasic;
        this.annualFeeDomPremium = annualFeeDomPremium;
        this.annualFeeForBasic = annualFeeForBasic;
        this.annualFeeForPremium = annualFeeForPremium;
        this.minPerformance = minPerformance;
        this.summary = summary;
        this.detailClick = detailClick;
        this.urlClick = urlClick;
        this.totalScore = totalScore;
        this.imageUrl = imageUrl;
    }

    // Getters
    public int getRank() { return rank; }
    public String getCardId() { return cardId; }
    public String getCardName() { return cardName; }
    public String getCompany() { return company; }
    public String getCardType() { return cardType; }
    public int getAnnualFeeDomBasic() { return annualFeeDomBasic; }
    public int getAnnualFeeDomPremium() { return annualFeeDomPremium; }
    public int getAnnualFeeForBasic() { return annualFeeForBasic; }
    public int getAnnualFeeForPremium() { return annualFeeForPremium; }
    public int getMinPerformance() { return minPerformance; }
    public String getSummary() { return summary; }
    public int getDetailClick() { return detailClick; }
    public int getUrlClick() { return urlClick; }
    public int getTotalScore() { return totalScore; }
    public String getImageUrl() { return imageUrl; }
}