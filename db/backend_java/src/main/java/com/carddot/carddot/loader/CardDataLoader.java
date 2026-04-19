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

    @Override
    public void run(ApplicationArguments args) throws Exception {

        if (cardRepository.count() > 0) {
            System.out.println("✅ 카드 데이터 이미 존재 - 스킵");
            return;
        }

        ClassPathResource resource = new ClassPathResource("data/신한카드_전체_기본정보.csv");
        BufferedReader reader = new BufferedReader(
                new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8)
        );

        // 헤더 읽어서 컬럼명 → 인덱스 매핑
        String headerLine = reader.readLine().replace("\uFEFF", "");
        System.out.println("헤더 확인: " + headerLine);
        String[] headers = headerLine.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);
        Map<String, Integer> headerMap = new HashMap<>();
        for (int i = 0; i < headers.length; i++) {
            headerMap.put(headers[i].trim(), i);
        }

        String line;
        while ((line = reader.readLine()) != null) {
            String[] cols = line.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);

            Card card = new Card();
            card.setCardId(getString(cols, headerMap, "card_id"));
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
            card.setMinPerformance(getInt(cols, headerMap, "min_performance"));
            card.setSummary(getString(cols, headerMap, "summary"));
            card.setImageUrl(getString(cols, headerMap, "image_url"));
            card.setLinkUrl(getString(cols, headerMap, "link_url"));
            card.setHasCashback(getBool(cols, headerMap, "has_cashback"));
            card.setViewCount(0);
            card.setClickCount(0);
            card.setTotalMaxBenefit(0);
            card.setUpdatedAt(LocalDateTime.now());

            cardRepository.save(card);
        }

        reader.close();
        System.out.println("✅ 카드 데이터 CSV 로딩 완료!");
    }

    // 컬럼명으로 문자열 값 가져오기
    private String getString(String[] cols, Map<String, Integer> headerMap, String colName) {
        Integer idx = headerMap.get(colName);
        if (idx == null || idx >= cols.length) return null;
        String val = cols[idx].trim();
        return val.isEmpty() ? null : val;
    }

    // 컬럼명으로 정수 값 가져오기
    private int getInt(String[] cols, Map<String, Integer> headerMap, String colName) {
        try {
            return (int) Double.parseDouble(getString(cols, headerMap, colName));
        } catch (Exception e) {
            return 0;
        }
    }

    // 컬럼명으로 boolean 값 가져오기
    private boolean getBool(String[] cols, Map<String, Integer> headerMap, String colName) {
        String val = getString(cols, headerMap, colName);
        return "true".equalsIgnoreCase(val);
    }
}