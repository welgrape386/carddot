import { useState, useEffect, useRef, useCallback } from "react";
import { Link } from "react-router";
import {
  Star,
  Heart,
  GitCompare,
  X,
  Check,
  TrendingUp,
  TrendingDown,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  ArrowUp,
  ArrowUpDown,
} from "lucide-react";
import { cards } from "../data/mockData";
import { CardVisual } from "../components/CardVisual";

/* ───────── 상수 ───────── */
const NAVBAR_H = 64;

// 서비스 대상 카드사 (4개)
const AVAILABLE_ISSUERS = ["KB국민카드", "삼성카드", "신한카드", "현대카드"];

const benefitCategories = [
  // 쇼핑
  {
    key: "온라인쇼핑",
    icon: "🛒",
    group: "쇼핑",
    desc: "지마켓, 쿠팡, 11번가 등",
  },
  { key: "패션/뷰티", icon: "👗", group: "쇼핑", desc: "올리브영, 스파브랜드" },
  { key: "슈퍼마켓/생활잡화", icon: "🏬", group: "쇼핑", desc: "" },
  {
    key: "백화점/아울렛",
    icon: "🏪",
    group: "쇼핑",
    desc: "백화점, 아울렛, 면세점",
  },
  // 교통
  { key: "대중교통/택시", icon: "🚌", group: "교통", desc: "버스, 기차, 택시" },
  {
    key: "자동차/주유",
    icon: "⛽",
    group: "교통",
    desc: "자동차 정비, 하이패스",
  },
  // 라이프
  { key: "반려동물", icon: "🐾", group: "라이프", desc: "" },
  { key: "구독/스트리밍", icon: "📺", group: "라이프", desc: "" },
  {
    key: "레저/스포츠",
    icon: "⛳",
    group: "라이프",
    desc: "골프, 게임, 경기관람, 피트니스",
  },
  { key: "페이/간편결제", icon: "📲", group: "라이프", desc: "" },
  {
    key: "문화/엔터",
    icon: "🎬",
    group: "라이프",
    desc: "영화, 놀이공원, 공연",
  },
  // 생활비
  {
    key: "생활비",
    icon: "📱",
    group: "생활비",
    desc: "통신, 보험, 공과금, 금융수수료, 렌탈/자동납부",
  },
  // 음식
  { key: "편의점", icon: "🏪", group: "음식", desc: "" },
  { key: "커피/카페/베이커리", icon: "☕", group: "음식", desc: "" },
  {
    key: "배달",
    icon: "🍕",
    group: "음식",
    desc: "배민, 요기요, 쿠팡이츠, 땡겨요",
  },
  { key: "외식", icon: "🍽️", group: "음식", desc: "아웃백, 레스토랑 등" },
  // 여행
  { key: "여행/숙박", icon: "🏨", group: "여행", desc: "렌터카 포함" },
  { key: "항공", icon: "✈️", group: "여행", desc: "공항라운지, 마일리지" },
  { key: "해외", icon: "🌏", group: "여행", desc: "직구, 현지, 외화 결제" },
  // 기타
  { key: "교육/육아", icon: "📚", group: "기타", desc: "학원, 서점, 육아용품" },
  { key: "의료", icon: "🏥", group: "기타", desc: "병원, 약국" },
];

const issuers = [
  { name: "KB국민카드", short: "KB국민", color: "#F5A200" },
  { name: "삼성카드", short: "삼성", color: "#1428A0" },
  { name: "신한카드", short: "신한", color: "#c0392b" },
  { name: "현대카드", short: "현대", color: "#1E1E1E" },
];

const feeOptions = [
  { label: "전체", min: 0, max: 999999 },
  { label: "무료", min: 0, max: 0 },
  { label: "~1만원", min: 1, max: 10000 },
  { label: "~3만원", min: 1, max: 30000 },
  { label: "~10만원", min: 1, max: 100000 },
  { label: "10만원~", min: 100001, max: 999999 },
];

