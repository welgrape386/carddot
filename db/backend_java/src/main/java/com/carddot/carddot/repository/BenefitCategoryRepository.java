package com.carddot.carddot.repository;

import com.carddot.carddot.entity.BenefitCategory;
import com.carddot.carddot.entity.BenefitCategoryId;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BenefitCategoryRepository extends JpaRepository<BenefitCategory, BenefitCategoryId> {
}