package com.carddot.carddot.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.math.BigDecimal;

@Entity
@Table(name = "benefit")
@Getter
@Setter
@NoArgsConstructor
public class Benefit {

    @Id
    @Column(name = "benefit_id", length = 50)
    private String benefitId;

    @Column(name = "card_id", nullable = false, length = 50)
    private String cardId;

    @Column(name = "row_type", nullable = false)
    private String rowType;

    @Column(name = "benefit_group", nullable = false)
    private String benefitGroup;

    @Column(name = "benefit_title")
    private String benefitTitle;

    @Column(name = "on_offline")
    private String onOffline;

    @Column(name = "benefit_type")
    private String benefitType;

    @Column(name = "benefit_value")
    private BigDecimal benefitValue;

    @Column(name = "benefit_unit")
    private String benefitUnit;

    @Column(name = "target_merchants", columnDefinition = "TEXT")
    private String targetMerchants;

    @Column(name = "excluded_merchants", columnDefinition = "TEXT")
    private String excludedMerchants;

    @Column(name = "performance_min")
    private Integer performanceMin = 0;

    @Column(name = "performance_max")
    private Integer performanceMax;

    @Column(name = "min_amount")
    private Integer minAmount;

    @Column(name = "max_count")
    private Integer maxCount;

    @Column(name = "max_limit")
    private Integer maxLimit;

    @Column(name = "max_limit_unit")
    private String maxLimitUnit;

    // 그룹 통합 한도 (예: 쇼핑멤버십+OTT+이동통신 합산 월 3천원)
    // 같은 benefit_group 내 여러 혜택이 한도를 공유할 때 사용
    // max_limit은 개별 행 한도, group_max_limit은 그룹 전체 상한선
    @Column(name = "group_max_limit")
    private Integer groupMaxLimit;

    @Column(name = "group_max_limit_unit")
    private String groupMaxLimitUnit;

    @Column(name = "benefit_content", columnDefinition = "TEXT")
    private String benefitContent;

    @Column(name = "performance_level", columnDefinition = "TEXT")
    private String performanceLevel;
}