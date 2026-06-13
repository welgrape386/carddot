package com.example.demo.repository;

import com.example.demo.entity.Benefit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface BenefitRepository extends JpaRepository<Benefit, String> {
    // 특정 카드(cardId)에 해당하는 혜택(Benefit)들을 리스트로 다 찾아줘~~
    List<Benefit> findByCardId(String cardId);
    
    // cardId 목록 받고 연관된 카테고리까지 한 번에 가져옴
    @Query("SELECT DISTINCT b FROM Benefit b LEFT JOIN FETCH b.categories WHERE b.cardId IN :cardIds")
    List<Benefit> findByCardIdInWithCategories(@Param("cardIds") List<String> cardIds);
}