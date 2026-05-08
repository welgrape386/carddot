package com.carddot.carddot.repository;

import com.carddot.carddot.entity.Benefit;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BenefitRepository extends JpaRepository<Benefit, String> {
}