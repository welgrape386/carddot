package com.example.demo.dto;

public class CardSearchResponse {
    private String cardId;
    private String imageUrl;
    private String cardType; // 신용/체크
    private String company;
    private String cardName;
    private int annualFee;

    // 생성자
    public CardSearchResponse(String cardId, String imageUrl, String cardType, String company, String cardName, int annualFee) {
        this.cardId = cardId;
        this.imageUrl = imageUrl;
        this.cardType = cardType;
        this.company = company;
        this.cardName = cardName;
        this.annualFee = annualFee;
    }
    // Getter
    public String getCardId() { return cardId; }
    public String getImageUrl() { return imageUrl; }
    public String getCardType() { return cardType; }
    public String getCompany() { return company; }
    public String getCardName() { return cardName; }
    public int getAnnualFee() { return annualFee; }
}