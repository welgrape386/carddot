import { useState, useEffect, useRef } from "react";
import { motion } from "motion/react";
import { Link } from "react-router";
import { ArrowRight, ChevronRight, CreditCard, Zap, Crown } from "lucide-react";
import { cards, issuerMeta } from "../data/mockData";
import { CardVisual } from "../components/CardVisual";

const HOME_ISSUERS = ["삼성카드", "신한카드", "현대카드", "KB국민카드"];

// 카드 조회 페이지 혜택 키와 동일하게 맞춘 12개
const quickCategories = [
  { key: "온라인쇼핑", icon: "🛒" },
  { key: "패션/뷰티", icon: "👗" },
  { key: "대중교통/택시", icon: "🚌" },
  { key: "자동차/주유", icon: "⛽" },
  { key: "구독/스트리밍", icon: "📺" },
  { key: "페이/간편결제", icon: "📲" },
  { key: "편의점", icon: "🏪" },
  { key: "커피/카페/베이커리", icon: "☕" },
  { key: "배달", icon: "🍕" },
  { key: "외식", icon: "🍽️" },
  { key: "여행/숙박", icon: "🏨" },
  { key: "해외", icon: "🌏" },
];

const medalEmoji = ["👑", "🥈", "🥉", "4", "5"];
const medalBg = [
  "border-yellow-300 bg-yellow-50",
  "border-gray-300 bg-gray-50",
  "border-amber-300 bg-amber-50",
  "border-gray-200 bg-white",
  "border-gray-200 bg-white",
];

function hexToSoftTint(hex: string, mix = 0.88) {
  const cleaned = hex.replace("#", "");

  const normalized =
    cleaned.length === 3
      ? cleaned
          .split("")
          .map((char) => char + char)
          .join("")
      : cleaned;

  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);

  const mixedR = Math.round(r + (255 - r) * mix);
  const mixedG = Math.round(g + (255 - g) * mix);
  const mixedB = Math.round(b + (255 - b) * mix);

  return `rgb(${mixedR}, ${mixedG}, ${mixedB})`;
}

