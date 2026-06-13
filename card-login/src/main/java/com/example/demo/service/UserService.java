package com.example.demo.service;

import com.example.demo.dto.PasswordUpdateRequest;
import com.example.demo.dto.RecentCardResponse;
import com.example.demo.dto.UserProfileUpdateRequest;
import com.example.demo.dto.RecentCompareResponse;
import com.example.demo.entity.User;
import com.example.demo.entity.UserActivity;
import com.example.demo.entity.Card;
import com.example.demo.entity.UserCompareHistory;
import com.example.demo.repository.UserCompareHistoryRepository;
import com.example.demo.repository.UserRepository;
import com.example.demo.repository.UserActivityRepository;
import com.example.demo.repository.CardRepository;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final UserActivityRepository userActivityRepository;
    private final CardRepository cardRepository;
    private final BCryptPasswordEncoder passwordEncoder;
    private final UserCompareHistoryRepository userCompareHistoryRepository;

    public UserService(UserRepository userRepository, UserActivityRepository userActivityRepository, 
                       CardRepository cardRepository, BCryptPasswordEncoder passwordEncoder,
                       UserCompareHistoryRepository userCompareHistoryRepository) {
        this.userRepository = userRepository;
        this.userActivityRepository = userActivityRepository;
        this.cardRepository = cardRepository;
        this.passwordEncoder = passwordEncoder;
        this.userCompareHistoryRepository = userCompareHistoryRepository;
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

        List<UserActivity> activities = userActivityRepository.findTop10ByUser_IdAndTypeOrderByCreatedAtDesc(user.getId(), "RECENT");

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
    
    // 카드 비교 이력 저장
    @Transactional
    public void recordCardCompare(String email, List<String> cardIds) {
        if (cardIds == null || cardIds.size() < 2) return;

        User user = userRepository.findByEmail(email).orElse(null);
        if (user == null) return;
        
        Set<String> inputSet = new HashSet<>(cardIds);
        
        List<UserCompareHistory> histories = userCompareHistoryRepository.findByUser_Id(user.getId());

        boolean isSubsetOfExisting = false;
        UserCompareHistory supersetToBump = null;

        // 포함 관계 검사
        for (UserCompareHistory h : histories) {
            Set<String> historySet = new HashSet<>();
            if (h.getCard1() != null) historySet.add(h.getCard1().getCardId());
            if (h.getCard2() != null) historySet.add(h.getCard2().getCardId());
            if (h.getCard3() != null) historySet.add(h.getCard3().getCardId());

            if (historySet.containsAll(inputSet)) {
                // Case A: 기존 [A, B, C]가 새 요청 [A, B]를 완전히 포함
                isSubsetOfExisting = true;
                supersetToBump = h; // 최상단으로 끌어올릴 타겟 지정
                
            } else if (inputSet.containsAll(historySet)) {
                // Case B: 새 요청 [A, B, C]가 기존 기록 [A, B]를 포함
                // 기존 작은 집합은 삭제
                userCompareHistoryRepository.delete(h);
            }
        }
        
        // 최종 저장 판별
        if (isSubsetOfExisting && supersetToBump != null) {
            // [A, B] 저장은 무시, 기존에 있던 [A, B, C]를 지웠다가 다시 저장해서 목록 최상단으로 끌어올림
            userCompareHistoryRepository.delete(supersetToBump);
            UserCompareHistory bumpedHistory = new UserCompareHistory(
                    user, 
                    supersetToBump.getCard1(), 
                    supersetToBump.getCard2(), 
                    supersetToBump.getCard3()
            );
            userCompareHistoryRepository.save(bumpedHistory);
            
        } else {
        String c1Id = cardIds.get(0);
        String c2Id = cardIds.get(1);
        String c3Id = cardIds.size() > 2 ? cardIds.get(2) : null;

        Card card1 = cardRepository.findById(c1Id).orElse(null);
        Card card2 = cardRepository.findById(c2Id).orElse(null);
        Card card3 = c3Id != null ? cardRepository.findById(c3Id).orElse(null) : null;

        if (card1 != null && card2 != null) {
            UserCompareHistory newHistory = new UserCompareHistory(user, card1, card2, card3);
            userCompareHistoryRepository.save(newHistory);
            }
        }
    }
    
    // 마이페이지에서 비교 이력 10개 반환
    @Transactional(readOnly = true)
    public List<RecentCompareResponse> getRecentCompares(String email) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다."));

        List<UserCompareHistory> histories = userCompareHistoryRepository.findTop10ByUser_IdOrderByCreatedAtDesc(user.getId());

        return histories.stream().map(h -> {
            List<RecentCompareResponse.CardSimpleDto> cardDtos = new ArrayList<>();
            
            if (h.getCard1() != null) cardDtos.add(new RecentCompareResponse.CardSimpleDto(h.getCard1().getCardId(), h.getCard1().getCompany(), h.getCard1().getCardName(), h.getCard1().getImageUrl()));
            if (h.getCard2() != null) cardDtos.add(new RecentCompareResponse.CardSimpleDto(h.getCard2().getCardId(), h.getCard2().getCompany(), h.getCard2().getCardName(), h.getCard2().getImageUrl()));
            if (h.getCard3() != null) cardDtos.add(new RecentCompareResponse.CardSimpleDto(h.getCard3().getCardId(), h.getCard3().getCompany(), h.getCard3().getCardName(), h.getCard3().getImageUrl()));

            return new RecentCompareResponse(h.getCompareId(), h.getCreatedAt(), cardDtos);
        }).collect(Collectors.toList());
    }
}