import { useEffect, useState } from "react";
import { Link } from "react-router";

import { getCards, filterCards } from "../../api/card";
import { CardListItem } from "../../types/card";

interface FilterState {
  cardType: string;
  company: string;
  annualFee: string;
  minPerformance: string;
  hasEvent: boolean;
  hasTransport: boolean;
  sort: string;
}

const cardTypeOptions = [
  "전체",
  "신용",
  "체크",
];

const companyOptions = [
  "전체",
  "국민",
  "삼성",
  "신한",
  "현대",
];

const sortOptions = [
  "인기순",
  "혜택많은순",
  "혜택적은순",
];

const annualFeeOptions = [
  "전체",
  "~1만원",
  "~3만원",
  "~10만원",
  "10만원~",
];

const performanceOptions = [
  "전체",
  "~30만원",
  "~50만원",
  "50만원~",
];

export function CardList() {
  /* ==================================================
     1. STATE
  ================================================== */

  const [cards, setCards] = useState<CardListItem[]>([]);

  const [displayCards, setDisplayCards] = useState<CardListItem[]>([]);

  const [loading, setLoading] = useState(false);

  const [keyword, setKeyword] = useState("");

  const [filters, setFilters] = useState<FilterState>({
    cardType: "전체",
    company: "전체",
    annualFee: "전체",
    minPerformance: "전체",
    hasEvent: false,
    hasTransport: false,
    sort: "인기순",
  });

  /* ==================================================
     2. API 함수
  ================================================== */

  const fetchAllCards = async () => {
    console.time("전체조회");

    try {
      setLoading(true);

      const data = await getCards();

      console.log("전체카드", data);

      setCards(data);
      setDisplayCards(data);
    } catch (error) {
      console.error(error);
    } finally {
      console.timeEnd("전체조회");
      setLoading(false);
    }
  };

  const searchCards = () => {
    const query = keyword.trim().toLowerCase();

    if (!query) {
      setDisplayCards(cards);
      return;
    }

    const result = cards.filter(
      (card) =>
        card.cardName?.toLowerCase().includes(query) ||
        card.company?.toLowerCase().includes(query)
    );

    setDisplayCards(result);
  };

  const fetchFilteredCards = async () => {
    try {
      setLoading(true);

      const result = await filterCards(filters);

      console.log("필터결과", result);

      setCards(result);
      setDisplayCards(result);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  /* ==================================================
     3. useEffect
  ================================================== */

  useEffect(() => {
    fetchAllCards();
  }, []);

  useEffect(() => {
    fetchFilteredCards();
  }, [filters]);

  /* ==================================================
     4. 이벤트 함수
  ================================================== */

  const changeCardType = (
    value: string
  ) => {
    setFilters((prev) => ({
      ...prev,
      cardType: value,
    }));
  };

  const changeCompany = (
    value: string
  ) => {
    setFilters((prev) => ({
      ...prev,
      company: value,
    }));
  };

  const changeAnnualFee = (
    value: string
  ) => {
    setFilters((prev) => ({
      ...prev,
      annualFee: value,
    }));
  };

  const changePerformance = (
    value: string
  ) => {
    setFilters((prev) => ({
      ...prev,
      minPerformance: value,
    }));
  };

  const changeSort = (
    value: string
  ) => {
    setFilters((prev) => ({
      ...prev,
      sort: value,
    }));
  };

  const toggleEvent = () => {
    setFilters((prev) => ({
      ...prev,
      hasEvent: !prev.hasEvent,
    }));
  };

  const toggleTransport = () => {
    setFilters((prev) => ({
      ...prev,
      hasTransport: !prev.hasTransport,
    }));
  };

  const resetFilters = () => {
    setFilters({
      cardType: "전체",
      company: "전체",
      annualFee: "전체",
      minPerformance: "전체",
      hasEvent: false,
      hasTransport: false,
      sort: "인기순",
    });
  };

  /* ==================================================
     5. RETURN
  ================================================== */

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* =========================
          헤더
      ========================= */}

      <section>
        <h1>카드 조회</h1>
        <p>원하는 카드를 찾아보세요</p>
      </section>

      {/* =========================
          검색 영역
      ========================= */}

      <section className="mb-6">

        <div className="flex gap-2">

          <input
            type="text"
            value={keyword}
            onChange={(e) => {
              const value = e.target.value;

              setKeyword(value);

              if (!value.trim()) {
                setDisplayCards(cards);
              }
            }}
            placeholder="카드명을 입력하세요"
            className="border px-4 py-2 rounded"
          />

          <button
            onClick={searchCards}
            className="border px-4 py-2 rounded"
          >
            검색
          </button>

        </div>

      </section>

      <section className="mb-6">

        <h3 className="mb-2 font-semibold">
          카드사
        </h3>

        <div className="flex gap-2">

          {companyOptions.map((company) => (
            <button
              key={company}
              onClick={() =>
                changeCompany(company)
              }
              className={`px-4 py-2 border rounded ${filters.company === company
                ? "bg-blue-500 text-white"
                : "bg-white"
                }`}
            >
              {company}
            </button>
          ))}

        </div>

      </section>

      <section className="mb-6">

        <h3 className="mb-2 font-semibold">
          정렬
        </h3>

        <div className="flex gap-2">

          {sortOptions.map((sort) => (
            <button
              key={sort}
              onClick={() =>
                changeSort(sort)
              }
              className={`px-4 py-2 border rounded ${filters.sort === sort
                ? "bg-blue-500 text-white"
                : "bg-white"
                }`}
            >
              {sort}
            </button>
          ))}

        </div>

      </section>

      <section className="mb-6">

        <h3 className="mb-2 font-semibold">
          연회비
        </h3>

        <div className="flex gap-2 flex-wrap">

          {annualFeeOptions.map((fee) => (
            <button
              key={fee}
              onClick={() =>
                changeAnnualFee(fee)
              }
              className={`px-4 py-2 border rounded ${filters.annualFee === fee
                ? "bg-blue-500 text-white"
                : "bg-white"
                }`}
            >
              {fee}
            </button>
          ))}

        </div>

      </section>

      <section className="mb-6">

        <h3 className="mb-2 font-semibold">
          전월실적
        </h3>

        <div className="flex gap-2 flex-wrap">

          {performanceOptions.map((performance) => (
            <button
              key={performance}
              onClick={() =>
                changePerformance(performance)
              }
              className={`px-4 py-2 border rounded ${filters.minPerformance === performance
                ? "bg-blue-500 text-white"
                : "bg-white"
                }`}
            >
              {performance}
            </button>
          ))}

        </div>

      </section>

      <section className="mb-6">

        <h3 className="mb-2 font-semibold">
          이벤트
        </h3>

        <button
          onClick={toggleEvent}
          className={`px-4 py-2 border rounded ${filters.hasEvent
            ? "bg-blue-500 text-white"
            : "bg-white"
            }`}
        >
          이벤트 카드 포함
        </button>

      </section>

      <section className="mb-6">

        <h3 className="mb-2 font-semibold">
          교통카드
        </h3>

        <button
          onClick={toggleTransport}
          className={`px-4 py-2 border rounded ${filters.hasTransport
            ? "bg-blue-500 text-white"
            : "bg-white"
            }`}
        >
          교통카드 기능 포함
        </button>

      </section>

      {/* =========================
          상세 필터
      ========================= */}

      <section className="mb-6">

        <div className="flex gap-2">

          {cardTypeOptions.map((type) => (
            <button
              key={type}
              onClick={() =>
                changeCardType(type)
              }
              className={`px-4 py-2 border rounded ${filters.cardType === type
                ? "bg-blue-500 text-white"
                : "bg-white"
                }`}
            >
              {type}
            </button>
          ))}

        </div>

      </section>

      {/* =========================
          결과 정보
      ========================= */}

      <section className="mb-6 flex items-center gap-4">

        <div>
          총 {displayCards.length}개
        </div>

        <button
          onClick={resetFilters}
          className="px-4 py-2 border rounded"
        >
          필터 초기화
        </button>

      </section>

      {/* =========================
          로딩
      ========================= */}

      {loading && (
        <section>
          카드 조회 중...
        </section>
      )}

      {/* =========================
          카드 목록
      ========================= */}

      {!loading && cards.length > 0 && (
        <section>
          {displayCards.map((card) => (
            <Link
              key={card.cardId}
              to={`/cards/${card.cardId}`}
            >
              {card.cardName}
            </Link>
          ))}
        </section>
      )}

      {/* =========================
          빈 결과
      ========================= */}

      {!loading && displayCards.length === 0 && (
        <section>
          검색 결과가 없습니다.
        </section>
      )}
    </div>
  );
}