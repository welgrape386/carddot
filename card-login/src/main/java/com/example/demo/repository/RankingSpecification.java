package com.example.demo.repository;

import com.example.demo.entity.VCardList;
import com.example.demo.dto.RankingFilterRequest;
import org.springframework.data.jpa.domain.Specification;
import jakarta.persistence.criteria.Predicate;
import java.util.ArrayList;
import java.util.List;

public class RankingSpecification {

    public static Specification<VCardList> filterRanking(RankingFilterRequest req) {
        return (root, query, cb) -> {
            List<Predicate> predicates = new ArrayList<>();

            // 카드 종류 필터
            if (req.getCardType() != null && !req.getCardType().equals("전체")) {
                predicates.add(cb.equal(root.get("cardType"), req.getCardType()));
            }

            // 카드사 필터
            if (req.getCompany() != null && !req.getCompany().equals("전체")) {
                predicates.add(cb.equal(root.get("company"), req.getCompany()));
            }

            return cb.and(predicates.toArray(new Predicate[0]));
        };
    }
}