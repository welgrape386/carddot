package com.example.demo.dto;

import java.util.List;

public class CardFilterRequest {
    private String cardType;       // 전체, 신용카드, 체크카드
    private List<String> company;  // 전체, 신한, 삼성 ...
    private String annualFee;      // 전체, ~1만원, ~3만원, ~10만원, 10만원~
    private String minPerformance; // 전체, ~30만원, ~50만원, 50만원~
    private boolean hasEvent;      // true/false
    private boolean hasTransport;  // true/false
    private String sort;           // 인기순, 혜택많은순, 혜택적은순

    public String getCardType() { return cardType; }
    public void setCardType(String cardType) { this.cardType = cardType; }

    public List<String> getCompany() { return company; }
    public void setCompany(List<String> company) { this.company = company; }

    public String getAnnualFee() { return annualFee; }
    public void setAnnualFee(String annualFee) { this.annualFee = annualFee; }

    public String getMinPerformance() { return minPerformance; }
    public void setMinPerformance(String minPerformance) { this.minPerformance = minPerformance; }

    public boolean isHasEvent() { return hasEvent; }
    public void setHasEvent(boolean hasEvent) { this.hasEvent = hasEvent; }

    public boolean isHasTransport() { return hasTransport; }
    public void setHasTransport(boolean hasTransport) { this.hasTransport = hasTransport; }

    public String getSort() { return sort; }
    public void setSort(String sort) { this.sort = sort; }
}