export function Home() {
  const [activeIssuer, setActiveIssuer] = useState(HOME_ISSUERS[0]);
  const [isSpread, setIsSpread] = useState(false);
  const heroCardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = heroCardRef.current;
    if (!el) return;

    let timer: ReturnType<typeof setTimeout>;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          timer = setTimeout(() => setIsSpread(true), 350);
        } else {
          clearTimeout(timer);
          setIsSpread(false);
        }
      },
      { threshold: 0.4 },
    );

    observer.observe(el);

    return () => {
      observer.disconnect();
      clearTimeout(timer);
    };
  }, []);

  const rankedCards = cards
    .filter((c) => c.issuer === activeIssuer)
    .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99))
    .slice(0, 5);

  const meta = issuerMeta[activeIssuer];

  // 기존보다 살짝 더 진하게 보이도록 0.88 -> 0.84
  // 특히 국민카드 노란색이 너무 흐리지 않게 조정
  const issuerTintBg = hexToSoftTint(meta.color, 0.84);
  const issuerBorder = hexToSoftTint(meta.color, 0.7);

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* Hero */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-[1280px] mx-auto px-6 py-20 flex items-center gap-16">
          <div className="flex-1 max-w-xl">
            <div className="inline-flex items-center gap-2 bg-[#1B3D7B]/8 text-[#1B3D7B] px-3 py-1.5 rounded-full text-sm font-normal mb-6">
              <Zap className="w-3.5 h-3.5" />
              2025년 3월 최신 카드 정보 업데이트
            </div>

            <h1 className="text-4xl text-gray-900 mb-5 leading-tight font-normal">
              내 소비패턴에 딱 맞는
              <br />
              <span className="text-[#6667AA]">카드를 찾아드려요</span>
            </h1>

            <p className="text-gray-500 mb-8 leading-relaxed font-normal">
              500개 이상의 신용·체크카드를 한눈에 비교하세요.
              <br />
              혜택 활용도와 소비패턴 분석으로 최적의 카드를 추천해드립니다.
            </p>

            <div className="flex items-center gap-3">
              <Link
                to="/cards"
                className="flex items-center gap-2 px-6 py-3 bg-[#464795] text-white rounded-xl hover:bg-[#5B5C9E] transition-all shadow-sm font-normal"
              >
                카드 조회하기 <ArrowRight className="w-4 h-4" />
              </Link>

              <Link
                to="/analysis"
                className="flex items-center gap-2 px-6 py-3 border-2 border-gray-200 text-gray-700 rounded-xl hover:border-[#6667AA] hover:text-[#6667AA] transition-all font-normal"
              >
                카드 판별하기
              </Link>
            </div>
          </div>

          {/* Hero 카드 애니메이션 */}
          <div className="hidden lg:flex flex-1 justify-center items-center">
            <div ref={heroCardRef} className="relative w-96 h-72">
              {cards.slice(0, 3).map((card, i) => {
                const spreadPos = [
                  { top: 140, left: 0, rotate: 10 },
                  { top: 95, left: 65, rotate: 40 },
                  { top: 85, left: 150, rotate: 70 },
                ][i];

                const stackedPos = { top: 28, left: 28, rotate: 0 };

                return (
                  <motion.div
                    key={card.id}
                    className="absolute"
                    style={{ zIndex: 3 - i }}
                    animate={
                      isSpread
                        ? {
                            top: spreadPos.top,
                            left: spreadPos.left,
                            rotate: spreadPos.rotate,
                            opacity: 1,
                          }
                        : {
                            top: stackedPos.top,
                            left: stackedPos.left,
                            rotate: stackedPos.rotate,
                            opacity: 1,
                          }
                    }
                    initial={{
                      top: stackedPos.top,
                      left: stackedPos.left,
                      rotate: 0,
                      opacity: 0,
                    }}
                    transition={{
                      type: "spring",
                      stiffness: 95,
                      damping: 15,
                      delay: isSpread ? i * 0.1 : (2 - i) * 0.06,
                      opacity: { duration: 0.25, delay: 0.1 },
                    }}
                  >
                    <CardVisual card={card} size="lg" />
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* 혜택별 빠른 카드 탐색 */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-[1280px] mx-auto px-6 py-8">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-normal text-gray-900">
                혜택별 빠른 카드 탐색
              </h2>
              <p className="text-sm text-gray-400 font-normal mt-0.5">
                자주 찾는 혜택 12개를 선택해 바로 카드 조회로 이동할 수 있어요
              </p>
            </div>
          </div>

          <div className="grid grid-cols-12 gap-2.5">
            {quickCategories.map((cat) => (
              <Link
                key={cat.key}
                to={`/cards?benefits=${encodeURIComponent(cat.key)}`}
                className="flex flex-col items-center gap-2 py-4 rounded-2xl border border-gray-200 bg-[#6667AA]/6 hover:bg-[#6667AA]/10 hover:border-[#6667AA]/20 transition-all group"
              >
                <span className="text-2xl">{cat.icon}</span>
                <span className="text-[11px] font-normal text-gray-700 text-center leading-tight group-hover:text-gray-900 px-1">
                  {cat.key}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* 카드사별 이번 달 랭킹 */}
      <div className="bg-[#6667AA]/25">
        <section className="max-w-[1280px] mx-auto px-6 py-12">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Crown className="w-5 h-5 text-yellow-500" />
              <div>
                <h2 className="text-xl text-gray-900 font-normal">
                  카드사별 이번 달 랭킹
                </h2>
                <p className="text-gray-500 text-sm font-normal mt-0.5">
                  삼성 · 신한 · 현대 · 국민카드 기준 TOP 5
                </p>
              </div>
            </div>

            <Link
              to="/ranking"
              className="flex items-center gap-1 text-sm text-[#1B3D7B] hover:underline font-normal"
            >
              전체 보기 <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          {/* 카드사 탭 */}
          <div className="flex items-center gap-2 mb-5 flex-wrap">
            {HOME_ISSUERS.map((issuer) => (
              <button
                key={issuer}
                onClick={() => setActiveIssuer(issuer)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl border-2 text-sm font-normal transition-all ${
                  activeIssuer === issuer
                    ? "text-white border-transparent shadow-md"
                    : "border-gray-200 text-gray-600 bg-white hover:border-gray-300"
                }`}
                style={
                  activeIssuer === issuer
                    ? { backgroundColor: issuerMeta[issuer].color }
                    : {}
                }
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{
                    backgroundColor:
                      activeIssuer === issuer
                        ? "rgba(255,255,255,0.7)"
                        : issuerMeta[issuer].color,
                  }}
                />
                {issuer}
              </button>
            ))}
          </div>

          {/* 랭킹 패널 */}
          <div
            className="rounded-2xl border-2 overflow-hidden"
            style={{ borderColor: `${meta.color}30` }}
          >
            <div
              className="px-6 py-4 flex items-center justify-between"
              style={{ backgroundColor: issuerTintBg }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-xs font-normal"
                  style={{ backgroundColor: meta.color }}
                >
                  {meta.logo}
                </div>

                <div>
                  <span className="font-normal text-gray-900">
                    {activeIssuer}
                  </span>
                  <span className="text-gray-400 text-xs font-normal ml-2">
                    {meta.desc}
                  </span>
                </div>
              </div>

              <Link
                to={`/ranking?issuer=${encodeURIComponent(activeIssuer)}`}
                className="text-xs font-normal flex items-center gap-1 hover:underline"
                style={{ color: meta.color }}
              >
                전체 카드 보기 <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div
              className="bg-white divide-y divide-gray-50 border-t-2"
              style={{ borderTopColor: issuerBorder }}
            >
              {rankedCards.map((card, idx) => (
                <Link key={card.id} to={`/cards/${card.id}`}>
                  <div className="px-6 py-5 flex items-center gap-5 hover:bg-gray-50/60 transition-all group">
                    <div
                      className={`flex-shrink-0 w-10 h-10 rounded-xl border-2 flex items-center justify-center text-base ${medalBg[idx]}`}
                    >
                      {idx < 3 ? (
                        <span>{medalEmoji[idx]}</span>
                      ) : (
                        <span className="font-normal text-gray-600">
                          {medalEmoji[idx]}
                        </span>
                      )}
                    </div>

                    <div className="flex-shrink-0">
                      <CardVisual card={card} size="sm" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`text-[10px] font-normal px-1.5 py-0.5 rounded ${
                            card.type === "credit"
                              ? "bg-blue-50 text-blue-600"
                              : "bg-purple-50 text-purple-600"
                          }`}
                        >
                          {card.type === "credit" ? "신용" : "체크"}
                        </span>

                        {card.tags.slice(0, 2).map((tag) => (
                          <span
                            key={tag}
                            className="text-[10px] font-normal bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>

                      <div className="text-sm font-normal text-gray-900 group-hover:text-[#1B3D7B] transition-colors mb-1.5">
                        {card.name}
                      </div>

                      <div className="flex items-center gap-4 text-xs text-gray-500 font-normal">
                        <span>
                          연회비{" "}
                          <span
                            className={
                              card.annualFee === 0
                                ? "text-green-600 font-normal"
                                : "text-gray-800 font-normal"
                            }
                          >
                            {card.annualFee === 0
                              ? "무료"
                              : `${card.annualFee.toLocaleString()}원`}
                          </span>
                        </span>

                        <span>
                          전월실적{" "}
                          <span className="text-gray-800 font-normal">
                            {card.minSpending === 0
                              ? "무실적"
                              : `${(card.minSpending / 10000).toFixed(0)}만원`}
                          </span>
                        </span>

                        <span>
                          월최대{" "}
                          <span className="text-[#1B3D7B] font-normal">
                            {(card.maxBenefit / 10000).toFixed(0)}만원 혜택
                          </span>
                        </span>
                      </div>
                    </div>

                    <div className="hidden lg:flex flex-col gap-1.5 w-52">
                      {card.benefits.slice(0, 2).map((b, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-1.5 text-xs text-gray-600 font-normal"
                        >
                          <span>{b.icon}</span>
                          <span>
                            {b.category}{" "}
                            <span className="text-[#1B3D7B] font-normal">
                              {b.discountRate}%
                            </span>{" "}
                            {b.type === "cashback"
                              ? "캐시백"
                              : b.type === "point"
                                ? "적립"
                                : "할인"}
                          </span>
                        </div>
                      ))}
                    </div>

                    <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-[#1B3D7B] transition-colors flex-shrink-0" />
                  </div>
                </Link>
              ))}
            </div>

            <div
              className="px-6 py-3 flex justify-center border-t-2"
              style={{
                backgroundColor: issuerTintBg,
                borderTopColor: issuerBorder,
              }}
            >
              <Link
                to={`/ranking?issuer=${encodeURIComponent(activeIssuer)}`}
                className="flex items-center gap-1.5 text-sm font-normal hover:underline"
                style={{ color: meta.color }}
              >
                {activeIssuer} 랭킹 전체 보기 <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="border-t border-[#6667AA]/30 bg-[#FEFEFE]/25">
        <div className="max-w-[1280px] mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className="w-6 h-6 rounded flex items-center justify-center"
                style={{ backgroundColor: "#6667AA" }}
              >
                <CreditCard className="w-3 h-3 text-white" />
              </div>
              <span className="font-normal" style={{ color: "#6667AA" }}>
                카드닷
              </span>
            </div>

            <p className="text-gray-400 text-xs font-normal">
              © 2025 카드닷. 본 서비스는 금융상품 비교 정보 제공 목적으로
              운영됩니다.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