const spendingOptions = [
  { label: "전체", max: 9999999 },
  { label: "무실적", max: 0 },
  { label: "~30만원", max: 300000 },
  { label: "~50만원", max: 500000 },
];

const sortOptions = [
  { value: "popular", label: "인기순", icon: "none" },
  { value: "rate_desc", label: "할인율 높은순", icon: "up" },
  { value: "rate_asc", label: "할인율 낮은순", icon: "down" },
  { value: "benefit_desc", label: "혜택 높은순", icon: "up" },
  { value: "benefit_asc", label: "혜택 낮은순", icon: "down" },
];

/* ───────── 혜택 매핑 ───────── */
const categoryBenefitMap: Record<string, string[]> = {
  온라인쇼핑: ["쇼핑"],
  "패션/뷰티": ["쇼핑"],
  "슈퍼마켓/생활잡화": ["마트"],
  "백화점/아울렛": ["마트", "쇼핑"],
  "대중교통/택시": ["교통"],
  "자동차/주유": ["주유"],
  반려동물: [],
  "구독/스트리밍": [],
  "레저/스포츠": [],
  "페이/간편결제": [],
  "문화/엔터": ["영화"],
  생활비: ["통신"],
  편의점: ["편의점"],
  "커피/카페/베이커리": ["카페"],
  배달: ["배달"],
  외식: ["외식"],
  "여행/숙박": ["여행"],
  항공: ["항공"],
  해외: ["해외"],
  "교육/육아": [],
  의료: ["의료"],
};

function getCategoryBenefit(
  card: (typeof cards)[0],
  category: string,
): { rate: number; type: string } | null {
  const mapped = categoryBenefitMap[category] ?? [category];
  if (!mapped.length) return null;
  const matched = card.benefits.filter((b) =>
    mapped.some((m) => b.category.toLowerCase().includes(m.toLowerCase())),
  );
  if (!matched.length) return null;
  const best = matched.reduce((a, b) =>
    a.discountRate >= b.discountRate ? a : b,
  );
  return { rate: best.discountRate, type: best.type };
}

function matchesCategories(
  card: (typeof cards)[0],
  selected: string[],
): boolean {
  if (!selected.length) return true;
  return selected.every((cat) => getCategoryBenefit(card, cat) !== null);
}

function getMaxRate(card: (typeof cards)[0]) {
  return Math.max(...card.benefits.map((b) => b.discountRate), 0);
}

const typeLabel: Record<string, string> = {
  discount: "할인",
  cashback: "캐시백",
  point: "적립",
  special: "",
};

