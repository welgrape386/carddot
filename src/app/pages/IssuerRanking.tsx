import { useState, useMemo, useEffect } from "react";
import { Link, useSearchParams } from "react-router";
import { Star, Crown, ChevronRight, CreditCard, TrendingUp, Eye, MousePointerClick } from "lucide-react";
import { cards, issuerMeta } from "../data/mockData";
import { CardVisual } from "../components/CardVisual";

// 서비스 대상 카드사 고정
const AVAILABLE_ISSUERS = ["삼성카드", "신한카드", "현대카드", "KB국민카드"];
const issuers = AVAILABLE_ISSUERS;

export function IssuerRanking() {
  const [searchParams] = useSearchParams();
  const initialIssuer = decodeURIComponent(searchParams.get("issuer") || "");

  const [cardType, setCardType] = useState<"all" | "credit" | "debit">("all");
  const [selectedIssuer, setSelectedIssuer] = useState<string>(
    issuers.includes(initialIssuer) ? initialIssuer : "전체",
  );

  // URL param으로 진입 시 issuer 자동 선택
  useEffect(() => {
    if (issuers.includes(initialIssuer)) {
      setSelectedIssuer(initialIssuer);
    }
  }, [initialIssuer]);

  const rankedCards = useMemo(() => {
    return cards
      .filter((c) => AVAILABLE_ISSUERS.includes(c.issuer))
      .filter((c) => cardType === "all" || c.type === cardType)
      .filter((c) => selectedIssuer === "전체" || c.issuer === selectedIssuer)
      .sort((a, b) => (b.views + b.clicks) - (a.views + a.clicks));
  }, [cardType, selectedIssuer]);

  const medalColors = ["text-yellow-500", "text-gray-400", "text-amber-600"];
  const medalBg = [
    "bg-yellow-50 border-yellow-200",
    "bg-gray-50 border-gray-200",
    "bg-amber-50 border-amber-200",
  ];
  const medals = ["👑", "🥈", "🥉"];

  const totalScore = (c: (typeof cards)[0]) => c.views + c.clicks;

  const typeTabLabel = {
    all: "전체",
    credit: "신용카드",
    debit: "체크카드",
  } as const;

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1280px] mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-2">
            <Crown className="w-6 h-6 text-yellow-500" />
            <h1 className="text-2xl font-normal text-gray-900">카드 랭킹</h1>
          </div>
          <div className="flex items-center gap-2 ml-9">
            <Eye className="w-3.5 h-3.5 text-gray-400" />
            <p className="text-gray-500 text-sm font-normal">
              2026년 4월 기준 조회수 + 카드사 바로가기 클릭 수 총합 집계
            </p>
          </div>
        </div>
      </div>

      {/* 필터 바 */}
      <div className="bg-white border-b border-gray-100 sticky top-16 z-30 shadow-sm">
        <div className="max-w-[1280px] mx-auto px-6 py-3 space-y-3">
          {/* 카드 종류 탭 */}
          <div className="flex items-center gap-3">
            <div className="flex rounded-xl overflow-hidden border border-gray-200">
              {(["all", "credit", "debit"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setCardType(t)}
                  className={`px-4 py-1.5 text-sm font-normal transition-all ${
                    cardType === t
                      ? "bg-[#6667AA] text-white"
                      : "text-gray-500 hover:bg-gray-50"
                  }`}
                >
                  {typeTabLabel[t]}{" "}
                  {cardType === t && (
                    <span className="text-xs opacity-80">Top</span>
                  )}
                </button>
              ))}
            </div>
            <span className="text-xs text-gray-400 font-normal">
              {selectedIssuer === "전체"
                ? `전체 ${rankedCards.length}개 카드`
                : `${selectedIssuer} ${rankedCards.length}개`}
            </span>
          </div>

          {/* 카드사 필터 */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              onClick={() => setSelectedIssuer("전체")}
              className={`px-3 py-1.5 rounded-lg text-sm font-normal transition-all ${
                selectedIssuer === "전체"
                  ? "bg-[#6667AA] text-white"
                  : "text-gray-600 hover:bg-gray-100 border border-gray-200"
              }`}
            >
              전체
            </button>
            {issuers.map((issuer) => {
              const meta = issuerMeta[issuer];
              return (
                <button
                  key={issuer}
                  onClick={() => setSelectedIssuer(issuer)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-normal transition-all flex items-center gap-1.5 border ${
                    selectedIssuer === issuer
                      ? "text-white border-transparent"
                      : "text-gray-600 hover:bg-gray-100 border-gray-200"
                  }`}
                  style={
                    selectedIssuer === issuer
                      ? { backgroundColor: meta.color }
                      : {}
                  }
                >
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: meta.color }}
                  />
                  {issuer.replace("카드", "").replace("NH농협", "NH농협")}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 랭킹 목록 */}
      <div className="max-w-[1280px] mx-auto px-6 py-8">
        {rankedCards.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-2xl border border-gray-100">
            <CreditCard className="w-12 h-12 text-gray-200 mx-auto mb-3" />
            <p className="text-gray-400 font-normal">해당 조건의 카드가 없습니다</p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            {/* 상단 안내 */}
            <div className="px-6 py-3.5 bg-[#6667AA]/5 border-b border-gray-100 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-[#6667AA]" />
              <span className="text-xs font-normal text-[#6667AA]">
                {cardType === "all"
                  ? "전체 카드 랭킹"
                  : cardType === "credit"
                    ? "신용카드 랭킹"
                    : "체크카드 랭킹"}
                {selectedIssuer !== "전체" ? ` · ${selectedIssuer}` : ""}
                {" "}· 조회수+클릭수 기준
              </span>
              <span className="ml-auto text-xs text-gray-400 font-normal">
                2026년 4월 기준
              </span>
            </div>

            <div className="divide-y divide-gray-50">
              {rankedCards.map((card, idx) => {
                const meta = issuerMeta[card.issuer];
                const score = totalScore(card);
                const topScore = totalScore(rankedCards[0]);
                const barWidth = Math.round((score / topScore) * 100);

                return (
                  <Link key={card.id} to={`/cards/${card.id}`}>
                    <div className="px-6 py-5 flex items-center gap-5 hover:bg-gray-50/70 transition-all group">
                      {/* 순위 */}
                      <div
                        className={`flex-shrink-0 w-10 h-10 rounded-xl border-2 flex items-center justify-center ${
                          idx < 3 ? medalBg[idx] : "bg-white border-gray-200"
                        }`}
                      >
                        {idx < 3 ? (
                          <span className="text-lg">{medals[idx]}</span>
                        ) : (
                          <span className="text-sm font-normal text-gray-500">
                            {idx + 1}
                          </span>
                        )}
                      </div>

                      {/* 카드 이미지 */}
                      <div className="flex-shrink-0">
                        <CardVisual card={card} size="sm" />
                      </div>

                      {/* 카드 정보 */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {/* 카드사 로고 */}
                          <span
                            className="text-[9px] font-normal px-1.5 py-0.5 rounded text-white"
                            style={{ backgroundColor: meta?.color }}
                          >
                            {meta?.logo}
                          </span>
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
                              #{tag}
                            </span>
                          ))}
                        </div>

                        <div className="text-sm font-normal text-gray-900 group-hover:text-[#6667AA] transition-colors mb-1.5">
                          {card.name}
                        </div>

                        <div className="flex items-center gap-4 text-xs text-gray-500 font-normal">
                          <span>
                            연회비{" "}
                            <span
                              className={
                                card.annualFee === 0
                                  ? "text-green-600"
                                  : "text-gray-700"
                              }
                            >
                              {card.annualFee === 0
                                ? "무료"
                                : `${card.annualFee.toLocaleString()}원`}
                            </span>
                          </span>
                          <span>
                            전월실적{" "}
                            <span className="text-gray-700">
                              {card.minSpending === 0
                                ? "무실적"
                                : `${(card.minSpending / 10000).toFixed(0)}만원`}
                            </span>
                          </span>
                          <span>
                            월최대{" "}
                            <span className="text-[#6667AA]">
                              {(card.maxBenefit / 10000).toFixed(0)}만원 혜택
                            </span>
                          </span>
                        </div>

                        {/* 조회 지표 바 */}
                        <div className="mt-2 flex items-center gap-2">
                          <div className="flex-1 max-w-[160px] bg-gray-100 rounded-full h-1.5">
                            <div
                              className="h-1.5 rounded-full transition-all"
                              style={{
                                width: `${barWidth}%`,
                                backgroundColor: meta?.color ?? "#6667AA",
                              }}
                            />
                          </div>
                          <div className="flex items-center gap-1 text-[10px] text-gray-400 font-normal">
                            <Eye className="w-3 h-3" />
                            {(card.views / 10000).toFixed(0)}만
                            <MousePointerClick className="w-3 h-3 ml-1" />
                            {(card.clicks / 10000).toFixed(1)}만
                          </div>
                        </div>
                      </div>

                      {/* 대표 혜택 */}
                      <div className="hidden xl:flex flex-col gap-1 w-52">
                        {card.benefits.slice(0, 2).map((b, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-1.5 text-xs text-gray-600 font-normal"
                          >
                            <span>{b.icon}</span>
                            <span>
                              {b.category}{" "}
                              <span className="text-[#6667AA]">
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

                      {/* 평점 */}
                      <div className="flex-shrink-0 flex items-center gap-3">
                        <div className="text-right">
                          <div className="flex items-center gap-1 justify-end mb-0.5">
                            <Star className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
                            <span className="text-sm font-normal text-gray-800">
                              {card.rating}
                            </span>
                          </div>
                          <div className="text-[10px] text-gray-400 font-normal">
                            {card.reviews.toLocaleString()}개 리뷰
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-[#6667AA] transition-colors" />
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        )}

        {/* 하단 안내 */}
        <div className="mt-8 flex items-center gap-2 text-xs text-gray-400 font-normal justify-center">
          <CreditCard className="w-3.5 h-3.5" />
          랭킹은 2026년 4월 기준 조회수 + 카드사 바로가기 클릭 수 총합으로 집계되며, 매월 1일 갱신됩니다.
        </div>
      </div>
    </div>
  );
}