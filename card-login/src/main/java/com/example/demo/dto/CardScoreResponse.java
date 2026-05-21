package com.example.demo.dto;

public class CardScoreResponse {
    private int practicality; // 페르소나
    private int annualFee;    // 연회비
    private int performance;  // 전월 실적
    private int diversity;    // 혜택 다양성
    private int limit;        // 할인 한도

    // 생성자
    public CardScoreResponse(int practicality, int annualFee, int performance, int diversity, int limit) {
        this.practicality = practicality;
        this.annualFee = annualFee;
        this.performance = performance;
        this.diversity = diversity;
        this.limit = limit;
    }

    // Getter (데이터를 JSON으로 바꿀 때 필수)
    public int getPracticality() { return practicality; }
    public int getAnnualFee() { return annualFee; }
    public int getPerformance() { return performance; }
    public int getDiversity() { return diversity; }
    public int getLimit() { return limit; }
}