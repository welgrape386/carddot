package com.example.demo.repository;

import com.example.demo.entity.Notice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface NoticeRepository extends JpaRepository<Notice, Integer> {
    // 특정 카드의 유의사항 목록을 가져옵니다.
    List<Notice> findByCardId(String cardId);
}