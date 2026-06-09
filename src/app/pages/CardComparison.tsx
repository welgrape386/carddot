import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  X,
  GitCompare,
  ChevronRight,
  Search,
  TrendingUp,
  Trophy,
  Zap,
  BarChart3,
  ArrowUp,
  ArrowDown,
  Minus,
} from "lucide-react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";
import { compareCards, searchCompareCards } from "../../api/card";
import type { CompareCardItem, CompareSearchCardItem } from "../../types/card";
import { useAuth } from "../context/AuthContext";

const MAX_COMPARE = 3;
const CHART_COLORS = ["#6667AA", "#F59E0B", "#10B981"];


const PERSONA_DETAILS = {
  STUDENT: {
    description: "교육비 및 대중교통 이용 빈도가 가장 높은 그룹",
    weights: { "교육/육아": 40, "대중교통/택시": 30, "카페/베이커리": 20, "편의점": 10 },
  },
  SINGLE: {
    description: "배달·편의점·온라인쇼핑 중심 소비 그룹",
    weights: { "배달": 35, "편의점": 25, "온라인쇼핑": 20, "외식": 20 },
  },
  WORKER: {
    description: "출퇴근과 온라인 소비 비중이 높은 직장인 그룹",
    weights: { "대중교통/택시": 25, "자동차/주유": 25, "생활비": 20, "온라인쇼핑": 15 },
  },
  FAMILY: {
    description: "교육·장보기·의료 소비가 많은 가족 그룹",
    weights: { "교육/육아": 35, "슈퍼마켓/생활잡화": 25, "생활비": 20, "의료": 20 },
  },
  SENIOR: {
    description: "의료·생활비 중심의 안정형 소비 그룹",
    weights: { "의료": 40, "생활비": 30, "슈퍼마켓/생활잡화": 30 },
  },
};


type PersonaType =
  | "STUDENT"
  | "SINGLE"
  | "WORKER"
  | "FAMILY"
  | "SENIOR";

const PERSONAS: {
  id: PersonaType;
  emoji: string;
  name: string;
  tags: string;
}[] = [
  { id: "STUDENT", emoji: "🎓", name: "실속파 대학생", tags: "#20대 #공부 #알바 #뚜벅이" },
  { id: "SINGLE", emoji: "🍜", name: "1인 가구 자취족", tags: "#나혼자산다 #배달 #편의점 #쿠팡" },
  { id: "WORKER", emoji: "💼", name: "스마트 직장인", tags: "#3040 #출퇴근 #온라인쇼핑 #취미" },
  { id: "FAMILY", emoji: "👨‍👩‍👧", name: "아이 있는 가족", tags: "#다인가구 #학원비 #장보기 #병원" },
  { id: "SENIOR", emoji: "🌿", name: "액티브 시니어", tags: "#5060+ #건강 #안정적 #마트" },
];



const typeLabel: Record<string, string> = {
  할인: "할인",
  적립: "적립",
  캐시백: "캐시백",
  discount: "할인",
  point: "적립",
  cashback: "캐시백",
  special: "특별",
};

const categoryIconMap: Record<string, string> = {
  "카페/베이커리": "☕",
  카페: "☕",
  베이커리: "🥐",
  편의점: "🏪",
  교통: "🚌",
  대중교통: "🚌",
  쇼핑: "🛍️",
  온라인쇼핑: "🛒",
  음식: "🍽️",
  외식: "🍽️",
  통신: "📱",
  영화: "🎬",
  문화: "🎬",
  주유: "⛽",
  마트: "🛒",
};

function formatWon(value?: number | null) {
  if (!value) return "없음";
  return `${value.toLocaleString()}원`;
}

function formatManWon(value?: number | null) {
  if (!value) return "없음";
  return `${Math.round(value / 10000)}만원`;
}

function pctDiff(a: number, b: number) {
  if (b === 0 && a === 0) return 0;
  if (b === 0) return 100;
  return Math.round(((a - b) / b) * 100);
}

function getBenefitNumber(valueText?: string) {
  if (!valueText) return 0;
  const matched = valueText.match(/\d+/);
  return matched ? Number(matched[0]) : 0;
}

function getBenefitTypeLabel(type?: string) {
  if (!type) return "";
  return typeLabel[type] ?? type;
}

