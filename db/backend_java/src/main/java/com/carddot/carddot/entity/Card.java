package com.carddot.carddot.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "card")
@Getter
@Setter
@NoArgsConstructor
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
    private Boolean isDomesticForeign = false;

    @Column(name = "has_transport", nullable = false)
    private Boolean hasTransport = false;

    @Column(name = "annual_fee_dom_basic", nullable = false)
    private Integer annualFeeDomBasic = 0;

    @Column(name = "annual_fee_dom_premium", nullable = false)
    private Integer annualFeeDomPremium = 0;

    @Column(name = "annual_fee_for_basic", nullable = false)
    private Integer annualFeeForBasic = 0;

    @Column(name = "annual_fee_for_premium", nullable = false)
    private Integer annualFeeForPremium = 0;

    @Column(name = "min_performance", nullable = false)
    private Integer minPerformance = 0;

    @Column(name = "annual_fee_notes", length = 255)
    private String annualFeeNotes;

    @Column(name = "summary", columnDefinition = "TEXT")
    private String summary;

    @Column(name = "has_cashback", nullable = false)
    private Boolean hasCashback = false;

    @Column(name = "image_url", length = 500)
    private String imageUrl;

    @Column(name = "link_url", length = 500)
    private String linkUrl;

    @Column(name = "view_count", nullable = false)
    private Integer viewCount = 0;

    @Column(name = "click_count", nullable = false)
    private Integer clickCount = 0;

    @Column(name = "total_max_benefit")
    private Integer totalMaxBenefit = 0;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}