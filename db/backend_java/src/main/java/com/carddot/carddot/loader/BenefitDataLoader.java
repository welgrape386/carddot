package com.carddot.carddot.loader;

import com.carddot.carddot.entity.Benefit;
import com.carddot.carddot.entity.BenefitCategory;
import com.carddot.carddot.repository.BenefitCategoryRepository;
import com.carddot.carddot.repository.BenefitRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Order(3)
public class BenefitDataLoader implements ApplicationRunner {

    private final BenefitRepository benefitRepository;
    private final BenefitCategoryRepository benefitCategoryRepository;

    private final String[] CSV_FILES = {
            "data/hd_card_benefit.csv",
            "data/shinhan_benefit.csv",
            "data/samsung_benefit.csv"
    };

    @Override
    public void run(ApplicationArguments args) throws Exception {
        for (String csvFile : CSV_FILES) {
            loadBenefits(csvFile);
        }
        System.out.println("✅ 전체 혜택 데이터 CSV 로딩 완료!");
    }

    private void loadBenefits(String csvFile) throws Exception {
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

            String benefitId = getString(cols, headerMap, "benefit_id");
            if (benefitId == null) continue;

            if (benefitRepository.existsById(benefitId)) {
                System.out.println("⏭ 이미 존재하는 혜택 스킵: " + benefitId);
                continue;
            }

            Benefit benefit = new Benefit();
            benefit.setBenefitId(benefitId);
            benefit.setCardId(getString(cols, headerMap, "card_id"));
            benefit.setRowType(getString(cols, headerMap, "row_type"));
            benefit.setBenefitGroup(getString(cols, headerMap, "benefit_group"));
            benefit.setBenefitTitle(getString(cols, headerMap, "benefit_title"));
            benefit.setBenefitSummary(getString(cols, headerMap, "benefit_summary"));
            benefit.setOnOffline(getString(cols, headerMap, "on_offline"));
            benefit.setBenefitType(getString(cols, headerMap, "benefit_type"));
            benefit.setBenefitValue(getBigDecimal(cols, headerMap, "benefit_value"));
            benefit.setBenefitUnit(getString(cols, headerMap, "benefit_unit"));
            benefit.setTargetMerchants(getString(cols, headerMap, "target_merchants"));
            benefit.setExcludedMerchants(getString(cols, headerMap, "excluded_merchants"));
            benefit.setPerformanceMin(getInt(cols, headerMap, "performance_min"));
            benefit.setPerformanceMax(getIntOrNull(cols, headerMap, "performance_max"));
            benefit.setMinAmount(getIntOrNull(cols, headerMap, "min_amount"));
            benefit.setMaxCount(getIntOrNull(cols, headerMap, "max_count"));
            benefit.setMaxLimit(getIntOrNull(cols, headerMap, "max_limit"));
            benefit.setMaxLimitUnit(getString(cols, headerMap, "max_limit_unit"));
            benefit.setBenefitContent(getString(cols, headerMap, "benefit_content"));

            benefitRepository.save(benefit);

            String categoryIdStr = getString(cols, headerMap, "category_id");
            if (categoryIdStr != null && !categoryIdStr.isBlank()) {
                String[] categoryIds = categoryIdStr.split(",");
                for (String catId : categoryIds) {
                    try {
                        int categoryId = Integer.parseInt(catId.trim());
                        BenefitCategory bc = new BenefitCategory();
                        bc.setBenefitId(benefitId);
                        bc.setCategoryId(categoryId);
                        benefitCategoryRepository.save(bc);
                    } catch (NumberFormatException e) {
                        System.out.println("⚠ category_id 파싱 실패: " + catId);
                    }
                }
            }
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

    private Integer getIntOrNull(String[] cols, Map<String, Integer> headerMap, String colName) {
        try {
            return (int) Double.parseDouble(getString(cols, headerMap, colName));
        } catch (Exception e) {
            return null;
        }
    }

    private BigDecimal getBigDecimal(String[] cols, Map<String, Integer> headerMap, String colName) {
        try {
            return new BigDecimal(getString(cols, headerMap, colName));
        } catch (Exception e) {
            return null;
        }
    }
}