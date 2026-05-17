package com.carddot.carddot.loader;

import com.carddot.carddot.entity.Card;
import com.carddot.carddot.repository.CardRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Order(1)
public class CardDataLoader implements ApplicationRunner {

    private final CardRepository cardRepository;

    private final String[] CSV_FILES = {
            "data/hd_card_info.csv",
            "data/shinhan_info.csv",
            "data/samsung_info.csv"
    };

    @Override
    public void run(ApplicationArguments args) throws Exception {
        for (String csvFile : CSV_FILES) {
            loadCards(csvFile);
        }
        System.out.println("✅ 전체 카드 데이터 CSV 로딩 완료!");
    }

    private void loadCards(String csvFile) throws Exception {
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
            if (cardId == null) continue;

            if (cardRepository.existsById(cardId)) {
                System.out.println("⏭ 이미 존재하는 카드 스킵: " + cardId);
                continue;
            }

            Card card = new Card();
            card.setCardId(cardId);
            card.setCompany(getString(cols, headerMap, "company"));
            card.setCardName(getString(cols, headerMap, "card_name"));
            card.setCardType(getString(cols, headerMap, "card_type"));
            card.setNetwork(getString(cols, headerMap, "network"));
            card.setIsDomesticForeign(getBool(cols, headerMap, "is_domestic_foreign"));
            card.setHasTransport(getBool(cols, headerMap, "has_transport"));
            card.setAnnualFeeDomBasic(getInt(cols, headerMap, "annual_fee_dom_basic"));
            card.setAnnualFeeDomPremium(getInt(cols, headerMap, "annual_fee_dom_premium"));
            card.setAnnualFeeForBasic(getInt(cols, headerMap, "annual_fee_for_basic"));
            card.setAnnualFeeForPremium(getInt(cols, headerMap, "annual_fee_for_premium"));
            card.setAnnualFeeNotes(getString(cols, headerMap, "annual_fee_notes"));  // 추가
            card.setMinPerformance(getInt(cols, headerMap, "min_performance"));
            card.setSummary(getString(cols, headerMap, "summary"));
            card.setImageUrl(getString(cols, headerMap, "image_url"));
            card.setLinkUrl(getString(cols, headerMap, "link_url"));
            card.setHasCashback(getBool(cols, headerMap, "has_cashback"));
            card.setDetailCount(0);
            card.setUrlCount(0);
            card.setTotalMaxBenefit(0);
            card.setUpdatedAt(LocalDateTime.now());

            cardRepository.save(card);
            System.out.println("✅ 카드 추가: " + cardId);
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

    private int getInt(String[] cols, Map<String, Integer> headerMap, String colName) {
        try {
            return (int) Double.parseDouble(getString(cols, headerMap, colName));
        } catch (Exception e) {
            return 0;
        }
    }

    private boolean getBool(String[] cols, Map<String, Integer> headerMap, String colName) {
        String val = getString(cols, headerMap, colName);
        return "true".equalsIgnoreCase(val);
    }
}