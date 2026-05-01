package com.example.demo.controller;

import com.example.demo.dto.CardDetailResponse;
import com.example.demo.dto.CardListResponse;
import com.example.demo.service.CardService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/cards")
@CrossOrigin(origins = "http://localhost:3000")
public class CardController {

    private final CardService cardService;

    public CardController(CardService cardService) {
        this.cardService = cardService;
    }

    // [기존 주소] 메인 화면 리스트 조회: GET /api/cards
    @GetMapping
    public ResponseEntity<List<CardListResponse>> getAllCards() {
        List<CardListResponse> cards = cardService.getAllCards();
        return ResponseEntity.ok(cards);
    }

    // [새로운 주소] 카드 상세보기: GET /api/cards/{cardId}
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
}