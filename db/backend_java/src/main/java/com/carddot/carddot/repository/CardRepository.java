package com.carddot.carddot.repository;

import com.carddot.carddot.entity.Card;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CardRepository extends JpaRepository<Card, String> {
    boolean existsByCardId(String cardId);
}