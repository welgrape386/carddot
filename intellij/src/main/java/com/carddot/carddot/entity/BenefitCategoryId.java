package com.carddot.carddot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;

@Embeddable
@Getter
@Setter
@NoArgsConstructor
public class BenefitCategoryId implements Serializable {

    @Column(name = "benefit_id")
    private String benefitId;

    @Column(name = "category_id")
    private Integer categoryId;
}