package com.carddot.carddot.loader;

import com.carddot.carddot.entity.Card;
import com.carddot.carddot.entity.Transaction;
import com.carddot.carddot.entity.User;
import com.carddot.carddot.repository.CardRepository;
import com.carddot.carddot.repository.CategoryRepository;
import com.carddot.carddot.repository.TransactionRepository;
import com.carddot.carddot.repository.UserRepository;
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
import java.util.stream.Collectors;

@Component
@RequiredArgsConstructor
@Order(2)
public class TransactionDataLoader implements ApplicationRunner {

    private final TransactionRepository transactionRepository;
    private final CardRepository cardRepository;
    private final CategoryRepository categoryRepository;
    private final UserRepository userRepository;

    @Override
    public void run(ApplicationArguments args) throws Exception {

        // 1번 유저 제외
        List<Integer> userIds = userRepository.findAll()
                .stream()
                .map(User::getUserId)
                .filter(id -> id != 1)
                .collect(Collectors.toList());

        Map<String, Integer> categoryMap = new HashMap<>();
        categoryRepository.findAll().forEach(c ->
                categoryMap.put(c.getCategoryName(), c.getCategoryId())
        );

        Map<String, Integer> merchantMap = new HashMap<>();
        ClassPathResource resource = new ClassPathResource("data/merchant_category.csv");
        BufferedReader reader = new BufferedReader(
                new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8)
        );
        reader.readLine();
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

        generateTransactions("현대", 30, userIds, merchantMap);
        generateTransactions("신한", 30, userIds, merchantMap);
        generateTransactions("삼성", 30, userIds, merchantMap);

        System.out.println("✅ 전체 결제 더미 데이터 생성 완료!");
    }

    private void generateTransactions(String company, int count,
                                      List<Integer> userIds, Map<String, Integer> merchantMap) {

        long existing = transactionRepository.countByCardCompany(company);
        if (existing >= count) {
            System.out.println("✅ " + company + " 결제 더미 데이터 이미 존재 - 스킵");
            return;
        }

        List<Card> cards = cardRepository.findAll()
                .stream()
                .filter(c -> c.getCompany().equals(company))
                .collect(Collectors.toList());

        if (cards.isEmpty()) {
            System.out.println("❌ " + company + " 카드 데이터 없음 - 스킵");
            return;
        }

        Random random = new Random();
        String[] merchantNames = merchantMap.keySet().toArray(new String[0]);

        for (int i = 0; i < count; i++) {
            String merchantName = merchantNames[random.nextInt(merchantNames.length)];

            Transaction tx = new Transaction();
            tx.setUserId(userIds.get(random.nextInt(userIds.size())));
            tx.setCardId(cards.get(random.nextInt(cards.size())).getCardId());
            tx.setMerchantName(merchantName);
            tx.setCategoryId(merchantMap.get(merchantName));
            tx.setAmount((random.nextInt(50) + 1) * 1000);
            tx.setApprovedAt(LocalDateTime.now().minusDays(random.nextInt(180)));

            transactionRepository.save(tx);
        }

        System.out.println("✅ " + company + " 결제 더미 데이터 " + count + "개 생성 완료!");
    }
}