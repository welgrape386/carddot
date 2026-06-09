import { useState, useRef, useMemo, useCallback } from "react";
import {
  Upload, CheckCircle2,
  AlertTriangle, Sparkles, TrendingUp, BarChart3,
  Check, RefreshCw, ChevronRight,
} from "lucide-react";
import { cards, Card, issuerMeta } from "../data/mockData";
import { CardVisual } from "../components/CardVisual";

// ─── 상수 ────────────────────────────────────────
const ACCENT = "#6667AA";

const CATEGORY_COLOR: Record<string, string> = {
  "온라인 쇼핑": "#6667AA", "쇼핑": "#6667AA",
  "식당/외식": "#F97316", "외식": "#F97316",
  "마트/편의점": "#10B981", "편의점": "#10B981", "마트": "#10B981",
  "배달앱": "#EF4444",
  "카페": "#8B5CF6",
  "대중교통": "#06B6D4",
  "통신비": "#3B82F6",
  "구독 서비스": "#EC4899", "구독서비스": "#EC4899",
  "주유": "#84CC16",
  "간편결제": "#F59E0B",
  "영화관": "#F43F5E", "문화/여가": "#F43F5E",
  "여행": "#0EA5E9",
  "의료": "#14B8A6",
  "항공": "#0369A1",
};

// 소비 카테고리 → 카드 혜택 카테고리 매핑
const CATEGORY_MATCH: Record<string, string[]> = {
  "온라인 쇼핑": ["온라인 쇼핑", "쇼핑", "간편결제"],
  "식당/외식": ["외식", "식당/외식"],
  "마트/편의점": ["편의점", "마트", "마트/편의점"],
  "배달앱": ["배달앱"],
  "카페": ["카페"],
  "대중교통": ["대중교통"],
  "통신비": ["통신비"],
  "구독서비스": ["구독 서비스"],
  "주유": ["주유"],
};

// ─── 더미 소비 데이터 ─────────────────────────────
interface SpendingItem {
  category: string;
  icon: string;
  amount: number;
  color: string;
}

const DUMMY_SPENDING: SpendingItem[] = [
  { category: "온라인 쇼핑", icon: "🛒", amount: 450000, color: "#6667AA" },
  { category: "식당/외식",   icon: "🍽️", amount: 320000, color: "#F97316" },
  { category: "마트/편의점", icon: "🏪", amount: 180000, color: "#10B981" },
  { category: "배달앱",      icon: "🍕", amount: 150000, color: "#EF4444" },
  { category: "카페",        icon: "☕",  amount: 120000, color: "#8B5CF6" },
  { category: "대중교통",    icon: "🚌", amount: 90000,  color: "#06B6D4" },
  { category: "통신비",      icon: "📱", amount: 75000,  color: "#3B82F6" },
  { category: "구독서비스",  icon: "📺", amount: 60000,  color: "#EC4899" },
  { category: "주유",        icon: "⛽",  amount: 55000,  color: "#84CC16" },
];

// ─── 후보 카드 (각 카드사 대표 1장씩) ──────────────
const ISSUERS = ["삼성카드", "신한카드", "현대카드", "KB국민카드", "NH농협카드", "우리카드", "하나카드", "롯데카드"];
const candidateCards: Card[] = ISSUERS
  .map((issuer) => cards.find((c) => c.issuer === issuer && c.rank === 1))
  .filter((c): c is Card => !!c);

// ─── 헬퍼: 카드 적합도 계산 ──────────────────────
function calcFit(card: Card, spending: SpendingItem[]): number {
  const total = spending.reduce((s, x) => s + x.amount, 0);
  const covered = new Set<string>();
  card.benefits.forEach((b) => {
    spending.forEach((s) => {
      if (CATEGORY_MATCH[s.category]?.includes(b.category)) covered.add(s.category);
    });
  });
  const coveredAmt = spending.filter((s) => covered.has(s.category)).reduce((a, s) => a + s.amount, 0);
  return Math.round((coveredAmt / total) * 100);
}

// ─── 헬퍼: 혜택 매칭 여부 ─────────────────────────
function isBenefitMatched(benefitCategory: string, spending: SpendingItem[]): boolean {
  return spending.some((s) => CATEGORY_MATCH[s.category]?.includes(benefitCategory));
}

