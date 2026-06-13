package com.example.demo.repository;

import com.example.demo.entity.VCardList;
import com.example.demo.dto.CardFilterRequest;
import org.springframework.data.jpa.domain.Specification;
import jakarta.persistence.criteria.Predicate;
import java.util.ArrayList;
import java.util.List;

// 조건 -> SQL 번역
public class CardSpecification {

    public static Specification<VCardList> filterCards(CardFilterRequest req) {
        return (root, query, cb) -> {
            List<Predicate> predicates = new ArrayList<>();

            // 1. 카드 종류
            if (req.getCardType() != null && !req.getCardType().equals("전체")) {
                String type = req.getCardType().contains("신용") ? "신용" : "체크";
                predicates.add(cb.equal(root.get("cardType"), type));
            }

            // 2. 카드사
            if (req.getCompanies() != null && !req.getCompanies().isEmpty()) {
            	if (!req.getCompanies().contains("전체")) {
                    // JPA IN 쿼리
                    predicates.add(root.get("company").in(req.getCompanies()));
                }
            }

            // 3. 연회비
            if (req.getAnnualFee() != null && !req.getAnnualFee().equals("전체")) {
                switch (req.getAnnualFee()) {
                    case "~1만원": predicates.add(cb.lessThanOrEqualTo(root.get("annualFeeDomBasic"), 10000)); break;
                    case "~3만원": predicates.add(cb.lessThanOrEqualTo(root.get("annualFeeDomBasic"), 30000)); break;
                    case "~10만원": predicates.add(cb.lessThanOrEqualTo(root.get("annualFeeDomBasic"), 100000)); break;
                    case "10만원~": predicates.add(cb.greaterThan(root.get("annualFeeDomBasic"), 100000)); break;
                }
            }

            // 4. 전월실적
            if (req.getMinPerformance() != null && !req.getMinPerformance().equals("전체")) {
                switch (req.getMinPerformance()) {
                    case "~30만원": predicates.add(cb.lessThanOrEqualTo(root.get("minPerformance"), 300000)); break;
                    case "~50만원": predicates.add(cb.lessThanOrEqualTo(root.get("minPerformance"), 500000)); break;
                    case "50만원~": predicates.add(cb.greaterThan(root.get("minPerformance"), 500000)); break;
                }
            }

            // 5. 추가 조건
            if (req.isHasEvent()) {
                predicates.add(cb.isTrue(root.get("hasCashback"))); // 이벤트 여부를 이 칼럼으로 판단
            }
            if (req.isHasTransport()) {
                predicates.add(cb.isTrue(root.get("hasTransport")));
            }
            
            // 6. 카테고리 필터링
            if (req.getCategoryNames() != null && !req.getCategoryNames().isEmpty()) {
                List<Predicate> categoryPredicates = new ArrayList<>();
                
                for (String category : req.getCategoryNames()) {
                    categoryPredicates.add(cb.like(root.get("categoryNames"), "%" + category + "%"));
                }
                
                // 배열 안의 카테고리 중 하나라도 포함되면 조회
                predicates.add(cb.or(categoryPredicates.toArray(new Predicate[0])));
            }

            return cb.and(predicates.toArray(new Predicate[0]));
        };
    }
}