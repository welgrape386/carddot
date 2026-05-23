package com.example.demo.dto;

public class BenefitCompareDto {
    private String categoryName;
    private String benefitType;     // 할인, 적립 등
    private String benefitValueText; // "10%" 혜택률 요약
    private String benefitTitle;     // 상세 비교표
    private String benefitContent;   // 상세 비교표 텍스트

    public BenefitCompareDto(String categoryName, String benefitType, String benefitValueText, String benefitTitle, String benefitContent) {
        this.categoryName = categoryName;
        this.benefitType = benefitType;
        this.benefitValueText = benefitValueText;
        this.benefitTitle = benefitTitle;
        this.benefitContent = benefitContent;
    }

    public String getCategoryName() { return categoryName; }
    public String getBenefitType() { return benefitType; }
    public String getBenefitValueText() { return benefitValueText; }
    public String getBenefitTitle() { return benefitTitle; }
    public String getBenefitContent() { return benefitContent; }
}