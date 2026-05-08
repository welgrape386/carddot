package com.carddot.carddot.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.LocalDate;

@Entity
@Table(name = "card_event")
@Getter
@Setter
@NoArgsConstructor
public class CardEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "event_id")
    private Integer eventId;

    @Column(name = "card_id", nullable = false)
    private String cardId;

    @Column(name = "event_title", nullable = false)
    private String eventTitle;

    @Column(name = "start_date")
    private LocalDate startDate;

    @Column(name = "end_date")
    private LocalDate endDate;

    @Column(name = "event_type")
    private String eventType;

    @Column(name = "section")
    private String section;

    @Column(name = "event_link")
    private String eventLink;

    @Column(name = "event_content", columnDefinition = "TEXT")
    private String eventContent;
}