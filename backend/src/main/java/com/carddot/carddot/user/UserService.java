package com.carddot.carddot.user;

import com.carddot.carddot.user.dto.LoginRequest;
import com.carddot.carddot.user.dto.SignupRequest;
import org.springframework.stereotype.Service;
import com.carddot.carddot.user.dto.LoginRequest;

@Service
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public String signup(SignupRequest req) {

        if (userRepository.findByEmail(req.email).isPresent()) {
            return "이미 존재하는 이메일입니다.";
        }

        User user = new User();
        user.setEmail(req.email);
        user.setPassword(req.password);
        user.setName(req.name);
        user.setNickname(req.nickname);
        user.setPhoneNumber(req.phoneNumber);

        userRepository.save(user);

        return "회원가입 성공";
    }
    public String login(LoginRequest req) {

        User user = userRepository.findByEmail(req.email)
            .orElse(null);

        if (user == null) {
            return "이메일이 존재하지 않습니다.";
        }

        if (!user.getPassword().equals(req.password)) {
            return "비밀번호가 틀렸습니다.";
        }

        return "로그인 성공";
    }
}