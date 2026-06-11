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

    @Column(name = "group_max_limit")
    private Integer groupMaxLimit;

    @Column(name = "group_max_limit_unit")
    private String groupMaxLimitUnit;

    @Column(name = "performance_level", columnDefinition = "TEXT")
    private String performanceLevel;

    @Column(name = "unit_amount")
    private Integer unitAmount;

    @Column(name = "ui_title", columnDefinition = "TEXT")
    private String uiTitle;

    @Column(name = "ui_content", columnDefinition = "TEXT")
    private String uiContent;

    @Column(name = "benefit_group")
    private String benefitGroup;

}