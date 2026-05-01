package com.example.demo.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "card")
public class Card {

    @Id
    @Column(name = "card_id", length = 50)
    private String cardId;

    @Column(name = "card_name", nullable = false, length = 100)
    private String cardName;

    @Column(name = "company", nullable = false, length = 50)
    private String company;

    @Column(name = "card_type", nullable = false, length = 10)
    private String cardType;

    @Column(name = "network", length = 50)
    private String network;

    @Column(name = "is_domestic_foreign", nullable = false)
    private boolean isDomesticForeign = false;

    @Column(name = "has_transport", nullable = false)
    private boolean hasTransport = false;

    @Column(name = "annual_fee_dom_basic", nullable = false)
    private int annualFeeDomBasic = 0;

    @Column(name = "annual_fee_dom_premium", nullable = false)
    private int annualFeeDomPremium = 0;

    @Column(name = "annual_fee_for_basic", nullable = false)
    private int annualFeeForBasic = 0;

    @Column(name = "annual_fee_for_premium", nullable = false)
    private int annualFeeForPremium = 0;

    @Column(name = "annual_fee_notes", length = 255)
    private String annualFeeNotes;

    @Column(name = "min_performance", nullable = false)
    private int minPerformance = 0;

    @Column(name = "summary", columnDefinition = "TEXT")
    private String summary;

    @Column(name = "has_cashback", nullable = false)
    private boolean hasCashback = false;

    @Column(name = "image_url", length = 500)
    private String imageUrl;

    @Column(name = "link_url", length = 500)
    private String linkUrl;

    @Column(name = "view_count", nullable = false)
    private int viewCount = 0;

    @Column(name = "click_count", nullable = false)
    private int clickCount = 0;

    @Column(name = "total_max_benefit")
    private Integer totalMaxBenefit = 0;

    @CreationTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;


    // --- Getter --- (세팅은 관리자만 하므로 우선 Getter만 열어둠~~)
    public String getCardId() { return cardId; }
    public String getCardName() { return cardName; }
    public String getCompany() { return company; }
    public String getCardType() { return cardType; }
    public String getNetwork() { return network; }
    public boolean isDomesticForeign() { return isDomesticForeign; }
    public boolean isHasTransport() { return hasTransport; }
    public int getAnnualFeeDomBasic() { return annualFeeDomBasic; }
    public int getAnnualFeeDomPremium() { return annualFeeDomPremium; }
    public int getAnnualFeeForBasic() { return annualFeeForBasic; }
    public int getAnnualFeeForPremium() { return annualFeeForPremium; }
    public String getAnnualFeeNotes() { return annualFeeNotes; }
    public int getMinPerformance() { return minPerformance; }
    public String getSummary() { return summary; }
    public boolean isHasCashback() { return hasCashback; }
    public String getImageUrl() { return imageUrl; }
    public String getLinkUrl() { return linkUrl; }
    public int getViewCount() { return viewCount; }
    public int getClickCount() { return clickCount; }
    public Integer getTotalMaxBenefit() { return totalMaxBenefit; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
}