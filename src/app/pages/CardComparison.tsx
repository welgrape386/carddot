import { useMemo, useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router";
import {
  Plus,
  X,
  GitCompare,
  ChevronRight,
  Search,
  TrendingUp,
  Trophy,
  Zap,
  Star,
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
import { cards, Card } from "../data/mockData";
import { CardVisual } from "../components/CardVisual";
import { useAuth } from "../context/AuthContext";

const MAX_COMPARE = 3;
const CHART_COLORS = ["#6667AA", "#F59E0B", "#10B981"];

const typeLabel: Record<string, string> = {
  discount: "할인",
  cashback: "캐시백",
  point: "적립",
  special: "특별",
};

// ─── 퍼센트 차이 계산 ────────────────────────────
function pctDiff(a: number, b: number) {
  if (b === 0 && a === 0) return 0;
  if (b === 0) return 100;
  return Math.round(((a - b) / b) * 100);
}

// ─── 카드 선택 모달 ──────────────────────────────
function CardPickerModal({
  currentIds,
  onSelect,
  onClose,
}: {
  currentIds: number[];
  onSelect: (id: number) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const filtered = cards.filter(
    (c) =>
      !currentIds.includes(c.id) &&
      (query === "" ||
        c.name.toLowerCase().includes(query.toLowerCase()) ||
        c.issuer.toLowerCase().includes(query.toLowerCase()) ||
        c.tags.some((t) => t.includes(query))),
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
            <p className="text-xs text-gray-400 font-normal mt-0.5">비교할 카드를 선택해주세요</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:bg-gray-100 transition-all">
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
            {query && <button onClick={() => setQuery("")}><X className="w-3.5 h-3.5 text-gray-400" /></button>}
          </div>
        </div>
        <div className="overflow-y-auto flex-1">
          {filtered.length === 0 ? (
            <div className="py-12 text-center text-gray-400 font-normal text-sm">검색 결과가 없습니다</div>
          ) : (
            filtered.map((c) => (
              <button key={c.id} onClick={() => onSelect(c.id)}
                className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-[#6667AA]/5 transition-all border-b border-gray-50 last:border-b-0"
              >
                <CardVisual card={c} size="sm" />
                <div className="flex-1 text-left min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={`text-[10px] font-normal px-1.5 py-0.5 rounded ${c.type === "credit" ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600"}`}>
                      {c.type === "credit" ? "신용" : "체크"}
                    </span>
                    <span className="text-[10px] text-gray-400 font-normal">{c.issuer}</span>
                  </div>
                  <div className="text-sm font-normal text-gray-900 truncate">{c.name}</div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-[10px] text-gray-400 font-normal">
                      연회비 <span className={c.annualFee === 0 ? "text-green-600" : "text-gray-600"}>
                        {c.annualFee === 0 ? "무료" : `${c.annualFee.toLocaleString()}원`}
                      </span>
                    </span>
                    <span className="text-[10px] text-gray-400 font-normal">
                      월최대 <span className="text-[#6667AA]">{(c.maxBenefit / 10000).toFixed(0)}만원</span>
                    </span>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-300 flex-shrink-0" />
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ─── 종합 점수 계산 ──────────────────────────────
function calcScores(card: Card, allCards: Card[]) {
  const maxBenefit = Math.max(...allCards.map((c) => c.maxBenefit), 1);
  const maxFee = Math.max(...allCards.map((c) => c.annualFee), 1);
  const maxSpending = Math.max(...allCards.map((c) => c.minSpending), 1);
  const maxBenefitCount = Math.max(...allCards.map((c) => c.benefits.length), 1);
  const benefitScore = Math.round((card.maxBenefit / maxBenefit) * 100);
  const feeScore = Math.round(((maxFee - card.annualFee) / maxFee) * 100);
  const spendingScore = Math.round(((maxSpending - card.minSpending) / maxSpending) * 100);
  const ratingScore = Math.round((card.rating / 5) * 100);
  const diversityScore = Math.round((card.benefits.length / maxBenefitCount) * 100);
  const total = Math.round(benefitScore * 0.3 + feeScore * 0.25 + spendingScore * 0.2 + ratingScore * 0.15 + diversityScore * 0.1);
  return { benefitScore, feeScore, spendingScore, ratingScore, diversityScore, total };
}

// ─── 종합 점수 카드 ──────────────────────────────
function ScoreSummaryCard({ card, scores, rank, color }: { card: Card; scores: ReturnType<typeof calcScores>; rank: number; color: string }) {
  const rankEmoji = ["🥇", "🥈", "🥉"][rank] ?? "";
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex flex-col gap-3" style={{ borderTop: `3px solid ${card.color}` }}>
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="text-[10px] text-gray-400 font-normal">{card.issuer}</div>
          <div className="text-sm font-normal text-gray-900 leading-snug truncate">{card.name}</div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <span className="text-lg">{rankEmoji}</span>
          <div className="text-xl font-normal" style={{ color }}>
            {scores.total}<span className="text-xs text-gray-400 font-normal ml-0.5">점</span>
          </div>
        </div>
      </div>
      <div className="space-y-2">
        {[
          { label: "최대 혜택", value: scores.benefitScore },
          { label: "연회비 효율", value: scores.feeScore },
          { label: "실적 부담↓", value: scores.spendingScore },
          { label: "평점", value: scores.ratingScore },
          { label: "혜택 다양성", value: scores.diversityScore },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500 font-normal w-20 flex-shrink-0">{label}</span>
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-700" style={{ width: `${value}%`, backgroundColor: card.color, opacity: 0.8 }} />
            </div>
            <span className="text-[10px] text-gray-500 font-normal w-8 text-right">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── 카테고리별 혜택률 Bar 데이터 ────────────────
function buildBenefitChartData(selectedCards: Card[], allCategories: string[]) {
  return allCategories.map((cat) => {
    const entry: Record<string, string | number> = { category: cat };
    selectedCards.forEach((card) => {
      const b = card.benefits.find((b) => b.category === cat);
      entry[card.name] = b ? b.discountRate : 0;
    });
    return entry;
  });
}

// ─── 상세 퍼센트 비교 섹션 ───────────────────────
function DetailedPctComparison({ selectedCards, allCategories }: { selectedCards: Card[]; allCategories: string[] }) {
  if (selectedCards.length < 2) return null;

  const metrics: {
    key: string; label: string; icon: string;
    getValue: (c: Card) => number; higherIsBetter: boolean;
    format: (v: number) => string;
  }[] = [
    { key: "maxBenefit", label: "월 최대 혜택", icon: "🏆", getValue: (c) => c.maxBenefit, higherIsBetter: true, format: (v) => v === 0 ? "없음" : `${(v / 10000).toFixed(0)}만원` },
    { key: "annualFee", label: "연회비", icon: "💳", getValue: (c) => c.annualFee, higherIsBetter: false, format: (v) => v === 0 ? "무료" : `${v.toLocaleString()}원` },
    { key: "minSpending", label: "전월실적", icon: "📊", getValue: (c) => c.minSpending, higherIsBetter: false, format: (v) => v === 0 ? "무실적" : `${(v / 10000).toFixed(0)}만원` },
    { key: "rating", label: "사용자 평점", icon: "⭐", getValue: (c) => Math.round(c.rating * 10), higherIsBetter: true, format: (v) => `${(v / 10).toFixed(1)}점` },
  ];

  // 공통 카테고리만 (모든 선택 카드가 갖고 있는)
  const sharedCategories = allCategories.filter((cat) =>
    selectedCards.every((c) => c.benefits.some((b) => b.category === cat)),
  );

  return (
    <div className="mt-12 space-y-5">
      {/* 구분선 + 제목 */}
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-gray-200" />
        <div className="flex items-center gap-2 px-4 py-1.5 bg-[#6667AA]/8 rounded-full border border-[#6667AA]/20">
          <span className="text-sm text-[#6667AA] font-normal">📐 상세 퍼센트 비교</span>
        </div>
        <div className="h-px flex-1 bg-gray-200" />
      </div>
      <p className="text-[11px] text-gray-400 font-normal text-center">
        선택한 카드들 사이의 수치 차이를 퍼센트(%)로 환산합니다 · ↑ 상위 / ↓ 하위 (다른 카드 평균 대비)
      </p>

      {/* ── 공통 카테고리 혜택률 퍼센트 비교 ── */}
      {sharedCategories.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 bg-slate-50">
            <span className="text-xs font-normal text-gray-700">🎯 공통 카테고리 혜택률 퍼센트 비교</span>
            <p className="text-[10px] text-gray-400 font-normal mt-0.5">모든 선택 카드가 공통으로 제공하는 카테고리에서의 혜택률(%) 차이</p>
          </div>
          <div className="divide-y divide-gray-50">
            {sharedCategories.map((cat) => {
              const catValues = selectedCards.map((card) => card.benefits.find((b) => b.category === cat)?.discountRate ?? 0);
              const maxRate = Math.max(...catValues, 0.01);
              const icon = selectedCards.flatMap((c) => c.benefits).find((b) => b.category === cat)?.icon ?? "";
              return (
                <div key={cat} className="px-5 py-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-base">{icon}</span>
                    <span className="text-sm font-normal text-gray-800">{cat}</span>
                    <span className="text-[10px] text-gray-400 font-normal ml-1">혜택률 비교</span>
                  </div>
                  <div className="space-y-2.5">
                    {selectedCards.map((card, idx) => {
                      const b = card.benefits.find((b) => b.category === cat);
                      const rate = b ? b.discountRate : 0;
                      const barPct = Math.round((rate / maxRate) * 100);
                      const isBest = rate === Math.max(...catValues);
                      const others = catValues.filter((_, i) => i !== idx);
                      const avgOther = others.length > 0 ? others.reduce((a, x) => a + x, 0) / others.length : rate;
                      const diff = pctDiff(rate, avgOther);
                      const isNeutral = diff === 0;
                      return (
                        <div key={card.id} className="flex items-center gap-3">
                          <div className="w-40 flex-shrink-0">
                            <div className="text-[10px] text-gray-400 font-normal truncate">{card.issuer}</div>
                            <div className="text-xs font-normal text-gray-700 truncate">{card.name}</div>
                          </div>
                          <div className="flex-1 flex items-center gap-2">
                            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                              <div className="h-full rounded-full transition-all duration-700"
                                style={{ width: `${barPct}%`, backgroundColor: CHART_COLORS[idx] ?? card.color, opacity: isBest ? 1 : 0.45 }}
                              />
                            </div>
                            <span className="text-xs font-normal w-20 text-right flex-shrink-0"
                              style={isBest ? { color: CHART_COLORS[idx] ?? card.color } : { color: "#6b7280" }}>
                              {rate}%{" "}<span className="text-[10px] text-gray-400">{b ? typeLabel[b.type] : ""}</span>
                            </span>
                          </div>
                          <div className="w-20 flex-shrink-0 flex justify-end">
                            {isNeutral ? (
                              <span className="inline-flex items-center gap-0.5 text-[10px] text-gray-400 bg-gray-50 border border-gray-200 px-2 py-0.5 rounded-full font-normal">
                                <Minus className="w-2.5 h-2.5" />동일
                              </span>
                            ) : (
                              <span className={`inline-flex items-center gap-0.5 text-[10px] px-2 py-0.5 rounded-full font-normal border ${diff > 0 ? "text-emerald-600 bg-emerald-50 border-emerald-200" : "text-red-500 bg-red-50 border-red-200"}`}>
                                {diff > 0 ? <ArrowUp className="w-2.5 h-2.5" /> : <ArrowDown className="w-2.5 h-2.5" />}
                                {Math.abs(diff)}%
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {selectedCards.length === 2 && (() => {
                    const d = pctDiff(catValues[0], catValues[1]);
                    if (d === 0) return null;
                    const winIdx = d > 0 ? 0 : 1;
                    const losIdx = winIdx === 0 ? 1 : 0;
                    return (
                      <div className="mt-2 pl-[172px] text-[10px] text-gray-400 font-normal">
                        💡 <span className="text-gray-600">{selectedCards[winIdx].name}</span>이(가){" "}
                        <span className="text-gray-600">{selectedCards[losIdx].name}</span>보다{" "}
                        <span className="font-normal" style={{ color: CHART_COLORS[winIdx] ?? selectedCards[winIdx].color }}>
                          {Math.abs(d)}% 높은 혜택률
                        </span>
                      </div>
                    );
                  })()}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── 메인 ────────────────────────────────────────
export function CardComparison() {
  const [searchParams] = useSearchParams();
  const { addRecentlyCompared } = useAuth();
  const initialIds = searchParams.get("cards")?.split(",").map(Number).filter(Boolean) || [];

  const [selectedIds, setSelectedIds] = useState<number[]>(
    initialIds.length > 0 ? initialIds.slice(0, MAX_COMPARE) : [1, 3],
  );
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerSlot, setPickerSlot] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"visual" | "table">("visual");

  const selectedCards = selectedIds.map((id) => cards.find((c) => c.id === id)).filter(Boolean) as Card[];

  const removeCard = (id: number) => setSelectedIds((prev) => prev.filter((i) => i !== id));
  const openPicker = (slot: number | null) => { setPickerSlot(slot); setPickerOpen(true); };
  const handlePickerSelect = (newId: number) => {
    if (pickerSlot !== null) {
      setSelectedIds((prev) => { const next = [...prev]; next[pickerSlot] = newId; return next; });
    } else {
      setSelectedIds((prev) => prev.length >= MAX_COMPARE || prev.includes(newId) ? prev : [...prev, newId]);
    }
    setPickerOpen(false);
    setPickerSlot(null);
  };

  const pickerExcludeIds = useMemo(() => {
    if (pickerSlot !== null) return selectedIds.filter((_, i) => i !== pickerSlot);
    return selectedIds;
  }, [selectedIds, pickerSlot]);

  const allCategories = useMemo(
    () => Array.from(new Set(selectedCards.flatMap((c) => c.benefits.map((b) => b.category)))),
    [selectedCards],
  );

  useEffect(() => {
    if (selectedIds.length >= 2) addRecentlyCompared(selectedIds);
  }, [selectedIds]);

  const allScores = useMemo(() => selectedCards.map((card) => calcScores(card, selectedCards)), [selectedCards]);
  const rankOrder = useMemo(() => {
    return [...allScores].map((s, i) => ({ score: s.total, idx: i })).sort((a, b) => b.score - a.score).map((x) => x.idx);
  }, [allScores]);
  const getRank = (idx: number) => rankOrder.indexOf(idx);

  const radarData = useMemo(() => {
    const keys = ["benefitScore", "feeScore", "spendingScore", "ratingScore", "diversityScore"] as const;
    return ["최대혜택", "연회비효율", "실적부담↓", "평점", "혜택다양성"].map((subject, i) => {
      const entry: Record<string, string | number> = { subject, fullMark: 100 };
      selectedCards.forEach((card, ci) => { entry[card.name] = allScores[ci][keys[i]]; });
      return entry;
    });
  }, [selectedCards, allScores]);

  const benefitChartData = useMemo(() => buildBenefitChartData(selectedCards, allCategories), [selectedCards, allCategories]);

  const getBenefitCell = (card: Card, category: string) => {
    const b = card.benefits.find((b) => b.category === category) ?? null;
    if (!b) return <span className="text-gray-300 font-normal text-sm select-none">—</span>;
    return (
      <div className="space-y-0.5">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-normal text-gray-800">{b.discountRate}% <span className="text-[#6667AA]">{typeLabel[b.type]}</span></span>
        </div>
        <div className="text-[11px] text-gray-400 font-normal">최대 {(b.maxMonthly / 10000).toFixed(0)}만원</div>
        {b.condition !== "제한없음" && <div className="text-[10px] text-gray-400 font-normal">{b.condition}</div>}
      </div>
    );
  };

  const colCount = MAX_COMPARE;

  return (
    <div className="bg-[#E9EEF5] min-h-screen">
      {pickerOpen && (
        <CardPickerModal currentIds={pickerExcludeIds} onSelect={handlePickerSelect}
          onClose={() => { setPickerOpen(false); setPickerSlot(null); }} />
      )}

      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1280px] mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-normal text-gray-900 mb-0.5">카드 비교</h1>
            <p className="text-gray-500 text-sm font-normal">혜택·연회비·전월실적 기준으로 최대 3장을 나란히 비교해보세요</p>
          </div>
          <div className="flex items-center gap-2 text-sm font-normal text-gray-500 bg-slate-50 px-4 py-2 rounded-xl border border-gray-200">
            <GitCompare className="w-4 h-4" />
            <span className="text-[#6667AA]">{selectedCards.length}</span> / {MAX_COMPARE} 카드 선택됨
          </div>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8">
        {/* 카드 슬롯 */}
        <div className="grid gap-3 mb-6" style={{ gridTemplateColumns: `repeat(${MAX_COMPARE}, minmax(0, 1fr))` }}>
          {Array.from({ length: MAX_COMPARE }).map((_, slotIdx) => {
            const card = selectedCards[slotIdx];
            return (
              <div key={slotIdx}>
                {card ? (
                  <div className="relative bg-white rounded-2xl border border-gray-200 shadow-sm px-4 py-5 flex flex-col items-center gap-3">
                    <button onClick={() => removeCard(card.id)}
                      className="absolute top-3 right-3 w-6 h-6 rounded-full bg-gray-100 hover:bg-red-50 hover:text-red-500 text-gray-400 flex items-center justify-center transition-all">
                      <X className="w-3 h-3" />
                    </button>
                    <CardVisual card={card} size="lg" />
                    <div className="text-center">
                      <div className="text-[10px] text-gray-400 font-normal mb-0.5">{card.issuer}</div>
                      <div className="text-sm font-normal text-gray-900 leading-snug">{card.name}</div>
                    </div>
                    <button onClick={() => openPicker(slotIdx)} className="text-xs text-[#6667AA] font-normal hover:underline">카드 변경</button>
                  </div>
                ) : (
                  <button onClick={() => openPicker(null)}
                    className="w-full min-h-[200px] border-2 border-dashed border-gray-200 hover:border-[#6667AA] rounded-2xl flex flex-col items-center justify-center gap-2 text-gray-400 hover:text-[#6667AA] transition-all bg-white">
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
          <div className="text-center py-20 bg-white rounded-2xl border border-gray-100 shadow-sm">
            <GitCompare className="w-12 h-12 text-gray-200 mx-auto mb-3" />
            <p className="text-gray-500 font-normal">비교할 카드를 2개 이상 선택해주세요</p>
            <Link to="/cards" className="mt-4 inline-flex items-center gap-1 text-sm text-[#6667AA] hover:underline font-normal">
              카드 둘러보기 <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <>
            {/* 탭 전환 */}
            <div className="flex items-center gap-1 mb-5 bg-white rounded-xl border border-gray-200 p-1 w-fit shadow-sm">
              <button onClick={() => setActiveTab("visual")}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-normal transition-all ${activeTab === "visual" ? "bg-[#6667AA] text-white shadow-sm" : "text-gray-500 hover:text-gray-700"}`}>
                <BarChart3 className="w-4 h-4" />한눈에 비교
              </button>
              <button onClick={() => setActiveTab("table")}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-normal transition-all ${activeTab === "table" ? "bg-[#6667AA] text-white shadow-sm" : "text-gray-500 hover:text-gray-700"}`}>
                <TrendingUp className="w-4 h-4" />상세 비교표
              </button>
            </div>

            {/* ── TAB 1: 한눈에 비교 ── */}
            {activeTab === "visual" && (
              <div className="space-y-5">
                {/* 종합 점수 */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <Trophy className="w-4 h-4 text-[#6667AA]" />
                    <h2 className="text-sm font-normal text-gray-800">종합 점수 비교</h2>
                    <span className="text-[10px] text-gray-400 font-normal ml-1">최대혜택 30% · 연회비효율 25% · 실적부담 20% · 평점 15% · 혜택다양성 10%</span>
                  </div>
                  <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${selectedCards.length}, minmax(0, 1fr))` }}>
                    {selectedCards.map((card, idx) => (
                      <ScoreSummaryCard key={card.id} card={card} scores={allScores[idx]} rank={getRank(idx)} color={CHART_COLORS[idx] ?? card.color} />
                    ))}
                  </div>
                </div>

                {/* Radar Chart */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <Zap className="w-4 h-4 text-[#6667AA]" />
                    <h2 className="text-sm font-normal text-gray-800">다차원 비교 레이더</h2>
                  </div>
                  <div className="flex flex-col md:flex-row items-center gap-6">
                    <div className="w-full md:w-[380px] h-[300px] flex-shrink-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={radarData} outerRadius={110}>
                          <PolarGrid stroke="#e5e7eb" />
                          <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: "#6b7280" }} />
                          {selectedCards.map((card, idx) => (
                            <Radar key={card.id} name={card.name} dataKey={card.name}
                              stroke={CHART_COLORS[idx] ?? card.color} fill={CHART_COLORS[idx] ?? card.color}
                              fillOpacity={0.12} strokeWidth={2} />
                          ))}
                          <Legend formatter={(v) => <span style={{ fontSize: 11, color: "#6b7280" }}>{v}</span>} />
                          <Tooltip formatter={(val: number, name: string) => [`${val}점`, name]}
                            contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex-1 grid grid-cols-1 gap-3 w-full">
                      {[
                        { label: "최대혜택", desc: "월 최대 혜택 금액 기준", icon: "💰", keyIdx: 0 },
                        { label: "연회비효율", desc: "연회비가 낮을수록 높은 점수", icon: "💳", keyIdx: 1 },
                        { label: "실적부담↓", desc: "전월실적이 낮을수록 유리", icon: "📊", keyIdx: 2 },
                        { label: "평점", desc: "사용자 리뷰 기반 평점", icon: "⭐", keyIdx: 3 },
                        { label: "혜택다양성", desc: "혜택 카테고리 수 기준", icon: "🎯", keyIdx: 4 },
                      ].map((item) => {
                        const keys = ["benefitScore", "feeScore", "spendingScore", "ratingScore", "diversityScore"] as const;
                        return (
                          <div key={item.label} className="flex items-center gap-3 p-2.5 bg-gray-50 rounded-xl">
                            <span className="text-base">{item.icon}</span>
                            <div>
                              <div className="text-xs font-normal text-gray-800">{item.label}</div>
                              <div className="text-[10px] text-gray-400 font-normal">{item.desc}</div>
                            </div>
                            <div className="ml-auto flex items-center gap-2">
                              {selectedCards.map((card, idx) => {
                                const val = allScores[idx][keys[item.keyIdx]];
                                return (
                                  <div key={card.id} className="flex flex-col items-center">
                                    <div className="w-1.5 h-8 rounded-full overflow-hidden bg-gray-200">
                                      <div className="w-full rounded-full transition-all duration-700"
                                        style={{ height: `${val}%`, backgroundColor: CHART_COLORS[idx] ?? card.color, marginTop: `${100 - val}%` }} />
                                    </div>
                                    <span className="text-[9px] mt-0.5" style={{ color: CHART_COLORS[idx] ?? card.color }}>{val}</span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* 카테고리별 혜택률 Bar Chart */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
                  <div className="flex items-center gap-2 mb-1">
                    <Star className="w-4 h-4 text-[#6667AA]" />
                    <h2 className="text-sm font-normal text-gray-800">카테고리별 혜택률 비교 (%)</h2>
                  </div>
                  <p className="text-[11px] text-gray-400 font-normal mb-4 ml-6">각 카테고리에서 제공하는 할인·적립·캐시백 비율</p>
                  <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={benefitChartData} margin={{ top: 5, right: 20, left: -10, bottom: 60 }} barCategoryGap="28%" barGap={3}>
                        <XAxis dataKey="category" tick={{ fontSize: 11, fill: "#9ca3af" }} angle={-35} textAnchor="end" interval={0} height={70} />
                        <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickFormatter={(v) => `${v}%`} width={36} />
                        <Tooltip formatter={(val: number, name: string) => [`${val}%`, name]}
                          contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }} />
                        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                          formatter={(v) => <span style={{ fontSize: 11, color: "#6b7280" }}>{v}</span>} />
                        {selectedCards.map((card, idx) => (
                          <Bar key={card.id} dataKey={card.name} fill={CHART_COLORS[idx] ?? card.color} radius={[4, 4, 0, 0]} maxBarSize={36} />
                        ))}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 핵심 수치 3개 요약 */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingUp className="w-4 h-4 text-[#6667AA]" />
                    <h2 className="text-sm font-normal text-gray-800">핵심 수치 한눈에 보기</h2>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                      { label: "💳 연회비", bg: "bg-blue-50 border-blue-100", text: "text-blue-600", getVal: (c: Card) => c.annualFee === 0 ? "무료" : `${c.annualFee.toLocaleString()}원`, getCls: (c: Card) => c.annualFee === 0 ? "text-green-600" : "text-gray-700" },
                      { label: "📊 전월실적 조건", bg: "bg-amber-50 border-amber-100", text: "text-amber-600", getVal: (c: Card) => c.minSpending === 0 ? "무실적" : `${(c.minSpending / 10000).toFixed(0)}만원`, getCls: () => "text-gray-700" },
                      { label: "🏆 월 최대 혜택", bg: "bg-purple-50 border-purple-100", text: "text-[#6667AA]", getVal: (c: Card) => `${(c.maxBenefit / 10000).toFixed(0)}만원`, getCls: (c: Card) => c.maxBenefit === Math.max(...selectedCards.map(x => x.maxBenefit)) && selectedCards.length > 1 ? "text-[#6667AA]" : "text-gray-700" },
                    ].map((col) => (
                      <div key={col.label} className={`rounded-xl ${col.bg} border p-4`}>
                        <div className={`text-xs ${col.text} font-normal mb-3`}>{col.label}</div>
                        <div className="space-y-2">
                          {selectedCards.map((card, idx) => (
                            <div key={card.id} className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: CHART_COLORS[idx] ?? card.color }} />
                              <span className="text-[11px] text-gray-600 font-normal truncate flex-1 min-w-0">{card.name}</span>
                              <span className={`text-xs font-normal flex-shrink-0 ${col.getCls(card)}`}>{col.getVal(card)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 혜택 요약 테이블 */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
                    <span className="text-sm font-normal text-gray-800">📋 카테고리별 혜택 요약</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[500px]">
                      <thead>
                        <tr className="bg-slate-50">
                          <th className="px-4 py-3 text-left text-[11px] text-gray-400 font-normal border-b border-gray-100 w-40">카테고리</th>
                          {selectedCards.map((card, idx) => (
                            <th key={card.id} className="px-4 py-3 text-left text-[11px] font-normal border-b border-gray-100" style={{ color: CHART_COLORS[idx] ?? card.color }}>
                              {card.name}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {allCategories.map((cat, ri) => {
                          const icon = selectedCards.flatMap((c) => c.benefits).find((b) => b.category === cat)?.icon ?? "";
                          const rates = selectedCards.map((card) => card.benefits.find((b) => b.category === cat)?.discountRate ?? 0);
                          const maxRate = Math.max(...rates);
                          return (
                            <tr key={cat} className={ri % 2 === 0 ? "bg-white" : "bg-gray-50/50"}>
                              <td className="px-4 py-3 border-b border-gray-50">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-sm">{icon}</span>
                                  <span className="text-xs text-gray-600 font-normal">{cat}</span>
                                </div>
                              </td>
                              {selectedCards.map((card, idx) => {
                                const b = card.benefits.find((b) => b.category === cat);
                                const isTop = b && b.discountRate === maxRate && maxRate > 0 && rates.filter((r) => r === maxRate).length < selectedCards.length;
                                return (
                                  <td key={card.id} className="px-4 py-3 border-b border-gray-50">
                                    {b ? (
                                      <div className="flex items-center gap-1.5">
                                        <span className="text-sm font-normal" style={isTop ? { color: CHART_COLORS[idx] ?? card.color } : { color: "#374151" }}>{b.discountRate}%</span>
                                        <span className="text-[10px] text-gray-400 font-normal">{typeLabel[b.type]}</span>
                                        {isTop && <span className="text-[9px] px-1 py-0.5 rounded-full font-normal text-white" style={{ backgroundColor: CHART_COLORS[idx] ?? card.color }}>Best</span>}
                                      </div>
                                    ) : (
                                      <span className="text-gray-200 text-sm">—</span>
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* ── TAB 2: 상세 비교표 ── */}
            {activeTab === "table" && (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                {/* 헤더 */}
                <div className="grid border-b-2 border-gray-200 sticky top-16 z-20 bg-white" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-3 bg-slate-50 border-r border-gray-200 flex items-center">
                    <span className="text-xs font-normal text-gray-400">비교 항목</span>
                  </div>
                  {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                    const card = selectedCards[idx];
                    return (
                      <div key={idx} className="px-4 py-3 border-r border-gray-200 last:border-r-0 flex items-center"
                        style={card ? { borderTop: `3px solid ${card.color}` } : {}}>
                        {card ? (
                          <div className="min-w-0">
                            <div className="text-[10px] text-gray-400 font-normal">{card.issuer}</div>
                            <div className="text-sm font-normal text-gray-900 truncate">{card.name}</div>
                          </div>
                        ) : <span className="text-xs text-gray-300 font-normal">—</span>}
                      </div>
                    );
                  })}
                </div>

                {/* 기본 정보 헤더 */}
                <div className="grid bg-slate-50 border-b border-gray-200" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-2.5 flex items-center gap-2" style={{ gridColumn: "1 / -1" }}>
                    <span className="text-xs font-normal text-gray-500">📋 기본 정보</span>
                  </div>
                </div>

                {/* 연회비 */}
                <div className="grid border-b border-gray-100" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-3 border-r border-gray-100 flex items-center"><span className="text-xs font-normal text-gray-500">연회비</span></div>
                  {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                    const card = selectedCards[idx];
                    return (
                      <div key={idx} className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center">
                        {card ? <span className={`text-sm font-normal ${card.annualFee === 0 ? "text-green-600" : "text-gray-800"}`}>{card.annualFee === 0 ? "무료" : `${card.annualFee.toLocaleString()}원`}</span>
                          : <span className="text-gray-200 text-sm">—</span>}
                      </div>
                    );
                  })}
                </div>

                {/* 전월실적 */}
                <div className="grid border-b border-gray-100" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-3 border-r border-gray-100 flex items-center"><span className="text-xs font-normal text-gray-500">전월실적</span></div>
                  {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                    const card = selectedCards[idx];
                    return (
                      <div key={idx} className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center">
                        {card ? <span className="text-sm font-normal text-gray-800">{card.minSpending === 0 ? "무실적" : `${(card.minSpending / 10000).toFixed(0)}만원`}</span>
                          : <span className="text-gray-200 text-sm">—</span>}
                      </div>
                    );
                  })}
                </div>

                {/* 월 최대 혜택 */}
                <div className="grid border-b border-gray-100 bg-[#6667AA]/[0.06]" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-3 border-r border-gray-100 flex items-center"><span className="text-xs font-normal text-gray-500">월 최대 혜택</span></div>
                  {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                    const card = selectedCards[idx];
                    const maxCard = selectedCards.reduce((a, b) => a.maxBenefit > b.maxBenefit ? a : b);
                    const isMax = card && card.id === maxCard.id && selectedCards.length > 1;
                    return (
                      <div key={idx} className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center gap-2">
                        {card ? (<>
                          <span className={`text-sm font-normal ${isMax ? "text-[#6667AA]" : "text-gray-800"}`}>{(card.maxBenefit / 10000).toFixed(0)}만원</span>
                          {isMax && <span className="text-[10px] bg-[#6667AA] text-white px-1.5 py-0.5 rounded-full font-normal">최대</span>}
                        </>) : <span className="text-gray-200 text-sm">—</span>}
                      </div>
                    );
                  })}
                </div>

                {/* 카드 종류 */}
                <div className="grid border-b border-gray-100" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-3 border-r border-gray-100 flex items-center"><span className="text-xs font-normal text-gray-500">카드 종류</span></div>
                  {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                    const card = selectedCards[idx];
                    return (
                      <div key={idx} className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center">
                        {card ? <span className={`text-xs font-normal px-2 py-1 rounded ${card.type === "credit" ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600"}`}>{card.type === "credit" ? "신용카드" : "체크카드"}</span>
                          : <span className="text-gray-200 text-sm">—</span>}
                      </div>
                    );
                  })}
                </div>

                {/* 카드 네트워크 */}
                <div className="grid border-b border-gray-100" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-3 border-r border-gray-100 flex items-center"><span className="text-xs font-normal text-gray-500">카드 네트워크</span></div>
                  {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                    const card = selectedCards[idx];
                    return (
                      <div key={idx} className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center">
                        {card ? <span className="text-sm font-normal text-gray-700">{card.network}</span> : <span className="text-gray-200 text-sm">—</span>}
                      </div>
                    );
                  })}
                </div>

                {/* 혜택 섹션 헤더 */}
                <div className="grid bg-slate-50 border-b border-gray-200 border-t border-t-gray-200" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-2.5 flex items-center gap-2" style={{ gridColumn: "1 / -1" }}>
                    <TrendingUp className="w-3.5 h-3.5 text-[#6667AA]" />
                    <span className="text-xs font-normal text-[#6667AA]">혜택 비교</span>
                  </div>
                </div>

                {allCategories.map((cat) => (
                  <div key={cat} className="grid border-b border-gray-100" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                    <div className="px-4 py-3 border-r border-gray-100 flex items-start gap-1.5">
                      <span className="text-base leading-none mt-0.5">{selectedCards.flatMap((c) => c.benefits).find((b) => b.category === cat)?.icon ?? ""}</span>
                      <span className="text-xs font-normal text-gray-600 leading-relaxed">{cat}</span>
                    </div>
                    {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                      const card = selectedCards[idx];
                      return (
                        <div key={idx} className="px-4 py-3 border-r border-gray-100 last:border-r-0">
                          {card ? getBenefitCell(card, cat) : <span className="text-gray-200 text-sm">—</span>}
                        </div>
                      );
                    })}
                  </div>
                ))}

                {/* 신규 발급 혜택 */}
                <div className="grid border-b border-gray-100" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-3 border-r border-gray-100 flex items-center"><span className="text-xs font-normal text-gray-500">신규 발급 혜택</span></div>
                  {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                    const card = selectedCards[idx];
                    return (
                      <div key={idx} className="px-4 py-3 border-r border-gray-100 last:border-r-0">
                        {card ? (card.eventBenefits.length > 0 ? (
                          <ul className="space-y-1">{card.eventBenefits.map((e, i) => (
                            <li key={i} className="text-xs text-gray-700 font-normal flex items-start gap-1">
                              <span className="text-green-500 mt-0.5">✓</span>{e}
                            </li>
                          ))}</ul>
                        ) : <span className="text-xs text-gray-300 font-normal">없음</span>)
                          : <span className="text-gray-200 text-sm">—</span>}
                      </div>
                    );
                  })}
                </div>

                {/* 상세 보기 링크 */}
                <div className="grid" style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}>
                  <div className="px-4 py-4 border-r border-gray-100 flex items-center"><span className="text-xs font-normal text-gray-400">카드 상세</span></div>
                  {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                    const card = selectedCards[idx];
                    return (
                      <div key={idx} className="px-4 py-4 border-r border-gray-100 last:border-r-0 flex items-center">
                        {card ? (
                          <Link to={`/cards/${card.id}`} className="flex items-center gap-1 text-xs text-[#6667AA] hover:underline font-normal">
                            상세보기 <ChevronRight className="w-3 h-3" />
                          </Link>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* ─── 상세 퍼센트 비교 (탭 공통, 맨 아래) ─── */}
            <DetailedPctComparison selectedCards={selectedCards} allCategories={allCategories} />
          </>
        )}
      </div>
    </div>
  );
}