/* ───────── 컴포넌트 ───────── */
export function CardList() {
  /* 필터 상태 */
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [cardType, setCardType] = useState<"all" | "credit" | "debit">("all");
  const [selectedIssuers, setSelectedIssuers] = useState<string[]>([]);
  const [feeOption, setFeeOption] = useState(feeOptions[0]);
  const [spendingOption, setSpendingOption] = useState(spendingOptions[0]);
  const [sort, setSort] = useState("popular");
  // 상세 체크박스 필터
  const [specialFilters, setSpecialFilters] = useState({
    coupon: false,
    noSpending: false,
    voucher: false,
  });

  /* UI 상태 */
  const [showDetail, setShowDetail] = useState(false);
  const [filterVisible, setFilterVisible] = useState(true);
  const [showScrollTop, setShowScrollTop] = useState(false);

  const [favorites, setFavorites] = useState<number[]>([1, 3, 5]);
  const [compareList, setCompareList] = useState<number[]>([]);

  /* 필터 바 높이 */
  const filterRef = useRef<HTMLDivElement>(null);
  const [filterHeight, setFilterHeight] = useState(110);

  useEffect(() => {
    const el = filterRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setFilterHeight(el.offsetHeight));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  /* 스크롤 방향 감지 */
  useEffect(() => {
    let lastY = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      setShowScrollTop(y > 400);
      if (y < 80) setFilterVisible(true);
      else if (y > lastY + 4) setFilterVisible(false);
      else if (y < lastY - 4) setFilterVisible(true);
      lastY = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /* 토글 헬퍼 */
  const toggleCategory = (key: string) =>
    setSelectedCategories((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  const toggleIssuer = (name: string) =>
    setSelectedIssuers((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    );
  const toggleFavorite = (id: number) =>
    setFavorites((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id],
    );
  const toggleCompare = (id: number) =>
    setCompareList((prev) => {
      if (prev.includes(id)) return prev.filter((c) => c !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });

  const resetAll = useCallback(() => {
    setSelectedCategories([]);
    setCardType("all");
    setSelectedIssuers([]);
    setFeeOption(feeOptions[0]);
    setSpendingOption(spendingOptions[0]);
    setSpecialFilters({ coupon: false, noSpending: false, voucher: false });
  }, []);

  const scrollToTop = () => window.scrollTo({ top: 0, behavior: "smooth" });

  /* 필터링 + 정렬 (4개 카드사만) */
  const filteredCards = cards
    .filter((c) => AVAILABLE_ISSUERS.includes(c.issuer))
    .filter((c) => cardType === "all" || c.type === cardType)
    .filter((c) => matchesCategories(c, selectedCategories))
    .filter(
      (c) => !selectedIssuers.length || selectedIssuers.includes(c.issuer),
    )
    .filter((c) => c.annualFee >= feeOption.min && c.annualFee <= feeOption.max)
    .filter((c) =>
      spendingOption.label === "전체"
        ? true
        : spendingOption.label === "무실적"
          ? c.minSpending === 0
          : c.minSpending <= spendingOption.max,
    )
    .filter((c) => !specialFilters.noSpending || c.minSpending === 0)
    .filter(
      (c) =>
        !specialFilters.coupon ||
        c.eventBenefits.some(
          (e) =>
            e.includes("쿠폰") ||
            e.includes("할인권") ||
            e.includes("쿠폰") ||
            e.includes("캐시백"),
        ),
    )
    .sort((a, b) => {
      if (sort === "rate_desc") return getMaxRate(b) - getMaxRate(a);
      if (sort === "rate_asc") return getMaxRate(a) - getMaxRate(b);
      if (sort === "benefit_desc") return b.maxBenefit - a.maxBenefit;
      if (sort === "benefit_asc") return a.maxBenefit - b.maxBenefit;
      return a.popularity - b.popularity;
    });

  const specialFilterCount =
    Object.values(specialFilters).filter(Boolean).length;
  const hasDetailFilter =
    cardType !== "all" ||
    selectedIssuers.length > 0 ||
    feeOption.label !== "전체" ||
    spendingOption.label !== "전체" ||
    specialFilterCount > 0;
  const hasAnyFilter = selectedCategories.length > 0 || hasDetailFilter;

  /* ─── 렌더 ─── */
  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* ════════════════════════════════
           고정 필터 바 (스크롤 hide/show)
          ════════════════════════════════ */}
      <div
        ref={filterRef}
        className="fixed left-0 right-0 z-40 bg-white border-b border-gray-200 shadow-sm transition-transform duration-300"
        style={{
          top: NAVBAR_H,
          transform: filterVisible ? "translateY(0)" : "translateY(-110%)",
        }}
      >
        <div className="max-w-[1280px] mx-auto px-6">
          {/* ── Row 1: 혜택 선택 ── */}
          <div className="py-3 flex items-start gap-3">
            <div className="flex-shrink-0 pt-1.5 w-20">
              <span className="text-xs font-black text-gray-400 whitespace-nowrap">
                혜택 선택
              </span>
            </div>

            <div className="flex flex-wrap gap-1.5 flex-1">
              {/* 전체 해제 버튼 */}
              <button
                onClick={() => setSelectedCategories([])}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-black transition-all border ${
                  selectedCategories.length === 0
                    ? "bg-[#6667AA] text-white border-[#6667AA]"
                    : "text-gray-500 border-gray-200 hover:bg-gray-50"
                }`}
              >
                전체
              </button>
              {benefitCategories.map((cat) => {
                const selected = selectedCategories.includes(cat.key);
                return (
                  <button
                    key={cat.key}
                    onClick={() => toggleCategory(cat.key)}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-black transition-all border ${
                      selected
                        ? "bg-[#6667AA] text-white border-[#6667AA]"
                        : "text-gray-600 border-gray-200 hover:bg-gray-50"
                    }`}
                    title={cat.desc || undefined}
                  >
                    <span>{cat.icon}</span>
                    {cat.key}
                    {selected && <X className="w-3 h-3 ml-0.5" />}
                  </button>
                );
              })}
            </div>

            {/* 상세 필터 토글 버튼 */}
            <button
              onClick={() => setShowDetail((v) => !v)}
              className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-black border transition-all ${
                hasDetailFilter
                  ? "bg-orange-50 border-orange-300 text-orange-600"
                  : showDetail
                    ? "bg-gray-100 border-gray-300 text-gray-700"
                    : "border-gray-200 text-gray-500 hover:bg-gray-50"
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              상세 필터
              {hasDetailFilter && (
                <span className="bg-orange-500 text-white text-[9px] font-black px-1 py-0.5 rounded-full leading-none">
                  {[
                    cardType !== "all" ? 1 : 0,
                    selectedIssuers.length,
                    feeOption.label !== "전체" ? 1 : 0,
                    spendingOption.label !== "전체" ? 1 : 0,
                    specialFilterCount,
                  ].reduce((a, b) => a + b, 0)}
                </span>
              )}
              {showDetail ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
            </button>
          </div>

          {/* ── Row 2: 상세 필터 드롭다운 ── */}
          <div
            className={`overflow-hidden transition-all duration-300 ${showDetail ? "max-h-[420px] opacity-100" : "max-h-0 opacity-0"}`}
          >
            <div className="border-t border-gray-100 py-3 space-y-3">
              {/* 카드 종류 */}
              <div className="flex items-center gap-3">
                <span className="text-xs font-black text-gray-400 w-20 flex-shrink-0">
                  카드 종류
                </span>
                <div className="flex rounded-xl overflow-hidden border border-gray-200">
                  {(["all", "credit", "debit"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setCardType(t)}
                      className={`px-4 py-1.5 text-xs font-black transition-all ${
                        cardType === t
                          ? "bg-[#6667AA] text-white"
                          : "text-gray-500 hover:bg-gray-50"
                      }`}
                    >
                      {t === "all"
                        ? "전체"
                        : t === "credit"
                          ? "신용카드"
                          : "체크카드"}
                    </button>
                  ))}
                </div>
              </div>

              {/* 카드사 */}
              <div className="flex items-center gap-3">
                <span className="text-xs font-black text-gray-400 w-20 flex-shrink-0">
                  카드사
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {issuers.map((issuer) => {
                    const selected = selectedIssuers.includes(issuer.name);
                    return (
                      <button
                        key={issuer.name}
                        onClick={() => toggleIssuer(issuer.name)}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-black transition-all ${
                          selected
                            ? "border-[#6667AA] bg-[#6667AA]/8 text-[#6667AA]"
                            : "border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50"
                        }`}
                      >
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: issuer.color }}
                        />
                        {issuer.short}
                        {selected && <Check className="w-3 h-3" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 연회비 */}
              <div className="flex items-center gap-3">
                <span className="text-xs font-black text-gray-400 w-20 flex-shrink-0">
                  연회비
                </span>
                <div className="flex gap-1 flex-wrap">
                  {feeOptions.map((opt) => (
                    <button
                      key={opt.label}
                      onClick={() => setFeeOption(opt)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-black transition-all ${feeOption.label === opt.label ? "bg-[#6667AA] text-white" : "text-gray-500 hover:bg-gray-100 border border-gray-200"}`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 전월실적 */}
              <div className="flex items-center gap-3">
                <span className="text-xs font-black text-gray-400 w-20 flex-shrink-0">
                  전월실적
                </span>
                <div className="flex gap-1">
                  {spendingOptions.map((opt) => (
                    <button
                      key={opt.label}
                      onClick={() => setSpendingOption(opt)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-black transition-all ${spendingOption.label === opt.label ? "bg-[#6667AA] text-white" : "text-gray-500 hover:bg-gray-100 border border-gray-200"}`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 특별 체크박스 필터 */}
              <div className="flex items-center gap-3">
                <span className="text-xs font-black text-gray-400 w-20 flex-shrink-0">
                  추가 조건
                </span>
                <div className="flex flex-wrap gap-3">
                  {[
                    {
                      key: "coupon" as const,
                      label: "쿠폰 제공",
                      desc: "호텔 숙박권 등",
                    },
                    {
                      key: "noSpending" as const,
                      label: "무실적",
                      desc: "할인, 적립",
                    },
                    { key: "voucher" as const, label: "바우처", desc: "" },
                  ].map((item) => (
                    <button
                      key={item.key}
                      onClick={() =>
                        setSpecialFilters((prev) => ({
                          ...prev,
                          [item.key]: !prev[item.key],
                        }))
                      }
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-black transition-all ${
                        specialFilters[item.key]
                          ? "bg-[#6667AA]/8 border-[#6667AA] text-[#6667AA]"
                          : "border-gray-200 text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      <div
                        className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition-all ${
                          specialFilters[item.key]
                            ? "bg-[#6667AA] border-[#6667AA]"
                            : "border-gray-300"
                        }`}
                      >
                        {specialFilters[item.key] && (
                          <Check className="w-2.5 h-2.5 text-white" />
                        )}
                      </div>
                      {item.label}
                      {item.desc && (
                        <span className="text-gray-400 font-bold">
                          ({item.desc})
                        </span>
                      )}
                    </button>
                  ))}
                </div>
                {hasDetailFilter && (
                  <button
                    onClick={() => {
                      setCardType("all");
                      setSelectedIssuers([]);
                      setFeeOption(feeOptions[0]);
                      setSpendingOption(spendingOptions[0]);
                      setSpecialFilters({
                        coupon: false,
                        noSpending: false,
                        voucher: false,
                      });
                    }}
                    className="ml-auto flex items-center gap-1 text-xs text-red-400 hover:text-red-600 font-black transition-colors"
                  >
                    <X className="w-3 h-3" /> 상세 필터 초기화
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* ── Row 3: 정렬 + 결과 수 (상세 필터와 동일한 좌우 정렬) ── */}
          <div className="border-t border-gray-100 py-2.5 flex items-center gap-3">
            <div className="w-20 flex-shrink-0 flex items-center gap-1.5 text-xs font-black text-gray-400">
              <ArrowUpDown className="w-3.5 h-3.5" /> 정렬
            </div>
            <div className="flex items-center gap-1.5 flex-1 flex-wrap">
              {sortOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setSort(opt.value)}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-black transition-all ${
                    sort === opt.value
                      ? "bg-[#6667AA] text-white"
                      : "text-gray-500 hover:bg-gray-100 bg-white border border-gray-200"
                  }`}
                >
                  {opt.icon === "up" && <TrendingUp className="w-3 h-3" />}
                  {opt.icon === "down" && <TrendingDown className="w-3 h-3" />}
                  {opt.icon === "none" && (
                    <SlidersHorizontal className="w-3 h-3" />
                  )}
                  {opt.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              {hasAnyFilter && (
                <button
                  onClick={resetAll}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-500 font-black transition-colors"
                >
                  <X className="w-3 h-3" /> 전체 초기화
                </button>
              )}
              <span className="text-xs text-gray-500 font-bold">
                총{" "}
                <span className="text-[#6667AA] font-black">
                  {filteredCards.length}
                </span>
                개
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 필터 바 높이만큼 상단 여백 */}
      <div style={{ paddingTop: filterHeight + NAVBAR_H }} />

      {/* ════════════════════════════════
           활성 필터 태그 + 카드 그리드
          ════════════════════════════════ */}
      <div className="max-w-[1280px] mx-auto px-6 py-6">
        {/* 활성 혜택 태그 */}
        {hasAnyFilter && (
          <div className="flex flex-wrap items-center gap-2 mb-5">
            <span className="text-xs font-black text-gray-400">적용 필터:</span>
            {selectedCategories.map((cat) => (
              <span
                key={cat}
                className="flex items-center gap-1 px-2.5 py-1 bg-[#6667AA] text-white rounded-full text-xs font-black"
              >
                {benefitCategories.find((c) => c.key === cat)?.icon} {cat}
                <button
                  onClick={() => toggleCategory(cat)}
                  className="ml-0.5 opacity-70 hover:opacity-100"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {cardType !== "all" && (
              <span className="flex items-center gap-1 px-2.5 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-black">
                {cardType === "credit" ? "신용카드" : "체크카드"}
                <button onClick={() => setCardType("all")}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {selectedIssuers.map((is) => (
              <span
                key={is}
                className="flex items-center gap-1 px-2.5 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-black"
              >
                {is}
                <button onClick={() => toggleIssuer(is)}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {feeOption.label !== "전체" && (
              <span className="flex items-center gap-1 px-2.5 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-black">
                연회비 {feeOption.label}
                <button onClick={() => setFeeOption(feeOptions[0])}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {spendingOption.label !== "전체" && (
              <span className="flex items-center gap-1 px-2.5 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-black">
                전월실적 {spendingOption.label}
                <button onClick={() => setSpendingOption(spendingOptions[0])}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {specialFilters.noSpending && (
              <span className="flex items-center gap-1 px-2.5 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-black">
                무실적
                <button
                  onClick={() =>
                    setSpecialFilters((p) => ({ ...p, noSpending: false }))
                  }
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {specialFilters.coupon && (
              <span className="flex items-center gap-1 px-2.5 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-black">
                쿠폰 제공
                <button
                  onClick={() =>
                    setSpecialFilters((p) => ({ ...p, coupon: false }))
                  }
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {specialFilters.voucher && (
              <span className="flex items-center gap-1 px-2.5 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-black">
                바우처
                <button
                  onClick={() =>
                    setSpecialFilters((p) => ({ ...p, voucher: false }))
                  }
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
          </div>
        )}

        {/* 카드 그리드 */}
        {filteredCards.length > 0 ? (
          <div className="grid grid-cols-4 gap-4">
            {filteredCards.map((card) => {
              const selectedBenefits = selectedCategories
                .map((cat) => {
                  const b = getCategoryBenefit(card, cat);
                  return b ? { cat, rate: b.rate, type: b.type } : null;
                })
                .filter(Boolean) as {
                cat: string;
                rate: number;
                type: string;
              }[];

              const missingCats = selectedCategories.filter(
                (cat) => !selectedBenefits.find((b) => b.cat === cat),
              );

              return (
                <div
                  key={card.id}
                  className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md hover:border-[#6667AA]/20 transition-all group flex flex-col"
                >
                  {/* 카드 이미지 영역 */}
                  <div className="bg-gray-50/70 p-5 flex items-start justify-between">
                    <div className="flex flex-col items-center gap-2">
                      <CardVisual card={card} size="md" />
                      <div className="flex gap-1 flex-wrap justify-center">
                        <span
                          className={`text-[9px] font-black px-1.5 py-0.5 rounded ${card.type === "credit" ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600"}`}
                        >
                          {card.type === "credit" ? "신용" : "체크"}
                        </span>
                        {card.tags.slice(0, 1).map((tag) => (
                          <span
                            key={tag}
                            className="text-[9px] font-black bg-[#6667AA]/8 text-[#6667AA] px-1.5 py-0.5 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <button
                        onClick={() => toggleFavorite(card.id)}
                        className={`p-1.5 rounded-lg transition-all ${favorites.includes(card.id) ? "text-red-500 bg-red-50" : "text-gray-300 hover:text-gray-500"}`}
                      >
                        <Heart
                          className={`w-4 h-4 ${favorites.includes(card.id) ? "fill-red-500" : ""}`}
                        />
                      </button>
                      <button
                        onClick={() => toggleCompare(card.id)}
                        className={`p-1.5 rounded-lg transition-all ${compareList.includes(card.id) ? "text-[#6667AA] bg-indigo-50" : "text-gray-300 hover:text-gray-500"}`}
                      >
                        <GitCompare className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* 카드 정보 */}
                  <div className="p-4 flex flex-col flex-1">
                    <div className="text-[10px] text-gray-400 font-black mb-0.5">
                      {card.issuer}
                    </div>
                    <h3 className="text-sm font-black text-gray-900 mb-3 group-hover:text-[#6667AA] transition-colors leading-snug">
                      {card.name}
                    </h3>

                    {/* ★ 선택 혜택 할인율 뱃지 */}
                    {selectedCategories.length > 0 && (
                      <div className="mb-3 rounded-xl border overflow-hidden">
                        {selectedBenefits.length > 0 && (
                          <div className="bg-[#6667AA]/4 border-b border-[#6667AA]/8 px-3 pt-2.5 pb-2">
                            <div className="text-[9px] text-[#6667AA] font-black mb-1.5 uppercase tracking-wide">
                              선택 혜택 할인율
                            </div>
                            <div className="space-y-1.5">
                              {selectedBenefits.map(({ cat, rate, type }) => {
                                const catInfo = benefitCategories.find(
                                  (c) => c.key === cat,
                                );
                                return (
                                  <div
                                    key={cat}
                                    className="flex items-center justify-between"
                                  >
                                    <div className="flex items-center gap-1 text-xs text-gray-600 font-bold">
                                      <span className="text-sm leading-none">
                                        {catInfo?.icon}
                                      </span>
                                      <span>{cat}</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                      <span className="text-base font-black text-[#6667AA] leading-none">
                                        {rate}%
                                      </span>
                                      <span
                                        className={`text-[9px] font-black px-1 py-0.5 rounded leading-none ${
                                          type === "cashback"
                                            ? "bg-green-50 text-green-600"
                                            : type === "point"
                                              ? "bg-purple-50 text-purple-600"
                                              : "bg-blue-50 text-blue-600"
                                        }`}
                                      >
                                        {typeLabel[type]}
                                      </span>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                        {missingCats.length > 0 && (
                          <div className="bg-gray-50 px-3 pt-2 pb-2">
                            {missingCats.map((cat) => {
                              const catInfo = benefitCategories.find(
                                (c) => c.key === cat,
                              );
                              return (
                                <div
                                  key={cat}
                                  className="flex items-center justify-between py-0.5"
                                >
                                  <div className="flex items-center gap-1 text-xs text-gray-400 font-bold">
                                    <span className="text-sm leading-none opacity-50">
                                      {catInfo?.icon}
                                    </span>
                                    <span>{cat}</span>
                                  </div>
                                  <span className="text-[10px] text-gray-300 font-black">
                                    혜택 없음
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}

                    {/* 기본 정보 */}
                    <div className="space-y-1.5 mb-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400 font-bold">연회비</span>
                        <span
                          className={`font-black ${card.annualFee === 0 ? "text-green-600" : "text-gray-900"}`}
                        >
                          {card.annualFee === 0
                            ? "무료"
                            : `${card.annualFee.toLocaleString()}원`}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400 font-bold">
                          전월실적
                        </span>
                        <span className="font-black text-gray-900">
                          {card.minSpending === 0
                            ? "무실적"
                            : `${(card.minSpending / 10000).toFixed(0)}만원`}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400 font-bold">
                          월 최대 혜택
                        </span>
                        <span className="font-black text-[#6667AA]">
                          {(card.maxBenefit / 10000).toFixed(0)}만원
                        </span>
                      </div>
                    </div>

                    {/* 대표 혜택 (카테고리 미선택 시) */}
                    {selectedCategories.length === 0 && (
                      <div className="mb-3 pb-3 border-b border-gray-50">
                        <div className="text-[10px] text-gray-400 font-black mb-1.5">
                          대표 혜택
                        </div>
                        <div className="space-y-1">
                          {card.benefits.slice(0, 2).map((b, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-1.5 text-xs text-gray-600 font-bold"
                            >
                              <span>{b.icon}</span>
                              <span className="flex-1">{b.category}</span>
                              <span className="font-black text-[#6667AA]">
                                {b.discountRate}%
                              </span>
                              <span className="text-gray-400 text-[10px]">
                                {b.type === "cashback"
                                  ? "캐시백"
                                  : b.type === "point"
                                    ? "적립"
                                    : "할인"}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 이벤트 혜택 */}
                    {card.eventBenefits.length > 0 && (
                      <div className="mb-3">
                        <div className="bg-amber-50 border border-amber-100 rounded-lg px-2.5 py-1.5 flex items-start gap-1.5">
                          <span className="text-[10px] font-black text-amber-600 mt-0.5">
                            🎉
                          </span>
                          <span className="text-[10px] text-amber-700 font-bold leading-snug">
                            {card.eventBenefits[0]}
                          </span>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between mt-auto pt-3 border-t border-gray-50">
                      <div className="flex items-center gap-1">
                        <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                        <span className="text-xs font-black text-gray-700">
                          {card.rating}
                        </span>
                        <span className="text-[10px] text-gray-400 font-bold">
                          ({card.reviews.toLocaleString()})
                        </span>
                      </div>
                      <Link
                        to={`/cards/${card.id}`}
                        className="text-xs px-3 py-1.5 text-white rounded-lg hover:opacity-90 transition-all font-black"
                        style={{ backgroundColor: "#6667AA" }}
                      >
                        상세보기
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-24">
            <div className="text-5xl mb-4">🔍</div>
            <p className="text-gray-600 font-black mb-1">
              조건에 맞는 카드가 없어요
            </p>
            <p className="text-gray-400 text-sm font-bold mb-5">
              혜택 선택이나 상세 필터를 조정해보세요
            </p>
            <button
              onClick={resetAll}
              className="px-5 py-2.5 text-white rounded-xl text-sm font-black hover:opacity-90 transition-all"
              style={{ backgroundColor: "#6667AA" }}
            >
              필터 전체 초기화
            </button>
          </div>
        )}
      </div>

      {/* ── 비교 플로팅 바 ── */}
      {compareList.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
          <div
            className="rounded-2xl shadow-xl px-6 py-3.5 flex items-center gap-4"
            style={{ backgroundColor: "#6667AA" }}
          >
            <div className="flex items-center gap-2">
              <GitCompare className="w-4 h-4 text-white" />
              <span className="text-white text-sm font-black">비교 중</span>
              <span className="bg-white/20 text-white text-xs px-2 py-0.5 rounded-full font-black">
                {compareList.length}/3
              </span>
            </div>
            <div className="flex gap-2">
              {compareList.map((id) => {
                const card = cards.find((c) => c.id === id);
                return card ? (
                  <div
                    key={id}
                    className="flex items-center gap-1 bg-white/10 text-white text-xs px-2 py-1 rounded-lg font-bold"
                  >
                    {card.name.split(" ").slice(-1)[0]}
                    <button
                      onClick={() => toggleCompare(id)}
                      className="ml-1 text-white/60 hover:text-white"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ) : null;
              })}
            </div>
            <Link
              to={`/compare?cards=${compareList.join(",")}`}
              className="px-4 py-2 bg-[#0ABFA3] text-white rounded-xl text-sm font-black hover:bg-[#099d86] transition-all"
            >
              비교하기
            </Link>
          </div>
        </div>
      )}

      {/* ── 맨 위로 버튼 ── */}
      <button
        onClick={scrollToTop}
        className={`fixed right-6 z-50 w-11 h-11 text-white rounded-2xl shadow-lg flex items-center justify-center hover:opacity-90 transition-all duration-300 ${
          showScrollTop
            ? "opacity-100 translate-y-0"
            : "opacity-0 translate-y-4 pointer-events-none"
        }`}
        style={{
          bottom: compareList.length > 0 ? "88px" : "24px",
          backgroundColor: "#6667AA",
        }}
        aria-label="맨 위로"
      >
        <ArrowUp className="w-5 h-5" />
      </button>
    </div>
  );
}
