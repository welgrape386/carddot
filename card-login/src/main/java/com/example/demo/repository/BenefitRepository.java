package com.example.demo.repository;

import com.example.demo.entity.Benefit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface BenefitRepository extends JpaRepository<Benefit, Long> {
    // 특정 카드(cardId)에 해당하는 혜택(Benefit)들을 리스트로 다 찾아줘~~
    List<Benefit> findByCardId(String cardId);
}