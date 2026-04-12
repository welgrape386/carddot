package com.example.demo.repository;

import com.example.demo.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    // loginId 대신 email로 찾도록 이름 변경
    Optional<User> findByEmail(String email);
    boolean existsByEmail(String email);
}