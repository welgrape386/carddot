package com.carddot.carddot.loader;

import com.carddot.carddot.entity.Card;
import com.carddot.carddot.entity.Transaction;
import com.carddot.carddot.repository.CardRepository;
import com.carddot.carddot.repository.CategoryRepository;
import com.carddot.carddot.repository.TransactionRepository;
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
import java.util.List;
import java.util.Map;
import java.util.Random;

@Component
@RequiredArgsConstructor
@Order(2)
public class TransactionDataLoader implements ApplicationRunner {

    private final TransactionRepository transactionRepository;
    private final CardRepository cardRepository;
    private final CategoryRepository categoryRepository;

    @Override
    public void run(ApplicationArguments args) throws Exception {

//        if (transactionRepository.count() > 0) {
//            System.out.println("✅ 결제 더미 데이터 이미 존재 - 스킵");
//            return;
//        }
//
        // 카드 목록 조회
        List<Card> cards = cardRepository.findAll();
        if (cards.isEmpty()) {
            System.out.println("❌ 카드 데이터 없음 - 스킵");
            return;
        }

        // category_name → category_id 맵 생성
        Map<String, Integer> categoryMap = new HashMap<>();
        categoryRepository.findAll().forEach(c ->
                categoryMap.put(c.getCategoryName(), c.getCategoryId())
        );

        // merchant_category.csv 읽어서 가맹점 → category_id 맵 생성
        Map<String, Integer> merchantMap = new HashMap<>();
        ClassPathResource resource = new ClassPathResource("data/merchant_category.csv");
        BufferedReader reader = new BufferedReader(
                new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8)
        );
        reader.readLine(); // 헤더 스킵
        String line;
        while ((line = reader.readLine()) != null) {
            String[] cols = line.split(",");
            if (cols.length < 2) continue;
            String merchantName = cols[0].trim();
            String categoryName = cols[1].trim();
            Integer categoryId = categoryMap.get(categoryName);
            if (categoryId != null) {
                merchantMap.put(merchantName, categoryId);
            }
        }
        reader.close();

        // 더미 결제 데이터 10개 생성
        Random random = new Random();
        String[] merchantNames = merchantMap.keySet().toArray(new String[0]);

        for (int i = 0; i < 30; i++) {
            String merchantName = merchantNames[random.nextInt(merchantNames.length)];

            Transaction tx = new Transaction();
            tx.setUserId(random.nextInt(50) + 1);
            tx.setCardId(cards.get(random.nextInt(cards.size())).getCardId());
            tx.setMerchantName(merchantName);
            tx.setCategoryId(merchantMap.get(merchantName));
            tx.setAmount((random.nextInt(50) + 1) * 1000);

            //기간 조정
            tx.setApprovedAt(LocalDateTime.now().minusDays(random.nextInt(180)));
            // ✅ 기간 직접 지정 방식
            // LocalDateTime start = LocalDateTime.of(2025, 1, 1, 0, 0);   // 시작일 (년, 월, 일, 시, 분)
            // LocalDateTime end = LocalDateTime.of(2025, 12, 31, 23, 59); // 종료일 (년, 월, 일, 시, 분)
            // long seconds = java.time.temporal.ChronoUnit.SECONDS.between(start, end); // 시작~종료 사이 총 초(seconds) 계산
            // tx.setApprovedAt(start.plusSeconds((long)(random.nextDouble() * seconds))); // 총 초 중 랜덤 값 더해서 날짜 생성

            transactionRepository.save(tx);
        }

        System.out.println("✅ 결제 더미 데이터 생성 완료!");
    }
}