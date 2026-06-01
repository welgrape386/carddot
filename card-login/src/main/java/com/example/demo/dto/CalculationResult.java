package com.example.demo.dto;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class CalculationResult {
    private BigDecimal rate;
    private String basis;

    public CalculationResult(double rate, String basis) {
        // 소수점 둘째 자리까지 표현
        this.rate = new BigDecimal(rate).setScale(2, RoundingMode.HALF_UP);
        this.basis = basis;
    }

    public BigDecimal getRate() { return rate; }
    public String getBasis() { return basis; }
}