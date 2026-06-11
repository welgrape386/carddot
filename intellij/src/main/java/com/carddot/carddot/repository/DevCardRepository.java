package com.carddot.carddot.repository;

import com.carddot.carddot.entity.DevCard;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DevCardRepository extends JpaRepository<DevCard, Integer> {
    boolean existsByBenefitGroupAndBenefitTitle(String benefitGroup, String benefitTitle);
}