package com.example.demo.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "notice")
public class Notice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "notice_id")
    private Integer noticeId;

    @Column(name = "card_id")
    private String cardId;

    @Column(name = "notice_content", columnDefinition = "TEXT")
    private String noticeContent;

    // 기본 생성자
    public Notice() {}

    // Getters
    public Integer getNoticeId() { return noticeId; }
    public String getCardId() { return cardId; }
    public String getNoticeContent() { return noticeContent; }
}