package com.example.demo.repository;

import com.example.demo.entity.CardStats;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public interface CardStatsRepository extends JpaRepository<CardStats, String> {

    @Transactional
    @Modifying
    @Query("UPDATE CardStats c SET c.detailClick = c.detailClick + 1 WHERE c.cardId = :cardId")
    void incrementDetailClick(@Param("cardId") String cardId);

    @Transactional
    @Modifying
    @Query("UPDATE CardStats c SET c.urlClick = c.urlClick + 1 WHERE c.cardId = :cardId")
    void incrementUrlClick(@Param("cardId") String cardId);
}