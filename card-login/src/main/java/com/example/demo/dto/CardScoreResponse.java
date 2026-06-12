package com.example.demo.dto;

public class CardScoreResponse {
	private int totalScore; // 종합 점수
    private int personaScore; // 페르소나
    private int annualFeeScore; // 연회비
    private int performanceScore; // 전월 실적
    private int diversityScore; // 혜택 다양성
    private int limitScore; // 할인 한도

    // 생성자
    public CardScoreResponse(int totalScore, int personaScore, int annualFeeScore, 
            int performanceScore, int diversityScore, int limitScore) {
        this.totalScore = totalScore;
        this.personaScore = personaScore;
        this.annualFeeScore = annualFeeScore;
        this.performanceScore = performanceScore;
        this.diversityScore = diversityScore;
        this.limitScore = limitScore;
    }

    // Getter (데이터를 JSON으로 바꿀 때 필수)
    public int getTotalScore() { return totalScore; }
    public int getPersonaScore() { return personaScore; }
    public int getAnnualFeeScore() { return annualFeeScore; }
    public int getPerformanceScore() { return performanceScore; }
    public int getDiversityScore() { return diversityScore; }
    public int getLimitScore() { return limitScore; }
}