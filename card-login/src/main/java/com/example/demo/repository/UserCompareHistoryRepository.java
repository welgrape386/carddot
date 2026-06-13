package com.example.demo.repository;

import com.example.demo.entity.UserCompareHistory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface UserCompareHistoryRepository extends JpaRepository<UserCompareHistory, Integer> {
    // 특정 유저의 최근 비교 기록 10개를 최신순으로 가져옴
    List<UserCompareHistory> findTop10ByUser_IdOrderByCreatedAtDesc(Long userId);
    List<UserCompareHistory> findByUser_Id(Long userId);
}