package com.example.demo.dto;

public class BenefitCompareDto {
    private String categoryName;
    private String benefitType;     // 할인, 적립 등
    private String benefitValueText; // "10%" 혜택률 요약
    private String benefitTitle;     // 상세 비교표
    private String benefitContent;   // 상세 비교표 텍스트
    
    // 실질 할인율, 환산 근거 추가
    private String effectiveRateText;
    private String effectiveBasis;

    public BenefitCompareDto(String categoryName, String benefitType, String benefitValueText, String benefitTitle, String benefitContent, String effectiveRateText, String effectiveBasis) {
        this.categoryName = categoryName;
        this.benefitType = benefitType;
        this.benefitValueText = benefitValueText;
        this.benefitTitle = benefitTitle;
        this.benefitContent = benefitContent;
        this.effectiveRateText = effectiveRateText;
        this.effectiveBasis = effectiveBasis;
    }

    public String getCategoryName() { return categoryName; }
    public String getBenefitType() { return benefitType; }
    public String getBenefitValueText() { return benefitValueText; }
    public String getBenefitTitle() { return benefitTitle; }
    public String getBenefitContent() { return benefitContent; }
    public String getEffectiveRateText() { return effectiveRateText; }
    public String getEffectiveBasis() { return effectiveBasis; }
}