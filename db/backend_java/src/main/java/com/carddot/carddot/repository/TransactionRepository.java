package com.carddot.carddot.repository;

import com.carddot.carddot.entity.Transaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface TransactionRepository extends JpaRepository<Transaction, Integer> {
    long countByCardIdStartingWith(String prefix);

    @Query("SELECT COUNT(t) FROM Transaction t JOIN Card c ON t.cardId = c.cardId WHERE c.company = :company")
    long countByCardCompany(@Param("company") String company);
}