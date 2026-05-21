package com.example.demo.common;

import java.util.HashMap;
import java.util.Map;

public class PersonaWeight {

    public static Map<Long, Double> getWeightsByPersona(String personaType) {
        Map<Long, Double> weights = new HashMap<>();
        
        switch (personaType.toUpperCase()) {
            case "STUDENT": // 1. 대학생
                weights.put(20L, 0.25); // 교육/육아
                weights.put(5L, 0.25);  // 대중교통/택시
                weights.put(13L, 0.10); // 편의점
                weights.put(14L, 0.10); // 카페/베이커리
                weights.put(15L, 0.10); // 배달
                break;
            case "SINGLE": // 2. 1인 가구 자취족
                weights.put(15L, 0.25); // 배달
                weights.put(13L, 0.25); // 편의점
                weights.put(1L, 0.10);  // 온라인쇼핑
                weights.put(10L, 0.10); // 페이/간편결제
                weights.put(8L, 0.10);  // 구독/스트리밍
                break;
            case "WORKER": // 3. 직장인
                weights.put(6L, 0.25);  // 자동차/주유
                weights.put(16L, 0.25); // 외식
                weights.put(1L, 0.10);  // 온라인쇼핑
                weights.put(19L, 0.10); // 해외
                weights.put(12L, 0.10); // 생활비
                break;
            case "FAMILY": // 4. 아이 있는 가족
                weights.put(20L, 0.25); // 교육/육아
                weights.put(3L, 0.25);  // 슈퍼마켓/생활잡화
                weights.put(21L, 0.10); // 의료
                weights.put(12L, 0.10); // 생활비
                weights.put(6L, 0.10);  // 자동차/주유
                break;
            case "SENIOR": // 5. 액티브 시니어
                weights.put(21L, 0.25); // 의료
                weights.put(3L, 0.25);  // 슈퍼마켓/생활잡화
                weights.put(12L, 0.10); // 생활비
                weights.put(16L, 0.10); // 외식
                weights.put(5L, 0.10);  // 대중교통/택시
                break;
            default: // 기본값 (에러 방지용)
                weights.put(15L, 0.25); 
                weights.put(13L, 0.25); 
                weights.put(1L, 0.10);  
                weights.put(10L, 0.10); 
                weights.put(8L, 0.10);  
                break;
        }
        return weights;
    }
}