package com.carddot.carddot.user;

import com.carddot.carddot.user.dto.LoginRequest;
import com.carddot.carddot.user.dto.SignupRequest;
import org.springframework.web.bind.annotation.*;
import com.carddot.carddot.user.dto.LoginRequest;

@RestController
@RequestMapping("/api/auth")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/signup")
    public String signup(@RequestBody SignupRequest req) {
        return userService.signup(req);
    }
    @PostMapping("/login")
public String login(@RequestBody LoginRequest req) {
    return userService.login(req);
}
}