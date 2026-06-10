package com.example.demo.entity;

import jakarta.persistence.*;
import java.time.LocalDate;

@Entity
@Table(name = "card_event")
public class CardEvent {

    @Id
    @Column(name = "event_id")
    private String eventId;

    @Column(name = "card_id")
    private String cardId;

    @Column(name = "event_title")
    private String eventTitle;

    @Column(name = "section")
    private String section;

    @Column(name = "event_content", columnDefinition = "TEXT")
    private String eventContent;

    @Column(name = "event_link")
    private String eventLink;

    @Column(name = "start_date")
    private String startDate;

    @Column(name = "end_date")
    private String endDate;

    // 기본 생성자
    public CardEvent() {}

    // Getters
    public String getEventId() { return eventId; }
    public String getCardId() { return cardId; }
    public String getEventTitle() { return eventTitle; }
    public String getSection() { return section; }
    public String getEventContent() { return eventContent; }
    public String getEventLink() { return eventLink; }
    public String getStartDate() { return startDate; }
    public void setStartDate(String startDate) { this.startDate = startDate; }
    public String getEndDate() { return endDate; }
    public void setEndDate(String endDate) { this.endDate = endDate; }
}