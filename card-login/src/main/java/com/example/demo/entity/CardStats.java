package com.example.demo.entity;

import java.time.LocalDateTime;

import org.hibernate.annotations.CreationTimestamp;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "card_stats")
public class CardStats {
    @Id
    @Column(name = "card_id")
    private String cardId;

    @Column(name = "detail_click")
    private int detailClick;

    @Column(name = "url_click")
    private int urlClick;
    
    @CreationTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
    
    // Getters & Setters
    public String getCardId() { return cardId; }
    public void setCardId(String cardId) { this.cardId = cardId; }

    public int getDetailClick() { return detailClick; }
    public void setDetailClick(int detailClick) { this.detailClick = detailClick; }

    public int getUrlClick() { return urlClick; }
    public void setUrlClick(int urlClick) { this.urlClick = urlClick; }
}