package com.example.demo.repository;

import com.example.demo.entity.UserActivity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface UserActivityRepository extends JpaRepository<UserActivity, Integer> {
    // 특정 유저의 특정 타입("VIEW") 활동을 최신순으로 10개만 가져옴
    List<UserActivity> findTop10ByUser_IdAndTypeOrderByCreatedAtDesc(Long userId, String type);
}