// ─── 헬퍼: 중복 혜택 카테고리 ────────────────────
function findOverlaps(selectedCards: Card[]): string[] {
  const catMap: Record<string, number> = {};
  selectedCards.forEach((card) => {
    card.benefits.forEach((b) => {
      catMap[b.category] = (catMap[b.category] ?? 0) + 1;
    });
  });
  return Object.entries(catMap).filter(([, n]) => n > 1).map(([c]) => c);
}

// ═══ 스텝 네비게이터 ══════════════════════════════
function StepNav({
  step,
  hasData,
  hasCards,
  onStepClick,
}: {
  step: number;
  hasData: boolean;
  hasCards: boolean;
  onStepClick: (s: number) => void;
}) {
  const steps = [
    { n: 1, label: "소비 데이터" },
    { n: 2, label: "카드 선택" },
    { n: 3, label: "분석 결과" },
  ];

  const canGo = (n: number) => {
    if (n === 1) return true;
    if (n === 2) return hasData;
    if (n === 3) return hasData && hasCards;
    return false;
  };

  return (
    <div className="flex items-center justify-center gap-0 py-2">
      {steps.map((s, i) => {
        const done = step > s.n;
        const current = step === s.n;
        const locked = !canGo(s.n);
        return (
          <div key={s.n} className="flex items-center">
            <button
              onClick={() => canGo(s.n) && onStepClick(s.n)}
              disabled={locked}
              className={`flex flex-col items-center gap-1.5 px-1 transition-all ${locked ? "cursor-not-allowed opacity-40" : "cursor-pointer"}`}
            >
              <div
                className={`w-9 h-9 rounded-full border-2 flex items-center justify-center transition-all ${
                  current
                    ? "bg-gray-900 border-gray-900 shadow-md"
                    : done
                    ? "bg-gray-400 border-gray-400"
                    : "bg-white border-gray-300"
                }`}
              >
                {done ? (
                  <Check className="w-4 h-4 text-white" />
                ) : (
                  <span
                    className={`text-xs font-normal ${current ? "text-white" : "text-gray-500"}`}
                  >
                    {s.n}
                  </span>
                )}
              </div>
              <span
                className={`text-[11px] font-normal whitespace-nowrap transition-all ${
                  current ? "text-gray-900" : done ? "text-gray-400" : "text-gray-400"
                }`}
              >
                {s.label}
              </span>
            </button>
            {i < steps.length - 1 && (
              <div
                className="w-16 h-0.5 mb-5 mx-1 rounded-full transition-all"
                style={{ backgroundColor: done ? "#9ca3af" : "#e5e7eb" }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ═══ 단계 1: 소비 데이터 ══════════════════════════
function SpendingStep({
  spending,
  onDataLoad,
  onNext,
}: {
  spending: SpendingItem[] | null;
  onDataLoad: (data: SpendingItem[]) => void;
  onNext: () => void;
}) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) simulateLoad();
  }, []);

  const simulateLoad = () => {
    setLoading(true);
    setTimeout(() => { setLoading(false); onDataLoad(DUMMY_SPENDING); }, 900);
  };

  const total = spending ? spending.reduce((a, s) => a + s.amount, 0) : 0;
  const topCategory = spending ? spending.reduce((a, b) => (a.amount > b.amount ? a : b)) : null;

  return (
    <div className="space-y-5">
      {/* 업로드 존 */}
      {!spending && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl px-8 py-12 flex flex-col items-center gap-4 cursor-pointer transition-all ${
            dragging ? "border-[#6667AA] bg-[#6667AA]/5" : "border-gray-300 bg-white hover:border-[#6667AA]/50 hover:bg-[#6667AA]/3"
          }`}
        >
          <div className="w-14 h-14 rounded-2xl bg-[#6667AA]/10 flex items-center justify-center">
            <Upload className="w-6 h-6 text-[#6667AA]" />
          </div>
          <div className="text-center">
            <p className="text-sm font-normal text-gray-700">파일을 드래그하거나 클릭하여 업로드</p>
            <p className="text-xs font-normal text-gray-400 mt-1">CSV · JSON 형식 지원 · 카드사 내역 직접 업로드</p>
          </div>
          <input ref={fileRef} type="file" accept=".csv,.json" className="hidden"
            onChange={() => simulateLoad()} />
        </div>
      )}

      {/* 더미 버튼 / 리셋 버튼 */}
      <div className="flex justify-center gap-3">
        {!spending ? (
          <button
            onClick={simulateLoad}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-[#6667AA]/30 bg-[#6667AA]/5 text-sm font-normal text-[#6667AA] hover:bg-[#6667AA]/10 transition-all disabled:opacity-50"
          >
            {loading ? (
              <><RefreshCw className="w-4 h-4 animate-spin" />불러오는 중...</>
            ) : (
              <><Sparkles className="w-4 h-4" />더미 데이터 불러오기</>
            )}
          </button>
        ) : (
          <button onClick={() => onDataLoad(DUMMY_SPENDING)}
            className="flex items-center gap-1.5 text-xs font-normal text-gray-400 hover:text-gray-600 transition-all">
            <RefreshCw className="w-3.5 h-3.5" />데이터 초기화
          </button>
        )}
      </div>

      {/* 데이터 결과 */}
      {spending && (
        <>
          {/* 요약 카드 3개 */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "월 총 지출", value: `${(total / 10000).toFixed(0)}만원`, icon: "💰", sub: `${spending.length}건 내역`, color: "#6667AA" },
              { label: "카테고리 수", value: `${spending.length}개`, icon: "🗂️", sub: "지출 카테고리", color: "#10B981" },
              { label: "최다 ��출", value: topCategory?.category ?? "", icon: topCategory?.icon ?? "📊", sub: `${((topCategory?.amount ?? 0) / 10000).toFixed(0)}만원 (${Math.round(((topCategory?.amount ?? 0) / total) * 100)}%)`, color: "#F97316" },
            ].map((card) => (
              <div key={card.label} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4">
                <div className="flex items-start justify-between mb-2">
                  <span className="text-xs font-normal text-gray-500">{card.label}</span>
                  <span className="text-xl">{card.icon}</span>
                </div>
                <div className="text-lg font-normal" style={{ color: card.color }}>{card.value}</div>
                <div className="text-[11px] font-normal text-gray-400 mt-0.5">{card.sub}</div>
              </div>
            ))}
          </div>

          {/* 카테고리별 지출 그리드 */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-4 h-4 text-[#6667AA]" />
              <span className="text-sm font-normal text-gray-800">카테고리별 지출</span>
              <span className="text-[10px] font-normal text-gray-400 ml-1">지출 높은 순 정렬</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[...spending].sort((a, b) => b.amount - a.amount).map((item) => {
                const pct = Math.round((item.amount / total) * 100);
                return (
                  <div key={item.category} className="rounded-xl border border-gray-100 p-3 hover:border-gray-200 transition-all">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">{item.icon}</span>
                      <div className="min-w-0">
                        <div className="text-xs font-normal text-gray-800 truncate">{item.category}</div>
                        <div className="text-[10px] font-normal text-gray-400">{pct}%</div>
                      </div>
                    </div>
                    <div className="text-sm font-normal mb-2" style={{ color: item.color }}>
                      {(item.amount / 10000).toFixed(0)}만원
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${pct}%`, backgroundColor: item.color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 다음 단계 */}
          <div className="flex justify-end">
            <button onClick={onNext}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-normal text-white transition-all hover:opacity-90"
              style={{ backgroundColor: ACCENT }}>
              카드 선택으로 <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ═══ 단계 2: 카드 선택 ════════════════════════════
function CardSelectStep({
  spending,
  selectedIds,
  onToggle,
  onNext,
}: {
  spending: SpendingItem[];
  selectedIds: number[];
  onToggle: (id: number) => void;
  onNext: () => void;
}) {
  const fitScores = useMemo(
    () => Object.fromEntries(candidateCards.map((c) => [c.id, calcFit(c, spending)])),
    [spending],
  );

  const sorted = useMemo(
    () => [...candidateCards].sort((a, b) => fitScores[b.id] - fitScores[a.id]),
    [fitScores],
  );

  const fitColor = (pct: number) => pct >= 60 ? "#10B981" : pct >= 40 ? "#F97316" : "#EF4444";
  const fitBg = (pct: number) => pct >= 60 ? "bg-emerald-50 border-emerald-200 text-emerald-700" : pct >= 40 ? "bg-amber-50 border-amber-200 text-amber-700" : "bg-red-50 border-red-200 text-red-500";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-normal text-gray-500">내 소비 데이터와 혜택이 겹치는 태그는 <span className="text-emerald-600">초록색</span>으로 표시돼요</p>
        <span className="text-xs font-normal text-gray-400">최대 3장 선택 · {selectedIds.length}/3</span>
      </div>

      <div className="space-y-2">
        {sorted.map((card) => {
          const fit = fitScores[card.id];
          const selected = selectedIds.includes(card.id);
          const maxable = selectedIds.length >= 3 && !selected;
          const meta = issuerMeta[card.issuer];

          return (
            <button
              key={card.id}
              onClick={() => !maxable && onToggle(card.id)}
              disabled={maxable}
              className={`w-full flex items-center gap-4 p-4 rounded-2xl border-2 transition-all text-left ${
                selected
                  ? "border-gray-900 bg-white shadow-md"
                  : maxable
                  ? "border-gray-100 bg-gray-50/50 opacity-50 cursor-not-allowed"
                  : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
              }`}
            >
              {/* 발급사 컬러 칩 */}
              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-normal flex-shrink-0"
                style={{ backgroundColor: meta?.color ?? card.color }}>
                {meta?.logo ?? card.issuer[0]}
              </div>

              {/* 카드 미니 이미지 */}
              <div className="flex-shrink-0">
                <CardVisual card={card} size="sm" />
              </div>

              {/* 카드 정보 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-normal text-gray-400">{card.issuer}</span>
                  <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                    {card.annualFee === 0 ? "연회비무료" : `${card.annualFee.toLocaleString()}원`}
                  </span>
                </div>
                <div className="text-sm font-normal text-gray-900 mb-2 truncate">{card.name}</div>
                {/* 혜택 태그 */}
                <div className="flex flex-wrap gap-1">
                  {card.benefits.map((b) => {
                    const matched = isBenefitMatched(b.category, spending);
                    return (
                      <span key={b.category}
                        className={`text-[10px] font-normal px-2 py-0.5 rounded-full border transition-all ${
                          matched
                            ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                            : "bg-gray-50 border-gray-200 text-gray-500"
                        }`}>
                        {matched && <span className="mr-0.5">✓</span>}
                        {b.category}
                      </span>
                    );
                  })}
                </div>
              </div>

              {/* 적합도 % */}
              <div className="flex flex-col items-center gap-1 flex-shrink-0">
                <div className={`text-sm font-normal px-3 py-1.5 rounded-xl border ${fitBg(fit)}`}>
                  {fit}%
                </div>
                <span className="text-[10px] font-normal text-gray-400">적합도</span>
              </div>

              {/* 체크박스 */}
              <div className="flex-shrink-0">
                <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                  selected ? "bg-gray-900 border-gray-900" : "border-gray-300"
                }`}>
                  {selected && <Check className="w-3.5 h-3.5 text-white" />}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {selectedIds.length >= 1 && (
        <div className="flex justify-between items-center pt-2">
          <span className="text-xs font-normal text-gray-400">{selectedIds.length}장 선택됨</span>
          <button onClick={onNext}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-normal text-white hover:opacity-90 transition-all"
            style={{ backgroundColor: ACCENT }}>
            분석하기 <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

// ═══ 단계 3: 분석 결과 ════════════════════════════
function ResultStep({
  spending,
  selectedIds,
  onBack,
}: {
  spending: SpendingItem[];
  selectedIds: number[];
  onBack: () => void;
}) {
  const selectedCards = selectedIds.map((id) => candidateCards.find((c) => c.id === id)).filter((c): c is Card => !!c);
  const overlapCategories = findOverlaps(selectedCards);
  const total = spending.reduce((a, s) => a + s.amount, 0);

  // 적합도 계산
  const fitMap = useMemo(
    () => Object.fromEntries(selectedCards.map((c) => [c.id, calcFit(c, spending)])),
    [],
  );

  // 갈아타기 추천 카드 (미선택 카드 중 점수 높은 3장)
  const alternatives = useMemo(() => {
    return candidateCards
      .filter((c) => !selectedIds.includes(c.id))
      .map((c) => {
        const fit = calcFit(c, spending);
        // 중복 혜택 페널티: 선택된 카드들과 겹치는 혜택 카테고리 수 × -12
        const overlapsWithSelected = c.benefits.filter((b) =>
          selectedCards.some((sc) => sc.benefits.some((sb) => sb.category === b.category))
        ).length;
        return { card: c, fit, score: fit - overlapsWithSelected * 12 };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, 3);
  }, []);

  // 유지/교체 판정
  const verdicts = selectedCards.map((card) => ({
    card,
    fit: fitMap[card.id],
    keep: fitMap[card.id] >= 60,
  }));

  // 추천 조합: 유지 카드 + 최적 대안 1장
  const keepCards = verdicts.filter((v) => v.keep).map((v) => v.card);
  const bestAlt = alternatives[0]?.card;
  const switchCards = verdicts.filter((v) => !v.keep);
  const recommendedCombo = [
    ...keepCards,
    ...(switchCards.length > 0 && bestAlt ? [bestAlt] : []),
  ];
  const comboOverlap = findOverlaps(recommendedCombo);

  return (
    <div className="space-y-5">

      {/* ── 카드별 판정 박스 ── */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.min(selectedCards.length, 3)}, minmax(0, 1fr))` }}>
        {verdicts.map(({ card, fit, keep }) => {
          const coveredCategories = new Set<string>();
          card.benefits.forEach((b) => {
            spending.forEach((s) => {
              if (CATEGORY_MATCH[s.category]?.includes(b.category)) coveredCategories.add(s.category);
            });
          });

          return (
            <div key={card.id}
              className={`rounded-2xl border-2 p-5 shadow-sm ${keep ? "border-emerald-200 bg-emerald-50/40" : "border-amber-200 bg-amber-50/40"}`}>
              {/* 헤더 */}
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="text-[10px] font-normal text-gray-400 mb-0.5">{card.issuer}</div>
                  <div className="text-sm font-normal text-gray-900 leading-snug">{card.name}</div>
                </div>
                <span className={`text-xs font-normal px-2.5 py-1 rounded-lg border ${
                  keep ? "bg-emerald-100 border-emerald-300 text-emerald-700" : "bg-amber-100 border-amber-300 text-amber-700"
                }`}>
                  {keep ? "✅ 유지 추천" : "🔄 갈아타기"}
                </span>
              </div>

              {/* 혜택 활용도 미터 */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-normal text-gray-500">혜택 활용도</span>
                  <span className="text-xs font-normal" style={{ color: keep ? "#10B981" : "#F97316" }}>{fit}%</span>
                </div>
                <div className="relative h-2.5 bg-gray-100 rounded-full overflow-visible">
                  <div className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${fit}%`, backgroundColor: keep ? "#10B981" : "#F97316" }} />
                  {/* 60% 기준선 */}
                  <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-0.5 h-4 bg-gray-400 rounded-full"
                    style={{ left: "60%" }} />
                  <div className="absolute -top-4 text-[9px] text-gray-400 font-normal"
                    style={{ left: "60%", transform: "translateX(-50%)" }}>60%</div>
                </div>
              </div>

              {/* 혜택별 상태 리스트 */}
              <div className="space-y-2">
                {card.benefits.map((b) => {
                  const matchedSpend = spending.find((s) => CATEGORY_MATCH[s.category]?.includes(b.category));
                  const isActive = !!matchedSpend;
                  const isOverlap = overlapCategories.includes(b.category);

                  return (
                    <div key={b.category} className="flex items-center gap-2">
                      <span className="text-sm flex-shrink-0">{b.icon}</span>
                      <span className={`flex-1 text-[11px] font-normal truncate ${
                        isActive ? "text-gray-800" : "text-gray-400"
                      }`}>
                        {b.category}
                      </span>
                      {isOverlap ? (
                        <span className="text-[9px] font-normal px-1.5 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-600">겹침</span>
                      ) : isActive ? (
                        <div className="flex items-center gap-1">
                          <span className="text-[9px] font-normal px-1.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600">활용중</span>
                          <span className="text-[9px] font-normal text-gray-400">
                            {Math.round((matchedSpend!.amount / 10000))}만원
                          </span>
                        </div>
                      ) : (
                        <span className="text-[9px] font-normal px-1.5 py-0.5 rounded-full bg-gray-100 border border-gray-200 text-gray-400">미사용</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── 중복 혜택 경고 ── */}
      {overlapCategories.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-normal text-amber-800 mb-1">중복 혜택 경고</div>
              <p className="text-xs font-normal text-amber-700 mb-3">
                선택한 카드들 사이에 아래 혜택 카테고리가 겹쳐요. 중복 혜택은 실제로 한 카드에서만 적용되므로 카드 교체를 고려해보세요.
              </p>
              <div className="flex flex-wrap gap-2">
                {overlapCategories.map((cat) => (
                  <span key={cat} className="text-xs font-normal px-3 py-1 rounded-full bg-amber-100 border border-amber-300 text-amber-700">
                    {CATEGORY_COLOR[cat] && (
                      <span className="inline-block w-2 h-2 rounded-full mr-1.5"
                        style={{ backgroundColor: CATEGORY_COLOR[cat] }} />
                    )}
                    {cat} 혜택 중복
                  </span>
                ))}
              </div>
              {overlapCategories.map((cat) => {
                const cardsWithCat = selectedCards.filter((c) => c.benefits.some((b) => b.category === cat));
                return (
                  <p key={cat} className="text-[11px] font-normal text-amber-600 mt-2">
                    · <strong>{cat}</strong>: {cardsWithCat.map((c) => c.name).join(", ")} — 동일 혜택 보유로 한 카드 교체 시 낭비 없음
                  </p>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── 갈아타기 추천 카드 3종 ── */}
      {alternatives.length > 0 && switchCards.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-4 h-4" style={{ color: ACCENT }} />
            <span className="text-sm font-normal text-gray-800">갈아타기 추천 카드</span>
            <span className="text-[10px] font-normal text-gray-400 ml-1">적합도 − 중복혜택 페널티 순 정렬</span>
          </div>
          <div className="space-y-3">
            {alternatives.map(({ card, fit, score }, idx) => {
              const isTop = idx === 0;
              const meta = issuerMeta[card.issuer];
              return (
                <div key={card.id}
                  className={`flex items-center gap-4 p-4 rounded-xl border-2 transition-all ${
                    isTop ? "border-gray-900 shadow-sm" : "border-gray-200"
                  }`}>
                  {/* 순위 */}
                  <div className="w-6 flex-shrink-0 text-center">
                    <span className="text-sm">{["🥇", "🥈", "🥉"][idx]}</span>
                  </div>

                  {/* 발급사 칩 */}
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-[10px] font-normal flex-shrink-0"
                    style={{ backgroundColor: meta?.color ?? card.color }}>
                    {meta?.logo}
                  </div>

                  {/* 카드 정보 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-normal text-gray-400">{card.issuer}</span>
                      {isTop && (
                        <span className="text-[9px] font-normal px-2 py-0.5 rounded-full bg-gray-900 text-white">최적 대안</span>
                      )}
                    </div>
                    <div className="text-sm font-normal text-gray-900 truncate mb-1.5">{card.name}</div>
                    <div className="flex flex-wrap gap-1">
                      {card.benefits.map((b) => {
                        const matched = isBenefitMatched(b.category, spending);
                        return (
                          <span key={b.category}
                            className={`text-[9px] font-normal px-1.5 py-0.5 rounded-full border ${
                              matched ? "bg-emerald-50 border-emerald-200 text-emerald-600" : "bg-gray-50 border-gray-200 text-gray-400"
                            }`}>
                            {b.category}
                          </span>
                        );
                      })}
                    </div>
                  </div>

                  {/* 점수 */}
                  <div className="flex flex-col items-end gap-0.5 flex-shrink-0">
                    <span className="text-sm font-normal text-emerald-600">{fit}%</span>
                    <span className="text-[10px] font-normal text-gray-400">적합도</span>
                    {score !== fit && (
                      <span className="text-[9px] font-normal text-amber-500">보정: {score}점</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── 추천 카드 조합 ── */}
      {recommendedCombo.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4" style={{ color: ACCENT }} />
            <span className="text-sm font-normal text-gray-800">이 조합을 추천해요</span>
          </div>
          <div className="flex items-center gap-4 flex-wrap mb-4">
            {recommendedCombo.map((card, idx) => (
              <div key={card.id} className="flex items-center gap-3">
                {idx > 0 && <span className="text-gray-300 text-lg">+</span>}
                <div className="flex flex-col items-center gap-1.5">
                  <CardVisual card={card} size="sm" />
                  <div className="text-center">
                    <div className="text-[9px] text-gray-400 font-normal">{card.issuer}</div>
                    <div className="text-[10px] text-gray-700 font-normal max-w-[100px] truncate">{card.name}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 조합 분석 */}
          <div className={`rounded-xl p-4 border ${comboOverlap.length === 0 ? "bg-emerald-50/50 border-emerald-100" : "bg-amber-50/50 border-amber-100"}`}>
            <div className="flex items-start gap-2">
              {comboOverlap.length === 0 ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
              )}
              <div>
                <p className={`text-xs font-normal ${comboOverlap.length === 0 ? "text-emerald-700" : "text-amber-700"}`}>
                  {comboOverlap.length === 0
                    ? "조합 내 중복 혜택 없음 — 각 카드의 혜택이 서로 겹치지 않아 최대 효율로 사용 가능해요."
                    : `조합 내 ${comboOverlap.join(", ")} 혜택이 일부 겹쳐요. 주요 사용 카드를 정해두면 효율이 높아집니다.`}
                </p>
                {/* 조합 커버리지 */}
                {(() => {
                  const coveredSpend = new Set<string>();
                  recommendedCombo.forEach((card) => {
                    card.benefits.forEach((b) => {
                      spending.forEach((s) => {
                        if (CATEGORY_MATCH[s.category]?.includes(b.category)) coveredSpend.add(s.category);
                      });
                    });
                  });
                  const comboPct = Math.round(
                    spending.filter((s) => coveredSpend.has(s.category)).reduce((a, s) => a + s.amount, 0) / total * 100
                  );
                  return (
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-[10px] font-normal text-gray-500">조합 커버리지</span>
                      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden max-w-[120px]">
                        <div className="h-full rounded-full" style={{ width: `${comboPct}%`, backgroundColor: ACCENT }} />
                      </div>
                      <span className="text-[10px] font-normal" style={{ color: ACCENT }}>{comboPct}%</span>
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 처음부터 버튼 */}
      <div className="flex justify-start pt-2">
        <button onClick={onBack}
          className="flex items-center gap-1.5 text-xs font-normal text-gray-400 hover:text-gray-600 transition-all">
          <RefreshCw className="w-3.5 h-3.5" />카드 다시 선택
        </button>
      </div>
    </div>
  );
}

// ═══ 메인 ════════════════════════════════════════
export function CardAnalysis() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [spending, setSpending] = useState<SpendingItem[] | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const toggleCard = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 3 ? [...prev, id] : prev,
    );
  };

  return (
    <div className="bg-[#E9EEF5] min-h-screen">
      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[860px] mx-auto px-6 py-6">
          <h1 className="text-2xl font-normal text-gray-900 mb-0.5">카드 판별</h1>
          <p className="text-gray-500 text-sm font-normal">
            내 소비 패턴을 분석해 지금 가진 카드가 맞는지, 더 좋은 카드로 갈아타야 하는지 알려드려요
          </p>
        </div>
      </div>

      <div className="max-w-[860px] mx-auto px-6 py-8 space-y-6">
        {/* 스텝 네비게이터 */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm px-8 py-5">
          <StepNav
            step={step}
            hasData={!!spending}
            hasCards={selectedIds.length > 0}
            onStepClick={(s) => setStep(s as 1 | 2 | 3)}
          />
        </div>

        {/* 스텝별 콘텐츠 */}
        <div>
          {step === 1 && (
            <SpendingStep
              spending={spending}
              onDataLoad={(d) => setSpending(d)}
              onNext={() => setStep(2)}
            />
          )}
          {step === 2 && spending && (
            <CardSelectStep
              spending={spending}
              selectedIds={selectedIds}
              onToggle={toggleCard}
              onNext={() => setStep(3)}
            />
          )}
          {step === 3 && spending && selectedIds.length > 0 && (
            <ResultStep
              spending={spending}
              selectedIds={selectedIds}
              onBack={() => setStep(2)}
            />
          )}
        </div>
      </div>
    </div>
  );
}