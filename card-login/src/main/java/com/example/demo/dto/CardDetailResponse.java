package com.example.demo.dto;

import java.util.List;

public class CardDetailResponse {
    private String cardId;
    private String cardName;
    private String company;
    private String cardType;
    private String network;
    private int annualFeeDomBasic;
    private int annualFeeForBasic;
    private int minPerformance;
    
    // 혜택 상세 리스트
    private List<BenefitDetailDto> benefits;

    public CardDetailResponse(String cardId, String cardName, String company, String cardType, 
                              String network, int annualFeeDomBasic, int annualFeeForBasic, 
                              int minPerformance, List<BenefitDetailDto> benefits) {
        this.cardId = cardId;
        this.cardName = cardName;
        this.company = company;
        this.cardType = cardType;
        this.network = network;
        this.annualFeeDomBasic = annualFeeDomBasic;
        this.annualFeeForBasic = annualFeeForBasic;
        this.minPerformance = minPerformance;
        this.benefits = benefits;
    }

    // 내부 바구니 - 혜택 1개의 상세 정보
    public static class BenefitDetailDto {
        private String categoryName;
        private String benefitTitle;
        private String benefitContent;
        private String benefitValueText; // 혜택 수치랑 단위 합친 거
        private Integer maxLimit;

        public BenefitDetailDto(String categoryName, String benefitTitle, String benefitContent, 
                                String benefitValueText, Integer maxLimit) {
            this.categoryName = categoryName;
            this.benefitTitle = benefitTitle;
            this.benefitContent = benefitContent;
            this.benefitValueText = benefitValueText;
            this.maxLimit = maxLimit;
        }

        // 프론트엔드가 JSON 파싱하려면 Getter 필수
        public String getCategoryName() { return categoryName; }
        public String getBenefitTitle() { return benefitTitle; }
        public String getBenefitContent() { return benefitContent; }
        public String getBenefitValueText() { return benefitValueText; }
        public Integer getMaxLimit() { return maxLimit; }
    }

    // CardDetailResponse의 Getter
    public String getCardId() { return cardId; }
    public String getCardName() { return cardName; }
    public String getCompany() { return company; }
    public String getCardType() { return cardType; }
    public String getNetwork() { return network; }
    public int getAnnualFeeDomBasic() { return annualFeeDomBasic; }
    public int getAnnualFeeForBasic() { return annualFeeForBasic; }
    public int getMinPerformance() { return minPerformance; }
    public List<BenefitDetailDto> getBenefits() { return benefits; }
}