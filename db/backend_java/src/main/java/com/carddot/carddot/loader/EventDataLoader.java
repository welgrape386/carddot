package com.carddot.carddot.loader;

import com.carddot.carddot.entity.CardEvent;
import com.carddot.carddot.repository.CardEventRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Order(5)
public class EventDataLoader implements ApplicationRunner {

    private final CardEventRepository cardEventRepository;

    private final String[] CSV_FILES = {
            "data/hd_card_events.csv",
            "data/shinhan_event.csv",
            "data/samsung_event.csv"
    };

    @Override
    public void run(ApplicationArguments args) throws Exception {
        for (String csvFile : CSV_FILES) {
            loadEvents(csvFile);
        }
        System.out.println("✅ 전체 이벤트 데이터 CSV 로딩 완료!");
    }

    private void loadEvents(String csvFile) throws Exception {
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
            String eventTitle = getString(cols, headerMap, "event_title");
            if (cardId == null || eventTitle == null) continue;

// 중복 체크
            if (cardEventRepository.existsByCardIdAndEventTitleAndEventContent(
                    cardId, eventTitle, getString(cols, headerMap, "event_content"))) {
                System.out.println("⏭ 이미 존재하는 이벤트 스킵: " + cardId);
                continue;
            }

            CardEvent event = new CardEvent();
            event.setCardId(cardId);
            event.setEventTitle(eventTitle);
            event.setStartDate(parseDate(getString(cols, headerMap, "start_date")));
            event.setEndDate(parseDate(getString(cols, headerMap, "end_date")));
            event.setEventType(getString(cols, headerMap, "event_type"));
            event.setSection(getString(cols, headerMap, "section"));
            event.setEventLink(getString(cols, headerMap, "event_link"));
            event.setEventContent(getString(cols, headerMap, "event_content"));

            cardEventRepository.save(event);
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

    private LocalDate parseDate(String val) {
        if (val == null || val.isBlank()) return null;
        try {
            return LocalDate.parse(val);
        } catch (Exception e) {
            try {
                return LocalDate.parse(val, DateTimeFormatter.ofPattern("yyyy.MM.dd"));
            } catch (Exception e2) {
                return null;
            }
        }
    }
}