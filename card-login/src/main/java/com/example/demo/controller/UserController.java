package com.example.demo.controller;

import com.example.demo.dto.PasswordUpdateRequest;
import com.example.demo.dto.RecentCardResponse;
import com.example.demo.dto.UserProfileUpdateRequest;
import com.example.demo.security.JwtTokenProvider;
import com.example.demo.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/users")
@CrossOrigin(origins = {"http://localhost:3000", "https://carddot.vercel.app"})
public class UserController {

    private final UserService userService;
    private final JwtTokenProvider jwtTokenProvider;

    public UserController(UserService userService, JwtTokenProvider jwtTokenProvider) {
        this.userService = userService;
        this.jwtTokenProvider = jwtTokenProvider;
    }

    // 공통 메서드: 헤더에서 이메일 추출
    private String getEmailFromToken(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            String token = bearerToken.substring(7);
            if (jwtTokenProvider.validateToken(token)) {
                return jwtTokenProvider.getLoginId(token);
            }
        }
        throw new IllegalArgumentException("유효하지 않거나 만료된 토큰입니다.");
    }

    // 개인정보 수정 API
    @PutMapping("/profile")
    public ResponseEntity<String> updateProfile(HttpServletRequest httpServletRequest, @RequestBody UserProfileUpdateRequest request) {
        try {
            String email = getEmailFromToken(httpServletRequest);
            userService.updateProfile(email, request);
            return ResponseEntity.ok("개인정보가 성공적으로 수정되었습니다.");
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(e.getMessage());
        }
    }

    // 비밀번호 수정 API
    @PutMapping("/password")
    public ResponseEntity<String> updatePassword(HttpServletRequest httpServletRequest, @RequestBody PasswordUpdateRequest request) {
        try {
            String email = getEmailFromToken(httpServletRequest);
            userService.updatePassword(email, request);
            return ResponseEntity.ok("비밀번호가 성공적으로 변경되었습니다.");
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(e.getMessage());
        }
    }

    // 최근 본 카드 10개 조회 API
    @GetMapping("/recent-cards")
    public ResponseEntity<?> getRecentCards(HttpServletRequest httpServletRequest) {
        try {
            String email = getEmailFromToken(httpServletRequest);
            List<RecentCardResponse> recentCards = userService.getRecentCards(email);
            return ResponseEntity.ok(recentCards);
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(e.getMessage());
        }
    }
}