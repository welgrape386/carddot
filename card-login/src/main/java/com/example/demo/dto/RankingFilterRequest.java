package com.example.demo.dto;

public class RankingFilterRequest {
    private String cardType; // "전체", "신용", "체크"
    private String company;  // "전체", "삼성", "신한", "현대", "국민" 등

    // Getters & Setters
    public String getCardType() { return cardType; }
    public void setCardType(String cardType) { this.cardType = cardType; }

    public String getCompany() { return company; }
    public void setCompany(String company) { this.company = company; }
}