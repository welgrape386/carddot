package com.carddot.carddot.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "dev_cards")
@Getter
@Setter
@NoArgsConstructor
public class DevCard {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "dev_id")
    private Integer devId;

    @Column(name = "benefit_group")
    private String benefitGroup;

    @Column(name = "benefit_title")
    private String benefitTitle;

    @Column(name = "benefit_content", columnDefinition = "TEXT")
    private String benefitContent;
}