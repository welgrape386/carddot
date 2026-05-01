package com.example.demo.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
@Table(name = "benefit")
public class Benefit {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "benefit_id")
    private Long benefitId;

    @Column(name = "card_id", nullable = false)
    private String cardId;

    // 카테고리 테이블을 객체로 참조 (DB의 JOIN 역할)
    @ManyToOne
    @JoinColumn(name = "category_id")
    private Category category;

    @Column(name = "benefit_title")
    private String benefitTitle;

    @Column(name = "benefit_content", columnDefinition = "TEXT")
    private String benefitContent;

    @Column(name = "benefit_value")
    private BigDecimal benefitValue;

    @Column(name = "benefit_unit", length = 20)
    private String benefitUnit;

    @Column(name = "max_limit")
    private Integer maxLimit;

    // Getter
    public Long getBenefitId() { return benefitId; }
    public String getCardId() { return cardId; }
    public Category getCategory() { return category; }
    public String getBenefitTitle() { return benefitTitle; }
    public String getBenefitContent() { return benefitContent; }
    public BigDecimal getBenefitValue() { return benefitValue; }
    public String getBenefitUnit() { return benefitUnit; }
    public Integer getMaxLimit() { return maxLimit; }
}