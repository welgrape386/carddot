package com.example.demo.service;

import com.example.demo.dto.*;
import com.example.demo.entity.Benefit;
import com.example.demo.entity.Card;
import com.example.demo.entity.Notice;
import com.example.demo.entity.CardEvent;
import com.example.demo.entity.UserActivity;
import com.example.demo.repository.BenefitRepository;
import com.example.demo.repository.CardRepository;
import com.example.demo.repository.NoticeRepository;
import com.example.demo.repository.CardEventRepository;
import com.example.demo.repository.CardStatsRepository;
import com.example.demo.repository.UserRepository;
import com.example.demo.repository.UserActivityRepository;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;
import java.util.ArrayList;

@Service
public class CardService {

    private final CardRepository cardRepository;
    private final BenefitRepository benefitRepository;
    private final NoticeRepository noticeRepository;
    private final CardEventRepository cardEventRepository;
    
    private final CardScoreService cardScoreService;
    private final BenefitEngineService benefitEngineService;
    
    private final CardStatsRepository cardStatsRepository;
    
    private final UserRepository userRepository;
    private final UserActivityRepository userActivityRepository;

    // 생성자를 통해 조수(Repository)를 모두 주입받음
    public CardService(CardRepository cardRepository, BenefitRepository benefitRepository,
    		NoticeRepository noticeRepository, CardEventRepository cardEventRepository,
    		CardScoreService cardScoreService, BenefitEngineService benefitEngineService,
    		CardStatsRepository cardStatsRepository, UserRepository userRepository,
    		UserActivityRepository userActivityRepository) {
        this.cardRepository = cardRepository;
        this.benefitRepository = benefitRepository;
        this.noticeRepository = noticeRepository;
        this.cardEventRepository = cardEventRepository;
        this.cardScoreService = cardScoreService;
        this.benefitEngineService = benefitEngineService;
        this.cardStatsRepository = cardStatsRepository;
        this.userRepository = userRepository;
        this.userActivityRepository = userActivityRepository;
    }

    // 1. 전체 카드 조회
    @Transactional(readOnly = true)
    public List<CardListResponse> getAllCards() {
        List<Card> cards = cardRepository.findAll();
        return cards.stream()
                .map(card -> {
                	List<Benefit> benefits = benefitRepository.findByCardId(card.getCardId());
                    List<String> categoryNames = benefits.stream()
                            .filter(b -> b.getCategories() != null)
                            .flatMap(b -> b.getCategories().stream())
                            .map(cat -> cat.getCategoryName()) // 이름만
                            .distinct() // 중복 제거
                            .toList();
                    
                	return new CardListResponse(
                            card.getCardId(), card.getCardName(),card.getCompany(),
                            card.getCardType(), card.isHasTransport(),
                            card.getAnnualFeeDomBasic(), card.getAnnualFeeDomPremium(),
                            card.getAnnualFeeForBasic(), card.getAnnualFeeForPremium(),
                            card.getMinPerformance(),
                            card.getSummary(), card.getImageUrl(),
                            categoryNames
                    );
                })
                .collect(Collectors.toList());
    }

    // 2. 특정 카드 상세 조회
    @Transactional
    public CardDetailResponse getCardDetail(String cardId) {
        // 1. 카드 기본 정보 가져오기 (없으면 에러 던짐)
        Card card = cardRepository.findById(cardId)
                .orElseThrow(() -> new IllegalArgumentException("해당 카드를 찾을 수 없습니다."));
        
        // 카드 찾으면 클릭 수 + 1
        cardStatsRepository.incrementDetailClick(cardId);
        
        // 최근 본 카드 이력 저장
        // 인증 정보 확인
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        // 회원이면
        if (auth != null && auth.isAuthenticated() && !auth.getPrincipal().equals("anonymousUser")) {
            String loginEmail = (String) auth.getPrincipal(); // JWT에서 꺼낸 이메일
            
            // 이메일로 유저의 DB PK(user_id) 찾아옴
            userRepository.findByEmail(loginEmail).ifPresent(user -> {
                UserActivity activity = new UserActivity();
                activity.setUser(user); // 유저 ID 세팅
                activity.setCard(card); // 지금 보고 있는 카드 ID 세팅
                activity.setType("RECENT"); // 타입은 "RECENT" 고정
                // createdAt은 DB 디폴트 설정에 의해 알아서 현재 시간으로 들어감
                
                userActivityRepository.save(activity); // DB에 저장
            });
        }
        
        // A. 주요 혜택 매핑
        // 2. 이 카드에 속한 혜택 목록 가져오기
        List<Benefit> benefits = benefitRepository.findByCardId(cardId);

        // 3. 혜택 엔티티(Entity)를 혜택 DTO로 변환
        List<CardDetailResponse.BenefitDto> benefitDtos = benefits.stream()
                .map(b -> {
                    // 카테고리 리스트 중 첫 번째 카테고리의 이름을 가져오되, 비어있으면 "기타"
                    String categoryName = (b.getCategories() != null && !b.getCategories().isEmpty()) 
                                          ? b.getCategories().get(0).getCategoryName() 
                                          : "기타";
                    
                    // 더 이상 안 쓰는 변수
                    // 수치(10)와 단위(%)를 합쳐서 "10%" 형태의 텍스트로 만듦
                    // String valueText = (b.getBenefitValue() != null ? b.getBenefitValue().toString() : "") 
                    //                  + (b.getBenefitUnit() != null ? b.getBenefitUnit() : "");
                    
                    // 실질 할인율 실시간 계산
                    CalculationResult calcResult = benefitEngineService.calculateEffectiveRate(b, card.getCompany());
                    String effectiveRateText = calcResult.getRate().doubleValue() > 0 
                                               ? calcResult.getRate().toString() + "%" : "-";
                    String effectiveBasis = calcResult.getBasis();

                    return new CardDetailResponse.BenefitDto(
                            categoryName,
                            b.getTargetMerchants(),
                            b.getUiTitle(),
                            b.getUiContent(),
                            effectiveRateText,
                            b.getBenefitValue(),
                            b.getBenefitUnit(),
                            b.getMaxLimit(),
                            b.getMaxLimitUnit(),
                            b.getGroupMaxLimit(),
                            b.getGroupMaxLimitUnit(),
                            effectiveBasis
                    );
                }).collect(Collectors.toList());
        
        // B. 유의사항 매핑
        List<Notice> notices = noticeRepository.findByCardId(cardId);
        List<CardDetailResponse.NoticeDto> noticeDtos = notices.stream()
                .map(n -> new CardDetailResponse.NoticeDto(n.getCardId(), n.getNoticeContent()))
                .collect(Collectors.toList());
        
        // C. 이벤트 매핑
        List<CardEvent> events = cardEventRepository.findByCardId(cardId);
        List<CardDetailResponse.EventDto> eventDtos = events.stream()
                .map(e -> {
                	String startDateStr = (e.getStartDate() != null) ? e.getStartDate() : "";
                    String endDateStr = (e.getEndDate() != null) ? e.getEndDate() : "";
                    
                    return new CardDetailResponse.EventDto(
                    		e.getEventTitle(), 
                            e.getSection(), 
                            e.getEventContent(), 
                            e.getEventLink(), 
                            startDateStr,
                            endDateStr
                    		);
                }).collect(Collectors.toList());
        
        // 4. 최종 응답 DTO로 조립해서 반환
        return new CardDetailResponse(
        		card.getCardId(), card.getCompany(), card.getCardType(), card.getNetwork(),
                card.getCardName(), card.isHasTransport(), card.getAnnualFeeDomBasic(),
                card.getAnnualFeeDomPremium(), card.getAnnualFeeForBasic(), card.getAnnualFeeForPremium(),
                card.getMinPerformance(), card.getLinkUrl(), card.getImageUrl(),
                benefitDtos, noticeDtos, eventDtos
        );
    }
    
