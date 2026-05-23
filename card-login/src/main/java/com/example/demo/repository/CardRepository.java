package com.example.demo.repository;

import com.example.demo.entity.Card;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface CardRepository extends JpaRepository<Card, String> {
    // 일단은 JpaRepository의 기본 findAll() 메서드 활용
	// 카드 비교 - 검색 팝업용: 카드명, 카드사에 키워드 포함된 카드 찾기
	List<Card> findByCardNameContainingOrCompanyContaining(String cardName, String company);
}