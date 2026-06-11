package com.carddot.carddot.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "benefit_category")
@Getter
@Setter
@NoArgsConstructor
public class BenefitCategory {

    @EmbeddedId
    private BenefitCategoryId id;

    public void setBenefitId(String benefitId) {
        if (this.id == null) this.id = new BenefitCategoryId();
        this.id.setBenefitId(benefitId);
    }

    public void setCategoryId(Integer categoryId) {
        if (this.id == null) this.id = new BenefitCategoryId();
        this.id.setCategoryId(categoryId);
    }
}