    // 3. 카드 비교
    @Transactional(readOnly = true)
    public List<CardCompareResponse> compareCards(List<String> cardIds, String personaType) {
        // 최대 3개까지만 비교 가능
        if (cardIds == null || cardIds.size() > 3) {
            throw new IllegalArgumentException("카드는 최대 3개까지만 비교할 수 있습니다.");
        }

        List<CardCompareResponse> responseList = new ArrayList<>();

        for (String cardId : cardIds) {
            Card card = cardRepository.findById(cardId)
                    .orElseThrow(() -> new IllegalArgumentException("해당 카드를 찾을 수 없습니다: " + cardId));
            
            // 카드 점수 가져오기
            CardScoreResponse scores = cardScoreService.getCardScores(card, personaType);
            
            // 혜택 가져오기
            List<Benefit> benefits = benefitRepository.findByCardId(cardId);
            List<BenefitCompareDto> benefitDtos = benefits.stream().map(b -> {
                String categoryName = (b.getCategories() != null && !b.getCategories().isEmpty()) 
                                      ? b.getCategories().get(0).getCategoryName() : "기타";
                String valueText = (b.getBenefitValue() != null ? b.getBenefitValue().toString() : "") 
                                 + (b.getBenefitUnit() != null ? b.getBenefitUnit() : "");
                
             // 실질 할인율 실시간 계산
                CalculationResult calcResult = benefitEngineService.calculateEffectiveRate(b, card.getCompany());
                String effectiveRateText = calcResult.getRate().doubleValue() > 0 
                                           ? calcResult.getRate().toString() + "%" : "-";
                String effectiveBasis = calcResult.getBasis();
                
                return new BenefitCompareDto(
                        categoryName, b.getBenefitType(), valueText, b.getUiTitle(), b.getUiContent(),
                        effectiveRateText, effectiveBasis
                );
            }).collect(Collectors.toList());

            responseList.add(new CardCompareResponse(
                    card.getCardId(), card.getCompany(), card.getCardName(),
                    card.getCardType(), card.getNetwork(), card.getMinPerformance(),
                    card.getImageUrl(), scores, benefitDtos
            ));
        }
        return responseList;
    }
    
    // 4. 카드 비교 - 카드 검색 팝업
    @Transactional(readOnly = true)
    public List<CardSearchResponse> searchCards(String keyword) {
        List<Card> cards;
        if (keyword == null || keyword.trim().isEmpty()) {
            cards = cardRepository.findAll(); // 검색어 없으면 전체 반환
        } else {
            cards = cardRepository.findByCardNameContainingOrCompanyContaining(keyword, keyword);
        }

        return cards.stream().map(card -> new CardSearchResponse(
                card.getCardId(), card.getImageUrl(), card.getCardType(),
                card.getCompany(), card.getCardName(), card.getAnnualFeeDomBasic()
        )).collect(Collectors.toList());
    }
    
    // 5. 카드 종합 점수
    @Transactional(readOnly = true)
    public CardScoreResponse getCardScores(String cardId, String personaType) {
        // DB에서 카드를 찾아옴
        Card card = cardRepository.findById(cardId)
                .orElseThrow(() -> new IllegalArgumentException("해당 카드를 찾을 수 없습니다: " + cardId));
        
        // 찾은 Card 객체를 CardScoreService로 넘겨서 결과를 받아옴
        return cardScoreService.getCardScores(card, personaType);
    }
}