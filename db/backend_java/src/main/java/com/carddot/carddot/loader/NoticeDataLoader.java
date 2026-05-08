package com.carddot.carddot.loader;

import com.carddot.carddot.entity.Notice;
import com.carddot.carddot.repository.NoticeRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Order(4)
public class NoticeDataLoader implements ApplicationRunner {

    private final NoticeRepository noticeRepository;

    private final String[] CSV_FILES = {
            "data/hd_card_notices.csv",
            "data/shinhan_notice.csv",
            "data/samsung_notice.csv"
    };

    @Override
    public void run(ApplicationArguments args) throws Exception {
        for (String csvFile : CSV_FILES) {
            loadNotices(csvFile);
        }
        System.out.println("✅ 전체 유의사항 데이터 CSV 로딩 완료!");
    }

    private void loadNotices(String csvFile) throws Exception {
        ClassPathResource resource = new ClassPathResource(csvFile);
        if (!resource.exists()) {
            System.out.println("❌ 파일 없음 - 스킵: " + csvFile);
            return;
        }

        BufferedReader reader = new BufferedReader(
                new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8)
        );

        String headerLine = reader.readLine().replace("\uFEFF", "");
        String[] headers = headerLine.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);
        Map<String, Integer> headerMap = new HashMap<>();
        for (int i = 0; i < headers.length; i++) {
            headerMap.put(headers[i].trim(), i);
        }

        String line;
        while ((line = reader.readLine()) != null) {
            String[] cols = line.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);

            String cardId = getString(cols, headerMap, "card_id");
            String noticeContent = getString(cols, headerMap, "notice_content");
            if (noticeContent == null || cardId == null) continue;

            // 중복 체크
            if (noticeRepository.existsByCardIdAndNoticeContent(cardId, noticeContent)) {
                System.out.println("⏭ 이미 존재하는 유의사항 스킵: " + cardId);
                continue;
            }

            Notice notice = new Notice();
            notice.setCardId(cardId);
            notice.setNoticeCategory(getString(cols, headerMap, "notice_category"));
            notice.setSubCategory(getString(cols, headerMap, "sub_category"));
            notice.setNoticeContent(noticeContent);
            notice.setNoticeType("card");

            noticeRepository.save(notice);
        }

        reader.close();
        System.out.println("✅ " + csvFile + " 로딩 완료!");
    }

    private String getString(String[] cols, Map<String, Integer> headerMap, String colName) {
        Integer idx = headerMap.get(colName);
        if (idx == null || idx >= cols.length) return null;
        String val = cols[idx].trim();
        if (val.startsWith("\"") && val.endsWith("\"")) {
            val = val.substring(1, val.length() - 1).trim();
        }
        return val.isEmpty() ? null : val;
    }
}