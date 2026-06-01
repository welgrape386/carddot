package com.example.demo.dto;

import java.time.LocalDateTime;
import java.util.List;

public class RecentCompareResponse {
    private Integer compareId;
    private LocalDateTime comparedAt;
    private List<CardSimpleDto> cards; // 2~3개의 카드 정보가 배열로 들어감

    public RecentCompareResponse(Integer compareId, LocalDateTime comparedAt, List<CardSimpleDto> cards) {
        this.compareId = compareId;
        this.comparedAt = comparedAt;
        this.cards = cards;
    }

    public Integer getCompareId() { return compareId; }
    public LocalDateTime getComparedAt() { return comparedAt; }
    public List<CardSimpleDto> getCards() { return cards; }

    // 내부 DTO: 비교 내역 리스트에 보여줄 간략한 카드 정보
    public static class CardSimpleDto {
        private String cardId;
        private String company;
        private String cardName;
        private String imageUrl;

        public CardSimpleDto(String cardId, String company, String cardName, String imageUrl) {
            this.cardId = cardId;
            this.company = company;
            this.cardName = cardName;
            this.imageUrl = imageUrl;
        }

        public String getCardId() { return cardId; }
        public String getCompany() { return company; }
        public String getCardName() { return cardName; }
        public String getImageUrl() { return imageUrl; }
    }
}