function getCardColor(idx: number) {
  return CHART_COLORS[idx] ?? "#6667AA";
}

function ApiCardImage({
  imageUrl,
  cardName,
  size = "lg",
}: {
  imageUrl?: string | null;
  cardName: string;
  size?: "sm" | "lg";
}) {
  const sizeClass =
    size === "sm"
      ? "w-20 h-12 rounded-xl"
      : "w-full max-w-[288px] aspect-[1.67/1] rounded-2xl";

  return (
    <div
      className={`${sizeClass} bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center overflow-hidden shadow-sm shrink max-w-full`}
    >
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={cardName}
          className="max-w-full max-h-full object-contain"
          loading="lazy"
        />
      ) : (
        <span className="text-[10px] text-gray-400">이미지 없음</span>
      )}
    </div>
  );
}

function CardPickerModal({
  currentIds,
  onSelect,
  onClose,
}: {
  currentIds: string[];
  onSelect: (id: string) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);

    return () => window.clearTimeout(timer);
  }, [query]);

  const {
    data: searchCards = [],
    isLoading: loading,
  } = useQuery({
    queryKey: ["compareCardSearch", debouncedQuery],
    queryFn: () => searchCompareCards(debouncedQuery),
    staleTime: 1000 * 60 * 5,
  });

  const filteredSearchCards = searchCards.filter(
    (card) => !currentIds.includes(card.cardId),
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(0,0,0,0.45)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg flex flex-col overflow-hidden max-h-[80vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <h3 className="text-base font-normal text-gray-900">카드 선택</h3>
            <p className="text-xs text-gray-400 font-normal mt-0.5">
              비교할 카드를 선택해주세요
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:bg-gray-100 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-3 border-b border-gray-100">
          <div className="flex items-center gap-2 bg-gray-50 rounded-xl px-3 py-2">
            <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="카드명 또는 카드사 검색..."
              className="flex-1 bg-transparent text-sm font-normal text-gray-700 outline-none placeholder-gray-400"
              autoFocus
            />
            {query && (
              <button onClick={() => setQuery("")}>
                <X className="w-3.5 h-3.5 text-gray-400" />
              </button>
            )}
          </div>
        </div>

        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="py-12 text-center text-gray-400 font-normal text-sm">
              카드를 불러오는 중입니다...
            </div>
          ) : filteredSearchCards.length === 0 ? (
            <div className="py-12 text-center text-gray-400 font-normal text-sm">
              검색 결과가 없습니다
            </div>
          ) : (
            filteredSearchCards.map((c) => (
              <button
                key={c.cardId}
                onClick={() => onSelect(c.cardId)}
                className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-[#6667AA]/5 transition-all border-b border-gray-50 last:border-b-0"
              >
                <ApiCardImage imageUrl={c.imageUrl} cardName={c.cardName} size="sm" />

                <div className="flex-1 text-left min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">
                      {c.cardType}
                    </span>
                    <span className="text-[10px] text-gray-400 font-normal">
                      {c.company}
                    </span>
                  </div>
                  <div className="text-sm font-normal text-gray-900 truncate">
                    {c.cardName}
                  </div>
                  <div className="text-[10px] text-gray-400 font-normal mt-0.5">
                    연회비{" "}
                    <span className={c.annualFee === 0 ? "text-green-600" : "text-gray-600"}>
                      {c.annualFee === 0 ? "무료" : formatWon(c.annualFee)}
                    </span>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ScoreSummaryCard({
  card,
  rank,
  idx,
}: {
  card: CompareCardItem;
  rank: number;
  idx: number;
}) {
  const rankEmoji = ["🥇", "🥈", "🥉"][rank] ?? "";
  const color = getCardColor(idx);
  const total = Math.round(
    (card.scores.practicality +
      card.scores.annualFee +
      card.scores.performance +
      card.scores.diversity +
      card.scores.limit) /
      5,
  );

  const scoreRows = [
    { label: "실용성", value: card.scores.practicality },
    { label: "연회비 효율", value: card.scores.annualFee },
    { label: "실적 부담↓", value: card.scores.performance },
    { label: "혜택 다양성", value: card.scores.diversity },
    { label: "한도", value: card.scores.limit },
  ];

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex flex-col gap-3"
      style={{ borderTop: `3px solid ${color}` }}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="text-[10px] text-gray-400 font-normal">{card.company}</div>
          <div className="text-sm font-normal text-gray-900 leading-snug truncate">
            {card.cardName}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <span className="text-lg">{rankEmoji}</span>
          <div className="text-xl font-normal" style={{ color }}>
            {total}
            <span className="text-xs text-gray-400 font-normal ml-0.5">점</span>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {scoreRows.map(({ label, value }) => (
          <div key={label} className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500 font-normal w-20 flex-shrink-0">
              {label}
            </span>
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${value}%`, backgroundColor: color, opacity: 0.8 }}
              />
            </div>
            <span className="text-[10px] text-gray-500 font-normal w-8 text-right">
              {value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DetailedPctComparison({
  selectedCards,
  allCategories,
}: {
  selectedCards: CompareCardItem[];
  allCategories: string[];
}) {
  if (selectedCards.length < 2) return null;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-[#6667AA]" />
        <h3 className="text-sm font-normal text-gray-900">상세 퍼센트 비교</h3>
      </div>

      <div className="p-5 space-y-5">
        {allCategories.map((cat) => {
          const catValues = selectedCards.map((card) => {
            const b = card.benefits.find((benefit) => benefit.categoryName === cat);
            return getBenefitNumber(b?.benefitValueText);
          });
          const maxRate = Math.max(...catValues, 1);

          return (
            <div key={cat} className="border border-gray-100 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <span>{categoryIconMap[cat] ?? "✨"}</span>
                <span className="text-sm font-normal text-gray-800">{cat}</span>
              </div>

              <div className="space-y-3">
                {selectedCards.map((card, idx) => {
                  const b = card.benefits.find((benefit) => benefit.categoryName === cat);
                  const rate = getBenefitNumber(b?.benefitValueText);
                  const barPct = Math.round((rate / maxRate) * 100);
                  const isBest = rate === Math.max(...catValues) && rate > 0;
                  const others = catValues.filter((_, i) => i !== idx);
                  const avgOther =
                    others.length > 0 ? others.reduce((a, x) => a + x, 0) / others.length : rate;
                  const diff = pctDiff(rate, avgOther);
                  const isNeutral = diff === 0;
                  const color = getCardColor(idx);

                  return (
                    <div key={card.cardId} className="flex items-center gap-3">
                      <div className="w-40 flex-shrink-0">
                        <div className="text-[10px] text-gray-400 font-normal truncate">
                          {card.company}
                        </div>
                        <div className="text-xs font-normal text-gray-700 truncate">
                          {card.cardName}
                        </div>
                      </div>

                      <div className="flex-1 flex items-center gap-2">
                        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{
                              width: `${barPct}%`,
                              backgroundColor: color,
                              opacity: isBest ? 1 : 0.45,
                            }}
                          />
                        </div>
                        <span
                          className="text-xs font-normal w-20 text-right flex-shrink-0"
                          style={isBest ? { color } : { color: "#6b7280" }}
                        >
                          {b?.benefitValueText ?? "—"}{" "}
                          <span className="text-[10px] text-gray-400">
                            {getBenefitTypeLabel(b?.benefitType)}
                          </span>
                        </span>
                      </div>

                      <div className="w-20 flex-shrink-0 flex justify-end">
                        {isNeutral ? (
                          <span className="inline-flex items-center gap-0.5 text-[10px] text-gray-400 bg-gray-50 border border-gray-200 px-2 py-0.5 rounded-full font-normal">
                            <Minus className="w-2.5 h-2.5" />
                            동일
                          </span>
                        ) : (
                          <span
                            className={`inline-flex items-center gap-0.5 text-[10px] px-2 py-0.5 rounded-full font-normal border ${
                              diff > 0
                                ? "text-emerald-600 bg-emerald-50 border-emerald-200"
                                : "text-red-500 bg-red-50 border-red-200"
                            }`}
                          >
                            {diff > 0 ? (
                              <ArrowUp className="w-2.5 h-2.5" />
                            ) : (
                              <ArrowDown className="w-2.5 h-2.5" />
                            )}
                            {Math.abs(diff)}%
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function CardComparison() {
  const [searchParams] = useSearchParams();
  useAuth();

  const initialIds =
    searchParams
      .get("cards")
      ?.split(",")
      .map((id) => id.trim())
      .filter(Boolean) || [];

  const [selectedIds, setSelectedIds] = useState<string[]>(
    initialIds.length > 0 ? initialIds.slice(0, MAX_COMPARE) : [],
  );
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerSlot, setPickerSlot] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"visual" | "table">("visual");
  const [selectedPersona, setSelectedPersona] = useState<PersonaType>("STUDENT");

const sortedSelectedIds = useMemo(() => [...selectedIds].sort(), [selectedIds]);

  const {
    data: compareApiCards = [],
    isLoading: compareLoading,
    isError: compareIsError,
  } = useQuery({
    queryKey: ["cardCompare", sortedSelectedIds, selectedPersona],
    queryFn: () => compareCards(sortedSelectedIds, selectedPersona as PersonaType),
    enabled: sortedSelectedIds.length >= 2,
  });

  const selectedCards = compareApiCards;


  
  const personaDescription = PERSONA_DETAILS[selectedPersona];

  const personaScores = useMemo(() => {
    return selectedCards.map((card) => {
      const weights = personaDescription?.weights || {};
      let categoryScore = 0;

      card.benefits?.forEach((benefit) => {
        const weight = (weights as any)[benefit.categoryName];
        if (weight) categoryScore += weight;
      });

      const finalScore = Math.min(
        100,
        Math.round(
          categoryScore * 0.7 +
          (card.scores?.practicality || 0) * 0.2 +
          (card.scores?.diversity || 0) * 0.1
        )
      );

      return {
        cardId: card.cardId,
        cardName: card.cardName,
        score: finalScore,
      };
    }).sort((a,b)=>b.score-a.score);
  }, [selectedCards, selectedPersona]);

  const recommendedCard = personaScores[0];


  const removeCard = (id: string) => {
    setSelectedIds((prev) => prev.filter((i) => i !== id));
  };

  const openPicker = (slot: number | null) => {
    setPickerSlot(slot);
    setPickerOpen(true);
  };

  const handlePickerSelect = (newId: string) => {
    if (pickerSlot !== null) {
      setSelectedIds((prev) => {
        const next = [...prev];
        next[pickerSlot] = newId;
        return Array.from(new Set(next)).slice(0, MAX_COMPARE);
      });
    } else {
      setSelectedIds((prev) =>
        prev.length >= MAX_COMPARE || prev.includes(newId)
          ? prev
          : [...prev, newId],
      );
    }

    setPickerOpen(false);
    setPickerSlot(null);
  };

  const pickerExcludeIds = useMemo(() => {
    if (pickerSlot !== null) return selectedIds.filter((_, i) => i !== pickerSlot);
    return selectedIds;
  }, [selectedIds, pickerSlot]);

  const allCategories = useMemo(() => {
    const categories = Array.from(
      new Set(selectedCards.flatMap((card) => card.benefits.map((b) => b.categoryName))),
    );

    return categories.sort((a, b) => {
      if (a === "기타") return 1;
      if (b === "기타") return -1;
      return 0;
    });
  }, [selectedCards]);

  const allScores = useMemo(() => {
    return selectedCards.map((card) => {
      const total = Math.round(
        (card.scores.practicality +
          card.scores.annualFee +
          card.scores.performance +
          card.scores.diversity +
          card.scores.limit) /
          5,
      );

      return {
        total,
        practicality: card.scores.practicality,
        annualFee: card.scores.annualFee,
        performance: card.scores.performance,
        diversity: card.scores.diversity,
        limit: card.scores.limit,
      };
    });
  }, [selectedCards]);

  const rankOrder = useMemo(() => {
    return [...allScores]
      .map((s, i) => ({ score: s.total, idx: i }))
      .sort((a, b) => b.score - a.score)
      .map((x) => x.idx);
  }, [allScores]);

  const getRank = (idx: number) => rankOrder.indexOf(idx);

  const radarData = useMemo(() => {
    const keys = ["practicality", "annualFee", "performance", "diversity", "limit"] as const;
    return ["실용성", "연회비효율", "실적부담↓", "혜택다양성", "한도"].map(
      (subject, i) => {
        const entry: Record<string, string | number> = { subject, fullMark: 100 };
        selectedCards.forEach((card) => {
          entry[card.cardName] = card.scores[keys[i]];
        });
        return entry;
      },
    );
  }, [selectedCards]);

  const benefitChartData = useMemo(() => {
    return allCategories.map((cat) => {
      const entry: Record<string, string | number> = { category: cat };
      selectedCards.forEach((card) => {
        const b = card.benefits.find((benefit) => benefit.categoryName === cat);
        entry[card.cardName] = getBenefitNumber(b?.benefitValueText);
      });
      return entry;
    });
  }, [selectedCards, allCategories]);

  const getBenefitCell = (card: CompareCardItem, category: string) => {
    const b = card.benefits.find((benefit) => benefit.categoryName === category) ?? null;

    if (!b) {
      return <span className="text-gray-300 font-normal text-sm select-none">—</span>;
    }

    return (
      <div className="space-y-0.5">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-normal text-gray-800">
            {b.benefitValueText}{" "}
            <span className="text-[#6667AA]">{getBenefitTypeLabel(b.benefitType)}</span>
          </span>
        </div>
        <div className="text-[11px] text-gray-400 font-normal">{b.benefitTitle}</div>
        <div className="text-[10px] text-gray-400 font-normal leading-relaxed">
          {b.benefitContent}
        </div>
      </div>
    );
  };

  const colCount = MAX_COMPARE;

  const detailTable = (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-x-auto">
      <div className="min-w-[900px]">
        <div
          className="grid border-b-2 border-gray-200 bg-white"
          style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}
        >
          <div className="px-4 py-3 bg-slate-50 border-r border-gray-200 flex items-center">
            <span className="text-xs font-normal text-gray-400">비교 항목</span>
          </div>

          {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
            const card = selectedCards[idx];

            return (
              <div
                key={idx}
                className="px-4 py-3 border-r border-gray-200 last:border-r-0 flex items-center"
                style={card ? { borderTop: `3px solid ${getCardColor(idx)}` } : {}}
              >
                {card ? (
                  <div className="min-w-0">
                    <div className="text-[10px] text-gray-400 font-normal">
                      {card.company}
                    </div>
                    <div className="text-sm font-normal text-gray-900 truncate">
                      {card.cardName}
                    </div>
                  </div>
                ) : (
                  <span className="text-xs text-gray-300 font-normal">—</span>
                )}
              </div>
            );
          })}
        </div>

        <div
          className="grid bg-slate-50 border-b border-gray-200"
          style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}
        >
          <div
            className="px-4 py-2.5 flex items-center gap-2"
            style={{ gridColumn: "1 / -1" }}
          >
            <span className="text-xs font-normal text-gray-500">📋 기본 정보</span>
          </div>
        </div>

        {[
          ["전월실적", (card: CompareCardItem) => formatManWon(card.minPerformance)],
          ["카드 종류", (card: CompareCardItem) => card.cardType],
          ["카드 네트워크", (card: CompareCardItem) => card.network ?? "—"],
        ].map(([label, getter]) => (
          <div
            key={label as string}
            className="grid border-b border-gray-100"
            style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}
          >
            <div className="px-4 py-3 border-r border-gray-100 flex items-center">
              <span className="text-xs font-normal text-gray-500">{label as string}</span>
            </div>

            {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
              const card = selectedCards[idx];

              return (
                <div
                  key={idx}
                  className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center"
                >
                  {card ? (
                    <span className="text-sm font-normal text-gray-800">
                      {(getter as (card: CompareCardItem) => string)(card)}
                    </span>
                  ) : (
                    <span className="text-gray-200 text-sm">—</span>
                  )}
                </div>
              );
            })}
          </div>
        ))}

        <div
          className="grid bg-slate-50 border-b border-gray-200 border-t border-t-gray-200"
          style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}
        >
          <div
            className="px-4 py-2.5 flex items-center gap-2"
            style={{ gridColumn: "1 / -1" }}
          >
            <TrendingUp className="w-3.5 h-3.5 text-[#6667AA]" />
            <span className="text-xs font-normal text-[#6667AA]">혜택 비교</span>
          </div>
        </div>

        {allCategories.map((cat) => (
          <div
            key={cat}
            className="grid border-b border-gray-100"
            style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}
          >
            <div className="px-4 py-3 border-r border-gray-100 flex items-start gap-1.5">
              <span className="text-base leading-none mt-0.5">
                {categoryIconMap[cat] ?? "✨"}
              </span>
              <span className="text-xs font-normal text-gray-600 leading-relaxed">
                {cat}
              </span>
            </div>

            {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
              const card = selectedCards[idx];

              return (
                <div
                  key={idx}
                  className="px-4 py-3 border-r border-gray-100 last:border-r-0"
                >
                  {card ? getBenefitCell(card, cat) : <span className="text-gray-200 text-sm">—</span>}
                </div>
              );
            })}
          </div>
        ))}

        <div
          className="grid"
          style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}
        >
          <div className="px-4 py-4 border-r border-gray-100 flex items-center">
            <span className="text-xs font-normal text-gray-400">카드 상세</span>
          </div>
          {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
            const card = selectedCards[idx];

            return (
              <div
                key={idx}
                className="px-4 py-4 border-r border-gray-100 last:border-r-0 flex items-center"
              >
                {card ? (
                  <Link
                    to={`/cards/${encodeURIComponent(card.cardId)}`}
                    className="flex items-center gap-1 text-xs text-[#6667AA] hover:underline font-normal"
                  >
                    상세보기 <ChevronRight className="w-3 h-3" />
                  </Link>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  return (
    <div className="bg-[#E9EEF5] min-h-screen">
      {pickerOpen && (
        <CardPickerModal
          currentIds={pickerExcludeIds}
          onSelect={handlePickerSelect}
          onClose={() => {
            setPickerOpen(false);
            setPickerSlot(null);
          }}
        />
      )}

      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1280px] mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-normal text-gray-900 mb-0.5">카드 비교</h1>
            <p className="text-gray-500 text-sm font-normal">
              혜택·연회비·전월실적 기준으로 최대 3장을 나란히 비교해보세요
            </p>
          </div>

          <div className="flex items-center gap-2 text-sm font-normal text-gray-500 bg-slate-50 px-4 py-2 rounded-xl border border-gray-200">
            <GitCompare className="w-4 h-4" />
            <span className="text-[#6667AA]">{selectedCards.length}</span> / {MAX_COMPARE} 카드 선택됨
          </div>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8">
        {compareLoading && (
          <div className="mb-4 rounded-xl border border-[#6667AA]/20 bg-[#6667AA]/5 px-4 py-3 text-sm text-[#6667AA]">
            카드 비교 정보를 불러오는 중입니다...
          </div>
        )}

        {compareIsError && (
          <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            카드 비교 정보를 불러오지 못했습니다.
          </div>
        )}

        <div
          className="grid gap-3 mb-6"
          style={{ gridTemplateColumns: `repeat(${MAX_COMPARE}, minmax(0, 1fr))` }}
        >
          {Array.from({ length: MAX_COMPARE }).map((_, slotIdx) => {
            const card = selectedCards[slotIdx];

            return (
              <div key={slotIdx}>
                {card ? (
                  <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 flex flex-col items-center gap-4 relative min-h-[260px]">
                    <button
                      onClick={() => removeCard(card.cardId)}
                      className="absolute top-3 right-3 w-6 h-6 rounded-full bg-gray-100 hover:bg-red-50 hover:text-red-500 text-gray-400 flex items-center justify-center transition-all"
                    >
                      <X className="w-3 h-3" />
                    </button>

                    <div className="w-full max-w-[288px] min-w-0 flex justify-center">
                      <ApiCardImage imageUrl={card.imageUrl} cardName={card.cardName} size="lg" />
                    </div>

                    <div className="text-center">
                      <div className="text-[10px] text-gray-400 font-normal mb-0.5">
                        {card.company}
                      </div>
                      <div className="text-sm font-normal text-gray-900 leading-snug">
                        {card.cardName}
                      </div>
                    </div>

                    <button
                      onClick={() => openPicker(slotIdx)}
                      className="text-xs text-[#6667AA] font-normal hover:underline"
                    >
                      카드 변경
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => openPicker(null)}
                    className="w-full min-h-[260px] border-2 border-dashed border-gray-200 hover:border-[#6667AA] rounded-2xl flex flex-col items-center justify-center gap-2 text-gray-400 hover:text-[#6667AA] transition-all bg-white"
                  >
                    <div className="w-10 h-10 rounded-full border-2 border-dashed border-current flex items-center justify-center">
                      <Plus className="w-5 h-5" />
                    </div>
                    <span className="text-sm font-normal">카드 추가</span>
                    <span className="text-xs font-normal opacity-70">클릭해서 선택</span>
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {selectedCards.length < 2 ? (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm py-16 text-center">
            <GitCompare className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm font-normal">
              비교하려면 카드를 2장 이상 선택해주세요.
            </p>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-5">
              <button
                onClick={() => setActiveTab("visual")}
                className={`px-4 py-2 rounded-xl text-sm font-normal transition-all ${
                  activeTab === "visual"
                    ? "bg-[#6667AA] text-white"
                    : "bg-white text-gray-500 border border-gray-200"
                }`}
              >
                페르소나
              </button>
              <button
                onClick={() => setActiveTab("table")}
                className={`px-4 py-2 rounded-xl text-sm font-normal transition-all ${
                  activeTab === "table"
                    ? "bg-[#6667AA] text-white"
                    : "bg-white text-gray-500 border border-gray-200"
                }`}
              >
                상세 퍼센트 비교
              </button>
            
</div>

            <div className="bg-white border border-gray-200 rounded-2xl p-4 mb-5">
              <div className="grid grid-cols-5 gap-3">
                {PERSONAS.map((persona) => (
                  <button
                    key={persona.id}
                    onClick={() => setSelectedPersona(persona.id)}
                    className={`rounded-xl border p-3 transition-all text-center ${
                      selectedPersona === persona.id
                        ? "bg-[#6667AA] text-white border-[#6667AA]"
                        : "bg-white text-gray-700 border-gray-200"
                    }`}
                  >
                    <div className="text-2xl mb-1">{persona.emoji}</div>
                    <div className="text-xs font-medium">{persona.name}</div>
                  </button>
                ))}
              </div>
              <div className="mt-4 text-sm text-gray-600">
                {PERSONAS.find((p) => p.id === selectedPersona)?.tags}
              </div>

              <div className="mt-4 p-4 rounded-xl bg-[#F8F8FC] border">
                <div className="font-semibold text-[#6667AA] mb-1">
                  {PERSONAS.find((p) => p.id === selectedPersona)?.name}
                </div>
                <div className="text-sm text-gray-600">
                  {personaDescription?.description}
                </div>
              </div>

              {recommendedCard && (
                <div className="mt-4 p-4 rounded-xl bg-gradient-to-r from-[#6667AA] to-[#7C7DD8] text-white">
                  <div className="text-sm opacity-90">🏆 추천 카드</div>
                  <div className="font-bold text-lg">{recommendedCard.cardName}</div>
                  <div className="text-sm mt-1">적합도 {recommendedCard.score}점</div>
                </div>
              )}
            </div>

            {activeTab === "visual" && (
              <div className="space-y-6">
                <div
                  className="grid gap-4"
                  style={{
                    gridTemplateColumns: `repeat(${selectedCards.length}, minmax(0, 1fr))`,
                  }}
                >
                  {selectedCards.map((card, idx) => (
                    <ScoreSummaryCard
                      key={card.cardId}
                      card={card}
                      idx={idx}
                      rank={getRank(idx)}
                    />
                  ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <Trophy className="w-4 h-4 text-[#6667AA]" />
                      <h3 className="text-sm font-normal text-gray-900">점수 비교</h3>
                    </div>

                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={radarData}>
                          <PolarGrid stroke="#e5e7eb" />
                          <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                          {selectedCards.map((card, idx) => (
                            <Radar
                              key={card.cardId}
                              name={card.cardName}
                              dataKey={card.cardName}
                              stroke={getCardColor(idx)}
                              fill={getCardColor(idx)}
                              fillOpacity={0.18}
                            />
                          ))}
                          <Legend />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <Zap className="w-4 h-4 text-[#6667AA]" />
                      <h3 className="text-sm font-normal text-gray-900">
                        카테고리별 혜택률
                      </h3>
                    </div>

                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={benefitChartData}>
                          <XAxis dataKey="category" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip />
                          <Legend />
                          {selectedCards.map((card, idx) => (
                            <Bar
                              key={card.cardId}
                              dataKey={card.cardName}
                              fill={getCardColor(idx)}
                              radius={[4, 4, 0, 0]}
                            />
                          ))}
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {detailTable}
              </div>
            )}

            {activeTab === "table" && (
              <DetailedPctComparison
                selectedCards={selectedCards}
                allCategories={allCategories}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}