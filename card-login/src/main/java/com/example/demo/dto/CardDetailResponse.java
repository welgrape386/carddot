package com.example.demo.dto;

import java.util.List;
import java.math.BigDecimal;

public class CardDetailResponse {
	// 상단 고정 공통 내용
	private String cardId;
    private String company;
    private String cardType;
    private String network;
    private String cardName;
    private boolean hasTransport;
    private int annualFeeDomBasic;
    private int annualFeeDomPremium;
    private int annualFeeForBasic;
    private int annualFeeForPremium;
    private int minPerformance;
    private String linkUrl;
    private String imageUrl;
    
    // 하단 탭 3개
    private List<BenefitDto> benefits;
    private List<NoticeDto> notices;
    private List<EventDto> events;

    public CardDetailResponse(String cardId, String company, String cardType, String network, 
            String cardName, boolean hasTransport, int annualFeeDomBasic, 
            int annualFeeDomPremium, int annualFeeForBasic, int annualFeeForPremium, 
            int minPerformance, String linkUrl, String imageUrl,
            List<BenefitDto> benefits, List<NoticeDto> notices, List<EventDto> events) {
    	this.cardId = cardId;
    	this.company = company;
    	this.cardType = cardType;
    	this.network = network;
    	this.cardName = cardName;
    	this.hasTransport = hasTransport;
    	this.annualFeeDomBasic = annualFeeDomBasic;
    	this.annualFeeDomPremium = annualFeeDomPremium;
    	this.annualFeeForBasic = annualFeeForBasic;
    	this.annualFeeForPremium = annualFeeForPremium;
    	this.minPerformance = minPerformance;
    	this.linkUrl = linkUrl;
    	this.imageUrl = imageUrl;
    	this.benefits = benefits;
    	this.notices = notices;
    	this.events = events;
    }

    // 탭1: 주요 혜택
    public static class BenefitDto {
        private String categoryName;
        private String targetMerchants;
        private String uiTitle;
        private String uiContent;
        private String effectiveRateText;
        private BigDecimal benefitValue;
        private String benefitUnit;
        private Integer maxLimit;
        private String maxLimitUnit;
        private Integer groupMaxLimit;
        private String groupMaxLimitUnit;

        public BenefitDto(String categoryName, String targetMerchants, String uiTitle, 
                          String uiContent, String effectiveRateText,
                          BigDecimal benefitValue, String benefitUnit,
                          Integer maxLimit, String maxLimitUnit,
                          Integer groupMaxLimit, String groupMaxLimitUnit) {
            this.categoryName = categoryName;
            this.targetMerchants = targetMerchants;
            this.uiTitle = uiTitle;
            this.uiContent = uiContent;
            this.effectiveRateText = effectiveRateText;
            this.benefitValue = benefitValue;
            this.benefitUnit = benefitUnit;
            this.maxLimit = maxLimit;
            this.maxLimitUnit = maxLimitUnit;
            this.groupMaxLimit = groupMaxLimit;
            this.groupMaxLimitUnit = groupMaxLimitUnit;
        }
        // Getter
        public String getCategoryName() { return categoryName; }
        public String getTargetMerchants() { return targetMerchants; }
        public String getUiTitle() { return uiTitle; }
        public String getUiContent() { return uiContent; }
        public String getEffectiveRateText() { return effectiveRateText; }
        public BigDecimal getBenefitValue() { return benefitValue; }
        public String getBenefitUnit() { return benefitUnit; }
        public Integer getMaxLimit() { return maxLimit; }
        public String getMaxLimitUnit() { return maxLimitUnit; }
        public Integer getGroupMaxLimit() { return groupMaxLimit; }
        public String getGroupMaxLimitUnit() { return groupMaxLimitUnit; }
    }
    
    // 탭2: 유의사항
    public static class NoticeDto {
        private String cardId;
        private String noticeContent;

        public NoticeDto(String cardId, String noticeContent) {
            this.cardId = cardId;
            this.noticeContent = noticeContent;
        }
        public String getCardId() { return cardId; }
        public String getNoticeContent() { return noticeContent; }
    }
    
    // 탭3: 이벤트
    public static class EventDto {
        private String eventTitle;
        private String section;
        private String eventContent;
        private String eventLink;
        private String startDate;
        private String endDate;

        public EventDto(String eventTitle, String section, String eventContent, String eventLink, 
                        String startDate, String endDate) {
            this.eventTitle = eventTitle;
            this.section = section;
            this.eventContent = eventContent;
            this.eventLink = eventLink;
            this.startDate = startDate;
            this.endDate = endDate;
        }
        // Getters
        public String getEventTitle() { return eventTitle; }
        public String getSection() { return section; }
        public String getEventContent() { return eventContent; }
        public String getEventLink() { return eventLink; }
        public String getStartDate() { return startDate; }
        public String getEndDate() { return endDate; }
    }

    // 최상위 Getters
    public String getCardId() { return cardId; }
    public String getCompany() { return company; }
    public String getCardType() { return cardType; }
    public String getNetwork() { return network; }
    public String getCardName() { return cardName; }
    public boolean isHasTransport() { return hasTransport; }
    public int getAnnualFeeDomBasic() { return annualFeeDomBasic; }
    public int getAnnualFeeDomPremium() { return annualFeeDomPremium; }
    public int getAnnualFeeForBasic() { return annualFeeForBasic; }
    public int getAnnualFeeForPremium() { return annualFeeForPremium; }
    public int getMinPerformance() { return minPerformance; }
    public String getLinkUrl() { return linkUrl; }
    public String getImageUrl() { return imageUrl; }
    public List<BenefitDto> getBenefits() { return benefits; }
    public List<NoticeDto> getNotices() { return notices; }
    public List<EventDto> getEvents() { return events; }
}