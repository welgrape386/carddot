package com.carddot.carddot.loader;

import com.carddot.carddot.entity.CardEvent;
import com.carddot.carddot.repository.CardEventRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;
import com.carddot.carddot.repository.CardRepository;

import com.opencsv.CSVReader;
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

    private final CardRepository cardRepository;

    private final String[] CSV_FILES = {
            "data/kb_events.csv",
            "data/hyundai_events.csv",
            "data/samsung_events.csv",
    };

    @Override
    public void run(ApplicationArguments args) throws Exception {
        for (String csvFile : CSV_FILES) {
            loadEvents(csvFile);
        }
        System.out.println("전체 이벤트 데이터 CSV 로딩 완료");
    }

    private void loadEvents(String csvFile) throws Exception {
        ClassPathResource resource = new ClassPathResource(csvFile);
        if (!resource.exists()) {
            System.out.println("파일 없음 - 스킵: " + csvFile);
            return;
        }

        CSVReader reader = new CSVReader(
                new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8)
        );

        String[] headers = reader.readNext();
        headers[0] = headers[0].replace("\uFEFF", "");
        Map<String, Integer> headerMap = new HashMap<>();
        for (int i = 0; i < headers.length; i++) {
            headerMap.put(headers[i].trim(), i);
        }

        String[] cols;
        while ((cols = reader.readNext()) != null) {
            String cardId = getString(cols, headerMap, "card_id");
            String eventTitle = getString(cols, headerMap, "event_title");
            if (cardId == null || cardId.isBlank() || eventTitle == null) continue;

            if (!cardRepository.existsByCardId(cardId)) {
                System.out.println(" card 테이블에 없는 card_id 스킵: " + cardId);
                continue;
            }

            // 중복 체크
            String section = getString(cols, headerMap, "section");
            String eventId = getString(cols, headerMap, "event_id");
            if (eventId != null && cardEventRepository.existsByEventIdAndSection(eventId,section)){
                System.out.println("이미 존재하는 이벤트 스킵: " + eventId + " - " + section);
                continue;
            }

            CardEvent event = new CardEvent();
            event.setEventId(eventId);
            event.setCardId(cardId);
            event.setEventTitle(eventTitle);
            event.setStartDate(parseDate(getString(cols, headerMap, "start_date")));
            event.setEndDate(parseDate(getString(cols, headerMap, "end_date")));
            event.setEventType(getString(cols, headerMap, "event_type"));
            event.setSection(section);
            event.setEventLink(getString(cols, headerMap, "event_link"));
            event.setEventContent(getString(cols, headerMap, "event_content"));
            cardEventRepository.save(event);
        }

        reader.close();
        System.out.println( csvFile + " 로딩 완료");
    }

    private String getString(String[] cols, Map<String, Integer> headerMap, String colName) {
        Integer idx = headerMap.get(colName);
        if (idx == null || idx >= cols.length) return null;
        String val = cols[idx].trim();
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