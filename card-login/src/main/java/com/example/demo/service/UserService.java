package com.example.demo.service;

import com.example.demo.dto.PasswordUpdateRequest;
import com.example.demo.dto.RecentCardResponse;
import com.example.demo.dto.UserProfileUpdateRequest;
import com.example.demo.entity.User;
import com.example.demo.entity.UserActivity;
import com.example.demo.entity.Card;
import com.example.demo.repository.UserRepository;
import com.example.demo.repository.UserActivityRepository;
import com.example.demo.repository.CardRepository;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final UserActivityRepository userActivityRepository;
    private final CardRepository cardRepository;
    private final BCryptPasswordEncoder passwordEncoder;

    public UserService(UserRepository userRepository, UserActivityRepository userActivityRepository, 
                       CardRepository cardRepository, BCryptPasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.userActivityRepository = userActivityRepository;
        this.cardRepository = cardRepository;
        this.passwordEncoder = passwordEncoder;
    }

    // 개인정보 수정
    @Transactional
    public void updateProfile(String email, UserProfileUpdateRequest request) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다."));
        
        user.setName(request.getName());
        user.setEmail(request.getEmail());
        user.setPhoneNumber(request.getPhoneNumber());
        // 이메일 변경 시 클라이언트 측에서 다시 로그인(새 토큰 발급)을 유도하는 게 좋음
    }

    // 비밀번호 변경
    @Transactional
    public void updatePassword(String email, PasswordUpdateRequest request) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다."));

        if (!passwordEncoder.matches(request.getCurrentPassword(), user.getPassword())) {
            throw new IllegalArgumentException("현재 비밀번호가 일치하지 않습니다.");
        }
        if (!request.getNewPassword().equals(request.getNewPasswordConfirm())) {
            throw new IllegalArgumentException("새 비밀번호가 서로 일치하지 않습니다.");
        }

        user.setPassword(passwordEncoder.encode(request.getNewPassword()));
    }

    // 최근 본 카드 조회
    @Transactional(readOnly = true)
    public List<RecentCardResponse> getRecentCards(String email) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다."));

        List<UserActivity> activities = userActivityRepository.findTop10ByUser_IdAndTypeOrderByCreatedAtDesc(user.getId(), "VIEW");

        return activities.stream()
                .map(UserActivity::getCard)
                .distinct() // 중복 카드 제거
                .map(card -> new RecentCardResponse(
                        card.getCardId(), card.getCompany(), card.getCardName(), 
                        card.getAnnualFeeDomBasic(), card.getImageUrl()
                ))
                .collect(Collectors.toList());
    }

    // 카드 상세 조회 시 이 메서드를 호출해서 '최근 본 카드' 기록 남기면 됨
    // 수정 예정
    @Transactional
    public void recordCardView(String email, String cardId) {
        User user = userRepository.findByEmail(email).orElse(null);
        Card card = cardRepository.findById(cardId).orElse(null);
        
        if (user != null && card != null) {
            UserActivity activity = new UserActivity(user, card, "VIEW");
            userActivityRepository.save(activity);
        }
    }
}