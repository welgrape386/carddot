package com.carddot.carddot.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "transactions")
@Getter
@Setter
@NoArgsConstructor
public class Transaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "transaction_id")
    private Integer transactionId;

    @Column(name = "user_id", nullable = false)
    private Integer userId;

    @Column(name = "category_id")
    private Integer categoryId;

    @Column(name = "card_id", nullable = false, length = 50)
    private String cardId;

    @Column(name = "merchant_name", length = 100)
    private String merchantName;

    @Column(name = "amount", nullable = false)
    private Integer amount;

    @Column(name = "approved_at", nullable = false)
    private LocalDateTime approvedAt;
}