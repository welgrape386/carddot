package com.example.demo.service;

import com.example.demo.dto.CardFilterRequest;
import com.example.demo.entity.VCardList;
import com.example.demo.repository.VCardListRepository;
import com.example.demo.repository.CardSpecification;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class CardFilterService {

    private final VCardListRepository vCardListRepository;

    public CardFilterService(VCardListRepository vCardListRepository) {
        this.vCardListRepository = vCardListRepository;
    }

    public List<VCardList> searchCards(CardFilterRequest req) {
        // 1. 정렬 기준 세팅
        Sort sort = Sort.unsorted();
        if (req.getSort() != null) {
            switch (req.getSort()) {
                case "인기순": 
                    // 뷰에 있는 total_score(조회수+클릭수) 기준으로 내림차순
                    sort = Sort.by(Sort.Direction.DESC, "totalScore"); 
                    break;
                case "혜택많은순": 
                    sort = Sort.by(Sort.Direction.DESC, "benefitCount"); 
                    break;
                case "혜택적은순": 
                    sort = Sort.by(Sort.Direction.ASC, "benefitCount"); 
                    break;
            }
        }

        // 2. 조건(Specification)과 정렬(Sort)을 합쳐서 쿼리 실행
        return vCardListRepository.findAll(CardSpecification.filterCards(req), sort);
    }
}