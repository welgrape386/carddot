package com.example.demo.dto;

public class PasswordUpdateRequest {
    private String currentPassword;
    private String newPassword;
    private String newPasswordConfirm;

    public String getCurrentPassword() { return currentPassword; }
    public String getNewPassword() { return newPassword; }
    public String getNewPasswordConfirm() { return newPasswordConfirm; }
}