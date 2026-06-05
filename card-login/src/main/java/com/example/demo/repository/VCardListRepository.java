package com.example.demo.repository;

import com.example.demo.entity.VCardList;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.stereotype.Repository;

// JpaSpecificationExecutor를 상속받아야 동적 쿼리(Specification)를 실행 가능
@Repository
public interface VCardListRepository extends JpaRepository<VCardList, String>, JpaSpecificationExecutor<VCardList> {
}