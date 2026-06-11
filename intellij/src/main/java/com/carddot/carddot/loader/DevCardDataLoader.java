package com.carddot.carddot.loader;

import com.carddot.carddot.entity.DevCard;
import com.carddot.carddot.repository.DevCardRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import com.opencsv.CSVReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Order(3)
public class DevCardDataLoader implements ApplicationRunner {

    private final DevCardRepository devCardRepository;

    private final String[] CSV_FILES = {
            "data/hyundai_benefit.csv",
            "data/kb_benefit.csv",
            "data/samsung_benefit.csv"
    };

    @Override
    public void run(ApplicationArguments args) throws Exception {
        for (String csvFile : CSV_FILES) {
            loadDevCards(csvFile);
        }
        System.out.println(" 전체 dev_cards 데이터 CSV 로딩 완료");
    }

    private void loadDevCards(String csvFile) throws Exception {
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
        while ((cols = reader.readNext()) !=null) {

            String benefitGroup = getString(cols, headerMap, "benefit_group");
            String benefitTitle = getString(cols, headerMap, "benefit_title");
            String benefitContent = getString(cols, headerMap, "benefit_content");

            if (benefitGroup == null && benefitTitle == null) continue;

            if (devCardRepository.existsByBenefitGroupAndBenefitTitle(benefitGroup, benefitTitle)) {
                System.out.println("이미 존재하는 dev_card 스킵: " + benefitGroup + " - " + benefitTitle);
                continue;
            }

            DevCard devCard = new DevCard();
            devCard.setBenefitGroup(benefitGroup);
            devCard.setBenefitTitle(benefitTitle);
            devCard.setBenefitContent(benefitContent);
            devCardRepository.save(devCard);
        }

        reader.close();
        System.out.println(csvFile + " dev_cards 로딩 완료");
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