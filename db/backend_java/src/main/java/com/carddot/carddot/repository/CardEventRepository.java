package com.carddot.carddot.repository;

import com.carddot.carddot.entity.CardEvent;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CardEventRepository extends JpaRepository<CardEvent, Integer> {
    boolean existsByCardIdAndEventTitleAndEventContent(String cardId, String eventTitle, String eventContent);
}