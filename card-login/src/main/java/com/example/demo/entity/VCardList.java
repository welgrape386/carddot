package com.example.demo.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

@Entity
@Table(name = "v_card_list")
@Immutable // 뷰니까 읽기 전용으로 설정ㅇ해서 성능 최적화
public class VCardList {

    @Id
    @Column(name = "card_id")
    private String cardId;

    @Column(name = "card_name")
    private String cardName;

    private String company;
    
    @Column(name = "card_type")
    private String cardType;

    @Column(name = "has_transport")
    private boolean hasTransport;

    @Column(name = "annual_fee_dom_basic")
    private int annualFeeDomBasic;
    
    @Column(name = "annual_fee_dom_premium")
    private int annualFeeDomPremium;
    
    @Column(name = "annual_fee_for_basic")
    private int annualFeeForBasic;
    
    @Column(name = "annual_fee_for_premium")
    private int annualFeeForPremium;

    @Column(name = "min_performance")
    private int minPerformance;

    @Column(name = "has_cashback")
    private boolean hasCashback;

    @Column(name = "image_url")
    private String imageUrl;

    @Column(name = "total_score")
    private int totalScore; // detail_click + url_click

    @Column(name = "benefit_count") 
    private Integer benefitCount; // 혜택 개수
    
    @Column(name = "summary")
    private String summary;

    @Column(name = "detail_click")
    private int detailClick;

    @Column(name = "url_click")
    private int urlClick;
    
    @Column(name = "category_names")
    private String categoryNames;

    // Getters
    public String getCardId() { return cardId; }
    public String getCardName() { return cardName; }
    public String getCompany() { return company; }
    public String getCardType() { return cardType; }
    public boolean isHasTransport() { return hasTransport; }
    public int getAnnualFeeDomBasic() { return annualFeeDomBasic; }
    public int getAnnualFeeDomPremium() { return annualFeeDomPremium; }
    public int getAnnualFeeForBasic() { return annualFeeForBasic; }
    public int getAnnualFeeForPremium() { return annualFeeForPremium; }
    public int getMinPerformance() { return minPerformance; }
    public boolean isHasCashback() { return hasCashback; }
    public String getImageUrl() { return imageUrl; }
    public int getTotalScore() { return totalScore; }
    public Integer getBenefitCount() { return benefitCount; }
    public String getSummary() { return summary; }
    public int getDetailClick() { return detailClick; }
    public int getUrlClick() { return urlClick; }
    public String getCategoryNames() { return categoryNames; }
}