import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { Plus, X, GitCompare, ChevronRight } from "lucide-react";
import { cards, Card } from "../data/mockData";
import { CardVisual } from "../components/CardVisual";

const MAX_COMPARE = 3;

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5 border-b border-gray-100 last:border-b-0">
      <span className="text-xs text-gray-400 font-normal">{label}</span>
      <span className="text-sm text-gray-800 font-normal text-right">
        {value}
      </span>
    </div>
  );
}

function SectionTitle({
  title,
  tone = "default",
}: {
  title: string;
  tone?: "default" | "common" | "unique";
}) {
  const toneClass =
    tone === "common"
      ? "bg-[#6667AA]/14 text-[#5C5EA8]"
      : tone === "unique"
        ? "bg-orange-100/80 text-orange-700"
        : "bg-slate-100 text-gray-800";

  return (
    <div className={`px-5 py-3 border-b border-gray-100 ${toneClass}`}>
      <span className="text-sm font-normal">{title}</span>
    </div>
  );
}

function EmptyCompareColumn() {
  return (
    <div className="bg-white rounded-2xl border border-dashed border-gray-200 min-h-full" />
  );
}

export function CardComparison() {
  const [searchParams] = useSearchParams();
  const initialIds =
    searchParams.get("cards")?.split(",").map(Number).filter(Boolean) || [];

  const [selectedIds, setSelectedIds] = useState<number[]>(
    initialIds.length > 0 ? initialIds.slice(0, MAX_COMPARE) : [1, 3],
  );
  const [showPicker, setShowPicker] = useState<number | null>(null);

  const selectedCards = selectedIds
    .map((id) => cards.find((c) => c.id === id))
    .filter(Boolean) as Card[];

  const removeCard = (id: number) =>
    setSelectedIds((prev) => prev.filter((i) => i !== id));

  const addCard = (id: number) => {
    setSelectedIds((prev) =>
      prev.length >= MAX_COMPARE || prev.includes(id) ? prev : [...prev, id],
    );
    setShowPicker(null);
  };

  const replaceCard = (slotIndex: number, newId: number) => {
    setSelectedIds((prev) => {
      const next = [...prev];
      next[slotIndex] = newId;
      return next;
    });
    setShowPicker(null);
  };

  const allCategories = useMemo(
    () =>
      Array.from(
        new Set(
          selectedCards.flatMap((c) => c.benefits.map((b) => b.category)),
        ),
      ),
    [selectedCards],
  );

  const commonCategories = allCategories.filter((category) =>
    selectedCards.every((card) =>
      card.benefits.some((benefit) => benefit.category === category),
    ),
  );

  const distinctBenefitsByCard = selectedCards.map((card) =>
    card.benefits.filter(
      (benefit) => !commonCategories.includes(benefit.category),
    ),
  );

  return (
    <div className="bg-[#E9EEF5] min-h-screen">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1280px] mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-normal text-gray-900 mb-0.5">
              카드 비교
            </h1>
            <p className="text-gray-500 text-sm font-normal">
              최대 3개 카드를 핵심 정보만 간단하게 비교해보세요
            </p>
          </div>

          <div className="flex items-center gap-2 text-sm font-normal text-gray-500 bg-slate-50 px-4 py-2 rounded-xl border border-gray-200">
            <GitCompare className="w-4 h-4" />
            <span className="text-[#1B3D7B]">
              {selectedCards.length}
            </span> / {MAX_COMPARE} 카드 선택됨
          </div>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8">
        {/* 상단 카드 슬롯 */}
        <div
          className="grid gap-4 mb-5"
          style={{
            gridTemplateColumns: `repeat(${MAX_COMPARE}, minmax(0, 1fr))`,
          }}
        >
          {Array.from({ length: MAX_COMPARE }).map((_, slotIdx) => {
            const card = selectedCards[slotIdx];

            return (
              <div key={slotIdx} className="relative">
                {card ? (
                  <div className="relative rounded-2xl border border-gray-200 bg-white shadow-sm px-4 py-5 flex flex-col items-center gap-4 min-h-[245px]">
                    <button
                      onClick={() => removeCard(card.id)}
                      className="absolute top-3 right-3 w-6 h-6 rounded-full bg-gray-100 hover:bg-red-50 hover:text-red-500 text-gray-400 flex items-center justify-center transition-all"
                    >
                      <X className="w-3 h-3" />
                    </button>

                    <CardVisual card={card} size="lg" />

                    <button
                      onClick={() =>
                        setShowPicker(showPicker === slotIdx ? null : slotIdx)
                      }
                      className="text-xs text-[#1B3D7B] font-normal hover:underline"
                    >
                      카드 변경
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() =>
                      setShowPicker(showPicker === slotIdx ? null : slotIdx)
                    }
                    className="w-full min-h-[245px] border-2 border-dashed border-gray-200 hover:border-[#1B3D7B] rounded-2xl flex flex-col items-center justify-center gap-2 text-gray-400 hover:text-[#1B3D7B] transition-all bg-white"
                  >
                    <Plus className="w-8 h-8" />
                    <span className="text-sm font-normal">카드 추가</span>
                    <span className="text-xs font-normal">클릭해서 선택</span>
                  </button>
                )}

                {showPicker === slotIdx && (
                  <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-100 rounded-2xl shadow-xl z-20 max-h-72 overflow-y-auto">
                    <div className="p-3 sticky top-0 bg-white border-b border-gray-50">
                      <p className="text-xs font-normal text-gray-500">
                        카드 선택
                      </p>
                    </div>

                    {cards
                      .filter(
                        (c) =>
                          !selectedIds.includes(c.id) ||
                          c.id === selectedCards[slotIdx]?.id,
                      )
                      .map((c) => (
                        <button
                          key={c.id}
                          onClick={() =>
                            card ? replaceCard(slotIdx, c.id) : addCard(c.id)
                          }
                          className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-all"
                        >
                          <CardVisual card={c} size="sm" />
                          <div className="text-left">
                            <div className="text-[10px] text-gray-400 font-normal">
                              {c.issuer}
                            </div>
                            <div className="text-sm font-normal text-gray-900">
                              {c.name}
                            </div>
                          </div>
                        </button>
                      ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {selectedCards.length < 2 ? (
          <div className="text-center py-20 bg-white rounded-2xl border border-gray-100 shadow-sm">
            <GitCompare className="w-12 h-12 text-gray-200 mx-auto mb-3" />
            <p className="text-gray-500 font-normal">
              비교할 카드를 2개 이상 선택해주세요
            </p>
            <Link
              to="/cards"
              className="mt-4 inline-flex items-center gap-1 text-sm text-[#1B3D7B] hover:underline font-normal"
            >
              카드 둘러보기 <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <div
            className="grid gap-4"
            style={{
              gridTemplateColumns: `repeat(${MAX_COMPARE}, minmax(0, 1fr))`,
            }}
          >
            {Array.from({ length: MAX_COMPARE }).map((_, idx) => {
              const card = selectedCards[idx];

              if (!card) {
                return <EmptyCompareColumn key={`empty-${idx}`} />;
              }

              return (
                <div
                  key={card.id}
                  className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden"
                >
                  {/* 카드 이름 */}
                  <SectionTitle title="카드 이름" />
                  <div className="px-5 py-4">
                    <div className="text-base text-gray-900 font-normal leading-snug">
                      {card.name}
                    </div>
                  </div>

                  {/* 공통 혜택 */}
                  <SectionTitle title="공통 혜택" tone="common" />
                  <div className="px-5 py-4 space-y-2 bg-[#6667AA]/[0.07]">
                    {commonCategories.length > 0 ? (
                      commonCategories.map((category) => {
                        const benefit = card.benefits.find(
                          (b) => b.category === category,
                        );
                        if (!benefit) return null;

                        return (
                          <div
                            key={category}
                            className="rounded-xl px-3 py-3 border border-[#6667AA]/20 bg-white"
                          >
                            <div className="flex items-start gap-2">
                              <span className="text-base mt-0.5">
                                {benefit.icon}
                              </span>
                              <div className="min-w-0">
                                <div className="text-sm text-gray-900 font-normal">
                                  {benefit.category}
                                </div>
                                <div className="text-xs text-[#5C5EA8] mt-0.5 font-normal">
                                  {benefit.discountRate}%{" "}
                                  {benefit.type === "cashback"
                                    ? "캐시백"
                                    : benefit.type === "point"
                                      ? "적립"
                                      : "할인"}
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="text-sm text-gray-400 font-normal">
                        공통 혜택 없음
                      </div>
                    )}
                  </div>

                  {/* 이 카드만의 혜택 */}
                  <SectionTitle title="이 카드만의 혜택" tone="unique" />
                  <div className="px-5 py-4 space-y-2 bg-orange-50/70">
                    {distinctBenefitsByCard[idx].length > 0 ? (
                      distinctBenefitsByCard[idx].map((benefit, benefitIdx) => (
                        <div
                          key={`${benefit.category}-${benefitIdx}`}
                          className="rounded-xl px-3 py-3 border border-orange-200 bg-white"
                        >
                          <div className="flex items-start gap-2">
                            <span className="text-base mt-0.5">
                              {benefit.icon}
                            </span>
                            <div className="min-w-0">
                              <div className="text-sm text-gray-900 font-normal">
                                {benefit.category}
                              </div>
                              <div className="text-xs text-orange-600 mt-0.5 font-normal">
                                {benefit.discountRate}%{" "}
                                {benefit.type === "cashback"
                                  ? "캐시백"
                                  : benefit.type === "point"
                                    ? "적립"
                                    : "할인"}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-gray-400 font-normal">
                        차별화된 혜택 없음
                      </div>
                    )}
                  </div>

                  {/* 기본 정보 */}
                  <SectionTitle title="기본 정보" />
                  <div className="px-5 py-3 bg-slate-50/65">
                    <InfoRow label="카드사" value={card.issuer} />
                    <InfoRow
                      label="카드 종류"
                      value={card.type === "credit" ? "신용카드" : "체크카드"}
                    />
                    <InfoRow label="카드 네트워크" value={card.network} />
                    <InfoRow
                      label="연회비"
                      value={
                        card.annualFee === 0
                          ? "무료"
                          : `${card.annualFee.toLocaleString()}원`
                      }
                    />
                    <InfoRow
                      label="전월실적"
                      value={
                        card.minSpending === 0
                          ? "무실적"
                          : `${(card.minSpending / 10000).toFixed(0)}만원`
                      }
                    />
                    <InfoRow
                      label="월 최대 혜택"
                      value={`${(card.maxBenefit / 10000).toFixed(0)}만원`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
