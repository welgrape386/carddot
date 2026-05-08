package com.carddot.carddot.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "notice")
@Getter
@Setter
@NoArgsConstructor
public class Notice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "notice_id")
    private Integer noticeId;

    @Column(name = "card_id", nullable = false)
    private String cardId;

    @Column(name = "notice_category")
    private String noticeCategory;

    @Column(name = "sub_category")
    private String subCategory;

    @Column(name = "notice_content", columnDefinition = "TEXT")
    private String noticeContent;

    @Column(name = "notice_type", nullable = false)
    private String noticeType;

    @Column(name = "benefit_group")
    private String benefitGroup;

    @Column(name = "benefit_title")
    private String benefitTitle;
}