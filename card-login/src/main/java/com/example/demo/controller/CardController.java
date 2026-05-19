package com.example.demo.controller;

import com.example.demo.dto.CardDetailResponse;
import com.example.demo.dto.CardListResponse;
import com.example.demo.service.CardService;
import com.example.demo.dto.CardScoreResponse;
import com.example.demo.service.CardScoreService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/cards")
@CrossOrigin(origins = "http://localhost:3000")
public class CardController {

    private final CardService cardService;
    private final CardScoreService cardScoreService;

 // 생성자
    public CardController(CardService cardService, CardScoreService cardScoreService) {
        this.cardService = cardService;
        this.cardScoreService = cardScoreService;
    }

    // 메인 화면 리스트 조회: GET /api/cards
    @GetMapping
    public ResponseEntity<List<CardListResponse>> getAllCards() {
        List<CardListResponse> cards = cardService.getAllCards();
        return ResponseEntity.ok(cards);
    }

    // 카드 상세보기: GET /api/cards/{cardId}
    @GetMapping("/{cardId}")
    public ResponseEntity<CardDetailResponse> getCardDetail(@PathVariable String cardId) {
        try {
            CardDetailResponse response = cardService.getCardDetail(cardId);
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            // 카드를 찾을 수 없을 때 404가 아닌 깔끔한 400 Bad Request와 메시지 보냄
            return ResponseEntity.badRequest().build(); 
        }
    }
    
    /**
     * 특정 카드의 종합 점수를 반환 (5항목)
     * @param id 카드 고유 ID
     * @param personaType 페르소나 타입 (STUDENT, SINGLE, WORKER, FAMILY, SENIOR)
     * @return 0~100점으로 환산된 5가지 스탯 데이터 (CardScoreResponse)
     */
    @GetMapping("/{id}/scores")
    public ResponseEntity<?> getCardScores( // <?> 로 변경하여 에러 메시지(String)도 반환 가능하게 수정
            @PathVariable("id") String id, 
            @RequestParam(name = "personaType", defaultValue = "STUDENT") String personaType) {
        
        try {
            CardScoreResponse response = cardScoreService.getCardScores(id, personaType);
            return ResponseEntity.ok(response);
            
        } catch (IllegalArgumentException e) {
            // DB에 해당 카드 ID가 없을 경우 화면에 메시지 출력 (400)
            return ResponseEntity.badRequest().body("요청 오류: " + e.getMessage());
            
        } catch (Exception e) {
            // 500 에러가 났을 때, 진짜 원인을 Talend 화면에 그대로 출력
            e.printStackTrace();
            return ResponseEntity.internalServerError().body("서버 500 에러 발생 원인: " + e.getMessage());
        }
    }
}