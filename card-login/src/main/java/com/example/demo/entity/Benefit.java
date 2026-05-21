package com.example.demo.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "benefit")
public class Benefit {
    @Id
    @Column(name = "benefit_id", length = 255)
    private String benefitId;

    @Column(name = "card_id", nullable = false)
    private String cardId;

 // 다대다 매핑: benefit_category 중간 테이블을 통해 카테고리 목록을 가져옴
    @ManyToMany
    @JoinTable(
        name = "benefit_category", // 중간 테이블 이름
        joinColumns = @JoinColumn(name = "benefit_id"),
        inverseJoinColumns = @JoinColumn(name = "category_id")
    )
    private List<Category> categories = new ArrayList<>();

    @Column(name = "row_type", nullable = false, length = 20)
    private String rowType;

    @Column(name = "benefit_group", nullable = false, length = 100)
    private String benefitGroup;

    @Column(name = "benefit_type", length = 50)
    private String benefitType;
    
    @Column(name = "benefit_title")
    private String benefitTitle;

    @Column(name = "benefit_content", columnDefinition = "TEXT")
    private String benefitContent;

    @Column(name = "benefit_value")
    private BigDecimal benefitValue;

    @Column(name = "benefit_unit", length = 20)
    private String benefitUnit;
    
    @Column(name = "on_offline", length = 10)
    private String onOffline;

    @Column(name = "target_merchants", columnDefinition = "TEXT")
    private String targetMerchants;

    @Column(name = "excluded_merchants", columnDefinition = "TEXT")
    private String excludedMerchants;

    @Column(name = "performance_min")
    private Integer performanceMin;

    @Column(name = "performance_max")
    private Integer performanceMax;

    @Column(name = "min_amount")
    private Integer minAmount;

    @Column(name = "max_count")
    private Integer maxCount;

    @Column(name = "max_limit")
    private Integer maxLimit;
    
    @Column(name = "max_limit_unit", length = 20)
    private String maxLimitUnit;

    @Column(name = "group_max_limit")
    private Integer groupMaxLimit;

    @Column(name = "group_max_limit_unit", length = 20)
    private String groupMaxLimitUnit;

    // Getter
    public String getBenefitId() { return benefitId; }
    public String getCardId() { return cardId; }
    public List<Category> getCategories() { return categories; }
    public String getRowType() { return rowType; }
    public String getBenefitGroup() { return benefitGroup; }
    public String getBenefitType() { return benefitType; }
    public String getBenefitTitle() { return benefitTitle; }
    public String getBenefitContent() { return benefitContent; }
    public BigDecimal getBenefitValue() { return benefitValue; }
    public String getBenefitUnit() { return benefitUnit; }
    public String getOnOffline() { return onOffline; }
    public String getTargetMerchants() { return targetMerchants; }
    public String getExcludedMerchants() { return excludedMerchants; }
    public Integer getPerformanceMin() { return performanceMin; }
    public Integer getPerformanceMax() { return performanceMax; }
    public Integer getMinAmount() { return minAmount; }
    public Integer getMaxCount() { return maxCount; }
    public Integer getMaxLimit() { return maxLimit; }
    public String getMaxLimitUnit() { return maxLimitUnit; }
    public Integer getGroupMaxLimit() { return groupMaxLimit; }
    public String getGroupMaxLimitUnit() { return groupMaxLimitUnit; }
}