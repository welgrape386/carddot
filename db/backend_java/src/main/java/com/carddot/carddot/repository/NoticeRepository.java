package com.carddot.carddot.repository;

import com.carddot.carddot.entity.Notice;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NoticeRepository extends JpaRepository<Notice, Integer> {
    boolean existsByCardIdAndNoticeContent(String cardId, String noticeContent);
}