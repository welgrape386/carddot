package com.carddot.carddot.loader;

import com.carddot.carddot.entity.User;
import com.carddot.carddot.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

@Component
@RequiredArgsConstructor
public class DummyUserLoader implements ApplicationRunner {

    private final UserRepository userRepository;

    @Override
    public void run(ApplicationArguments args) throws Exception {

        if (userRepository.count() > 0) {
            System.out.println("✅ 유저 더미 데이터 이미 존재 - 스킵");
            return;
        }

        String[] lastNames = {"김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"};
        String[] firstNames = {"민준", "서연", "지호", "수아", "도윤", "하은", "준서", "지아", "현우", "민서",
                "지원", "예린", "승현", "나은", "태양", "소희", "재원", "유진", "동현", "채원"};

        Random random = new Random();
        List<User> users = new ArrayList<>();

        for (int i = 1; i <= 50; i++) {
            String lastName = lastNames[random.nextInt(lastNames.length)];
            String firstName = firstNames[random.nextInt(firstNames.length)];

            // 010-XXXX-XXXX 랜덤 생성
            String phone = "010-" +
                    String.format("%04d", random.nextInt(10000)) + "-" +
                    String.format("%04d", random.nextInt(10000));

            User user = new User();
            user.setEmail("user" + i + "@carddot.com");
            user.setPassword("password" + i + "!");   // password1! ~ password50!
            user.setName(lastName + firstName);
            user.setPhoneNumber(phone);
            user.setCreatedAt(LocalDateTime.now());
            users.add(user);
        }

        userRepository.saveAll(users);
        System.out.println("✅ 더미 유저 50명 생성 완료!");
    }
}