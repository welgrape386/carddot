package com.example.demo.repository;

import com.example.demo.entity.CardEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface CardEventRepository extends JpaRepository<CardEvent, Integer> {
    // 특정 카드의 이벤트 목록을 가져옵니다.
    List<CardEvent> findByCardId(String cardId);
}