package com.example.demo.dto;

public class RecentCardResponse {
    private String cardId;
    private String company;
    private String cardName;
    private int annualFee;
    private String imageUrl;

    public RecentCardResponse(String cardId, String company, String cardName, int annualFee, String imageUrl) {
        this.cardId = cardId;
        this.company = company;
        this.cardName = cardName;
        this.annualFee = annualFee;
        this.imageUrl = imageUrl;
    }

    public String getCardId() { return cardId; }
    public String getCompany() { return company; }
    public String getCardName() { return cardName; }
    public int getAnnualFee() { return annualFee; }
    public String getImageUrl() { return imageUrl; }
}