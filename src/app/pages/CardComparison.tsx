import { useMemo, useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router";
import { Plus, X, GitCompare, ChevronRight, Search, TrendingUp } from "lucide-react";
import { cards, Card } from "../data/mockData";
import { CardVisual } from "../components/CardVisual";
import { useAuth } from "../context/AuthContext";

const MAX_COMPARE = 3;

const typeLabel: Record<string, string> = {
  discount: "할인",
  cashback: "캐시백",
  point: "적립",
  special: "특별",
};

// ─── 모달: 카드 선택창 ────────────────────────────
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
        {/* 헤더 */}
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

        {/* 검색 */}
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

        {/* 카드 목록 */}
        <div className="overflow-y-auto flex-1">
          {filtered.length === 0 ? (
            <div className="py-12 text-center text-gray-400 font-normal text-sm">
              검색 결과가 없습니다
            </div>
          ) : (
            filtered.map((c) => (
              <button
                key={c.id}
                onClick={() => onSelect(c.id)}
                className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-[#6667AA]/5 transition-all border-b border-gray-50 last:border-b-0"
              >
                <CardVisual card={c} size="sm" />
                <div className="flex-1 text-left min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span
                      className={`text-[10px] font-normal px-1.5 py-0.5 rounded ${
                        c.type === "credit"
                          ? "bg-blue-50 text-blue-600"
                          : "bg-purple-50 text-purple-600"
                      }`}
                    >
                      {c.type === "credit" ? "신용" : "체크"}
                    </span>
                    <span className="text-[10px] text-gray-400 font-normal">
                      {c.issuer}
                    </span>
                  </div>
                  <div className="text-sm font-normal text-gray-900 truncate">
                    {c.name}
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-[10px] text-gray-400 font-normal">
                      연회비{" "}
                      <span
                        className={
                          c.annualFee === 0 ? "text-green-600" : "text-gray-600"
                        }
                      >
                        {c.annualFee === 0
                          ? "무료"
                          : `${c.annualFee.toLocaleString()}원`}
                      </span>
                    </span>
                    <span className="text-[10px] text-gray-400 font-normal">
                      월최대{" "}
                      <span className="text-[#6667AA]">
                        {(c.maxBenefit / 10000).toFixed(0)}만원
                      </span>
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

// ─── 비교 테이블 행 ────────────────────────────────
function CompareRow({
  label,
  values,
  highlight = false,
  isSection = false,
  colCount,
}: {
  label: React.ReactNode;
  values?: React.ReactNode[];
  highlight?: boolean;
  isSection?: boolean;
  colCount: number;
}) {
  if (isSection) {
    return (
      <div
        className="grid border-b border-gray-200"
        style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}
      >
        <div
          className={`col-span-${colCount + 1} px-4 py-2.5 flex items-center gap-2`}
          style={{ gridColumn: `1 / -1` }}
        >
          {label}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`grid border-b border-gray-100 ${highlight ? "bg-[#6667AA]/[0.04]" : ""}`}
      style={{ gridTemplateColumns: `200px repeat(${colCount}, 1fr)` }}
    >
      <div className="px-4 py-3 flex items-center border-r border-gray-100">
        <span className="text-xs font-normal text-gray-500">{label}</span>
      </div>
      {values?.map((val, i) => (
        <div
          key={i}
          className="px-4 py-3 flex items-start border-r border-gray-100 last:border-r-0"
        >
          {val}
        </div>
      ))}
    </div>
  );
}

export function CardComparison() {
  const [searchParams] = useSearchParams();
  const { addRecentlyCompared } = useAuth();
  const initialIds =
    searchParams.get("cards")?.split(",").map(Number).filter(Boolean) || [];

  const [selectedIds, setSelectedIds] = useState<number[]>(
    initialIds.length > 0 ? initialIds.slice(0, MAX_COMPARE) : [1, 3],
  );
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerSlot, setPickerSlot] = useState<number | null>(null); // null = add new

  const selectedCards = selectedIds
    .map((id) => cards.find((c) => c.id === id))
    .filter(Boolean) as Card[];

  const removeCard = (id: number) =>
    setSelectedIds((prev) => prev.filter((i) => i !== id));

  const openPicker = (slot: number | null) => {
    setPickerSlot(slot);
    setPickerOpen(true);
  };

  const handlePickerSelect = (newId: number) => {
    if (pickerSlot !== null) {
      // Replace existing slot
      setSelectedIds((prev) => {
        const next = [...prev];
        next[pickerSlot] = newId;
        return next;
      });
    } else {
      // Add new
      setSelectedIds((prev) =>
        prev.length >= MAX_COMPARE || prev.includes(newId)
          ? prev
          : [...prev, newId],
      );
    }
    setPickerOpen(false);
    setPickerSlot(null);
  };

  // 비교에서 제외할 ID 목록 (현재 슬롯 카드 포함/제외 처리)
  const pickerExcludeIds = useMemo(() => {
    if (pickerSlot !== null) {
      // 현재 슬롯 카드를 제외한 나머지 선택된 카드들
      return selectedIds.filter((_, i) => i !== pickerSlot);
    }
    return selectedIds;
  }, [selectedIds, pickerSlot]);

  // ─── 혜택 분석 ───────────────────────────────────
  const allCategories = useMemo(
    () =>
      Array.from(
        new Set(
          selectedCards.flatMap((c) => c.benefits.map((b) => b.category)),
        ),
      ),
    [selectedCards],
  );

  // 최근 비교 카드 기록 (2장 이상 선택 시)
  useEffect(() => {
    if (selectedIds.length >= 2) {
      addRecentlyCompared(selectedIds);
    }
  }, [selectedIds]);

  const getBenefit = (card: Card, category: string) =>
    card.benefits.find((b) => b.category === category) ?? null;

  const getBenefitCell = (card: Card, category: string) => {
    const b = getBenefit(card, category);
    if (!b) {
      return (
        <span className="text-gray-300 font-normal text-sm select-none">
          —
        </span>
      );
    }
    return (
      <div className="space-y-0.5">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-normal text-gray-800">
            {b.discountRate}%{" "}
            <span className="text-[#6667AA]">{typeLabel[b.type]}</span>
          </span>
        </div>
        <div className="text-[11px] text-gray-400 font-normal">
          최대 {(b.maxMonthly / 10000).toFixed(0)}만원
        </div>
        {b.condition !== "제한없음" && (
          <div className="text-[10px] text-gray-400 font-normal">
            {b.condition}
          </div>
        )}
      </div>
    );
  };

  const colCount = MAX_COMPARE;

  return (
    <div className="bg-[#E9EEF5] min-h-screen">
      {/* 피커 모달 */}
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

      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1280px] mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-normal text-gray-900 mb-0.5">
              카드 비교
            </h1>
            <p className="text-gray-500 text-sm font-normal">
              혜택·연회비·전월실적 기준으로 최대 3장을 나란히 비교해보세요
            </p>
          </div>

          <div className="flex items-center gap-2 text-sm font-normal text-gray-500 bg-slate-50 px-4 py-2 rounded-xl border border-gray-200">
            <GitCompare className="w-4 h-4" />
            <span className="text-[#6667AA]">{selectedCards.length}</span> /{" "}
            {MAX_COMPARE} 카드 선택됨
          </div>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8">
        {/* ─── 카드 슬롯 상단 ─────────────────── */}
        <div
          className="grid gap-3 mb-6"
          style={{
            gridTemplateColumns: `repeat(${MAX_COMPARE}, minmax(0, 1fr))`,
          }}
        >
          {Array.from({ length: MAX_COMPARE }).map((_, slotIdx) => {
            const card = selectedCards[slotIdx];
            return (
              <div key={slotIdx}>
                {card ? (
                  <div className="relative bg-white rounded-2xl border border-gray-200 shadow-sm px-4 py-5 flex flex-col items-center gap-3">
                    <button
                      onClick={() => removeCard(card.id)}
                      className="absolute top-3 right-3 w-6 h-6 rounded-full bg-gray-100 hover:bg-red-50 hover:text-red-500 text-gray-400 flex items-center justify-center transition-all"
                    >
                      <X className="w-3 h-3" />
                    </button>

                    <CardVisual card={card} size="lg" />

                    <div className="text-center">
                      <div className="text-[10px] text-gray-400 font-normal mb-0.5">
                        {card.issuer}
                      </div>
                      <div className="text-sm font-normal text-gray-900 leading-snug">
                        {card.name}
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
                    className="w-full min-h-[200px] border-2 border-dashed border-gray-200 hover:border-[#6667AA] rounded-2xl flex flex-col items-center justify-center gap-2 text-gray-400 hover:text-[#6667AA] transition-all bg-white"
                  >
                    <div className="w-10 h-10 rounded-full border-2 border-dashed border-current flex items-center justify-center">
                      <Plus className="w-5 h-5" />
                    </div>
                    <span className="text-sm font-normal">카드 추가</span>
                    <span className="text-xs font-normal opacity-70">
                      클릭해서 선택
                    </span>
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* ─── 비교 테이블 ─────────────────────── */}
        {selectedCards.length < 2 ? (
          <div className="text-center py-20 bg-white rounded-2xl border border-gray-100 shadow-sm">
            <GitCompare className="w-12 h-12 text-gray-200 mx-auto mb-3" />
            <p className="text-gray-500 font-normal">
              비교할 카드를 2개 이상 선택해주세요
            </p>
            <Link
              to="/cards"
              className="mt-4 inline-flex items-center gap-1 text-sm text-[#6667AA] hover:underline font-normal"
            >
              카드 둘러보기 <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {/* 테이블 헤더 (카드명 고정) */}
            <div
              className="grid border-b-2 border-gray-200 sticky top-16 z-20 bg-white"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div className="px-4 py-3 bg-slate-50 border-r border-gray-200 flex items-center">
                <span className="text-xs font-normal text-gray-400">
                  비교 항목
                </span>
              </div>
              {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                const card = selectedCards[idx];
                return (
                  <div
                    key={idx}
                    className="px-4 py-3 border-r border-gray-200 last:border-r-0 flex items-center justify-between gap-2"
                    style={
                      card ? { borderTop: `3px solid ${card.color}` } : {}
                    }
                  >
                    {card ? (
                      <div className="min-w-0">
                        <div className="text-[10px] text-gray-400 font-normal">
                          {card.issuer}
                        </div>
                        <div className="text-sm font-normal text-gray-900 truncate">
                          {card.name}
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-300 font-normal">
                        —
                      </span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* ── 기본 정보 섹션 ── */}
            <div
              className="grid bg-slate-50 border-b border-gray-200"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div
                className="px-4 py-2.5 flex items-center gap-2"
                style={{ gridColumn: "1 / -1" }}
              >
                <span className="text-xs font-normal text-gray-500">
                  📋 기본 정보
                </span>
              </div>
            </div>

            {/* 연회비 */}
            <div
              className="grid border-b border-gray-100"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div className="px-4 py-3 border-r border-gray-100 flex items-center">
                <span className="text-xs font-normal text-gray-500">연회비</span>
              </div>
              {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                const card = selectedCards[idx];
                return (
                  <div
                    key={idx}
                    className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center"
                  >
                    {card ? (
                      <span
                        className={`text-sm font-normal ${card.annualFee === 0 ? "text-green-600" : "text-gray-800"}`}
                      >
                        {card.annualFee === 0
                          ? "무료"
                          : `${card.annualFee.toLocaleString()}원`}
                      </span>
                    ) : (
                      <span className="text-gray-200 text-sm">—</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* 전월실적 */}
            <div
              className="grid border-b border-gray-100"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div className="px-4 py-3 border-r border-gray-100 flex items-center">
                <span className="text-xs font-normal text-gray-500">전월실적</span>
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
                        {card.minSpending === 0
                          ? "무실적"
                          : `${(card.minSpending / 10000).toFixed(0)}만원`}
                      </span>
                    ) : (
                      <span className="text-gray-200 text-sm">—</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* 월 최대 혜택 */}
            <div
              className="grid border-b border-gray-100 bg-[#6667AA]/[0.06]"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div className="px-4 py-3 border-r border-gray-100 flex items-center">
                <span className="text-xs font-normal text-gray-500">
                  월 최대 혜택
                </span>
              </div>
              {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                const card = selectedCards[idx];
                const maxCard = selectedCards.reduce((a, b) =>
                  a.maxBenefit > b.maxBenefit ? a : b,
                );
                const isMax = card && card.id === maxCard.id && selectedCards.length > 1;
                return (
                  <div
                    key={idx}
                    className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center gap-2"
                  >
                    {card ? (
                      <>
                        <span
                          className={`text-sm font-normal ${isMax ? "text-[#6667AA]" : "text-gray-800"}`}
                        >
                          {(card.maxBenefit / 10000).toFixed(0)}만원
                        </span>
                        {isMax && (
                          <span className="text-[10px] bg-[#6667AA] text-white px-1.5 py-0.5 rounded-full font-normal">
                            최대
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-gray-200 text-sm">—</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* 카드 종류 */}
            <div
              className="grid border-b border-gray-100"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div className="px-4 py-3 border-r border-gray-100 flex items-center">
                <span className="text-xs font-normal text-gray-500">카드 종류</span>
              </div>
              {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                const card = selectedCards[idx];
                return (
                  <div
                    key={idx}
                    className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center"
                  >
                    {card ? (
                      <span
                        className={`text-xs font-normal px-2 py-1 rounded ${card.type === "credit" ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600"}`}
                      >
                        {card.type === "credit" ? "신용카드" : "체크카드"}
                      </span>
                    ) : (
                      <span className="text-gray-200 text-sm">—</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* 카드 네트워크 */}
            <div
              className="grid border-b border-gray-100"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div className="px-4 py-3 border-r border-gray-100 flex items-center">
                <span className="text-xs font-normal text-gray-500">카드 네트워크</span>
              </div>
              {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                const card = selectedCards[idx];
                return (
                  <div
                    key={idx}
                    className="px-4 py-3 border-r border-gray-100 last:border-r-0 flex items-center"
                  >
                    {card ? (
                      <span className="text-sm font-normal text-gray-700">
                        {card.network}
                      </span>
                    ) : (
                      <span className="text-gray-200 text-sm">—</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* ── 혜택 총합 요약 ── */}
            <div
              className="grid bg-slate-50 border-b border-gray-200 border-t border-t-gray-200"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div
                className="px-4 py-2.5 flex items-center gap-2"
                style={{ gridColumn: "1 / -1" }}
              >
                <TrendingUp className="w-3.5 h-3.5 text-[#6667AA]" />
                <span className="text-xs font-normal text-[#6667AA]">
                  혜택 비교
                </span>
              </div>
            </div>

            {/* ── 전체 혜택 (공통 + 고유 통합) ── */}
            {allCategories.map((cat) => (
              <div
                key={cat}
                className="grid border-b border-gray-100"
                style={{
                  gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
                }}
              >
                <div className="px-4 py-3 border-r border-gray-100 flex items-start gap-1.5">
                  <span className="text-base leading-none mt-0.5">
                    {selectedCards
                      .flatMap((c) => c.benefits)
                      .find((b) => b.category === cat)?.icon ?? ""}
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
                      {card
                        ? getBenefitCell(card, cat)
                        : <span className="text-gray-200 text-sm">—</span>}
                    </div>
                  );
                })}
              </div>
            ))}

            {/* ── 이벤트 혜택 섹션 헤더 제거 후 신규 발급 혜택만 표시 ── */}
            <div
              className="grid border-b border-gray-100"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div className="px-4 py-3 border-r border-gray-100 flex items-center">
                <span className="text-xs font-normal text-gray-500">
                  신규 발급 혜택
                </span>
              </div>
              {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
                const card = selectedCards[idx];
                return (
                  <div
                    key={idx}
                    className="px-4 py-3 border-r border-gray-100 last:border-r-0"
                  >
                    {card ? (
                      card.eventBenefits.length > 0 ? (
                        <ul className="space-y-1">
                          {card.eventBenefits.map((e, i) => (
                            <li
                              key={i}
                              className="text-xs text-gray-700 font-normal flex items-start gap-1"
                            >
                              <span className="text-green-500 mt-0.5">✓</span>
                              {e}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-xs text-gray-300 font-normal">
                          없음
                        </span>
                      )
                    ) : (
                      <span className="text-gray-200 text-sm">—</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* ── 바로가기 ── */}
            <div
              className="grid"
              style={{
                gridTemplateColumns: `200px repeat(${colCount}, 1fr)`,
              }}
            >
              <div className="px-4 py-4 border-r border-gray-100 flex items-center">
                <span className="text-xs font-normal text-gray-400">
                  카드 상세
                </span>
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
                        to={`/cards/${card.id}`}
                        className="flex items-center gap-1 text-xs text-[#6667AA] hover:underline font-normal"
                      >
                        상세 보기 <ChevronRight className="w-3 h-3" />
                      </Link>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}