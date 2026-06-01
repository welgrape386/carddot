package com.example.demo.controller;

import com.example.demo.dto.CardCompareResponse;
import com.example.demo.dto.CardDetailResponse;
import com.example.demo.dto.CardListResponse;
import com.example.demo.service.CardService;
import com.example.demo.dto.CardScoreResponse;
import com.example.demo.dto.CardSearchResponse;
import com.example.demo.security.JwtTokenProvider;
import com.example.demo.service.CardScoreService;
import com.example.demo.service.UserService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import jakarta.servlet.http.HttpServletRequest;

import java.util.List;

@RestController
@RequestMapping("/api/cards")
@CrossOrigin(origins = {"http://localhost:3000", "https://carddot.vercel.app"})
public class CardController {

    private final CardService cardService;
    private final CardScoreService cardScoreService;
    private final UserService userService;
    private final JwtTokenProvider jwtTokenProvider;

 // 생성자
    public CardController(CardService cardService, CardScoreService cardScoreService,
    		UserService userService, JwtTokenProvider jwtTokenProvider) {
        this.cardService = cardService;
        this.cardScoreService = cardScoreService;
        this.userService = userService;
        this.jwtTokenProvider = jwtTokenProvider;
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
    
    // 비교: GET /api/cards/compare?ids=card1,card2,card3&personaType=STUDENT)
    @GetMapping("/compare")
    public ResponseEntity<?> compareCards(
    		HttpServletRequest request,
            @RequestParam List<String> ids,
            @RequestParam(defaultValue = "STUDENT") String personaType) {
        try {
        	// 토큰 있다면 '최근 비교한 카드'에 기록
        	String bearerToken = request.getHeader("Authorization");
            if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
                String token = bearerToken.substring(7);
                if (jwtTokenProvider.validateToken(token)) {
                    String email = jwtTokenProvider.getLoginId(token);
                    userService.recordCardCompare(email, ids); // 기록 저장
                }
            }
        	
            // 기존 비교 응답 로직
            List<CardCompareResponse> result = cardService.compareCards(ids, personaType);
            return ResponseEntity.ok(result);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(e.getMessage());
        }
    }
    
    // 비교 - 카드 검색 팝업: GET /api/cards/search?keyword=신한
    @GetMapping("/search")
    public ResponseEntity<List<CardSearchResponse>> searchCards(
            @RequestParam(required = false) String keyword) {
        List<CardSearchResponse> result = cardService.searchCards(keyword);
        return ResponseEntity.ok(result);
    }
}