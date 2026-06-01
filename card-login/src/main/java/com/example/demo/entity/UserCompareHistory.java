package com.example.demo.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "user_compare_history")
public class UserCompareHistory {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "compare_id")
    private Integer compareId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "card_id_1", nullable = false)
    private Card card1;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "card_id_2", nullable = false)
    private Card card2;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "card_id_3")
    private Card card3;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    public UserCompareHistory() {}

    public UserCompareHistory(User user, Card card1, Card card2, Card card3) {
        this.user = user;
        this.card1 = card1;
        this.card2 = card2;
        this.card3 = card3;
    }

    // Getter
    public Integer getCompareId() { return compareId; }
    public User getUser() { return user; }
    public Card getCard1() { return card1; }
    public Card getCard2() { return card2; }
    public Card getCard3() { return card3; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}