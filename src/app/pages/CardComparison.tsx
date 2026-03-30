import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Plus, X, Star, Check, Minus, GitCompare, Trophy, Info, ChevronRight } from 'lucide-react';
import { cards, Card } from '../data/mockData';
import { CardVisual } from '../components/CardVisual';

const MAX_COMPARE = 3;

const benefitTypeLabel: Record<string, string> = { discount: '할인', cashback: '캐시백', point: '포인트' };
const benefitTypeColor: Record<string, string> = {
  discount: 'text-blue-600 bg-blue-50',
  cashback: 'text-green-600 bg-green-50',
  point: 'text-purple-600 bg-purple-50',
};

// 섹션 구분선 컴포넌트
function SectionDivider({ label, badge, color }: { label: string; badge?: string; color: string }) {
  return (
    <div className={`flex items-center gap-2 px-6 py-3 border-t border-gray-100`} style={{ backgroundColor: color }}>
      <span className="text-xs font-black tracking-wide text-gray-700">{label}</span>
      {badge && (
        <span className="text-[10px] bg-white/70 text-gray-600 px-2 py-0.5 rounded-full font-bold border border-gray-200/60">
          {badge}
        </span>
      )}
    </div>
  );
}

export function CardComparison() {
  const [searchParams] = useSearchParams();
  const initialIds = searchParams.get('cards')?.split(',').map(Number).filter(Boolean) || [];

  const [selectedIds, setSelectedIds] = useState<number[]>(
    initialIds.length > 0 ? initialIds.slice(0, MAX_COMPARE) : [1, 3]
  );
  const [showPicker, setShowPicker] = useState<number | null>(null);

  const selectedCards = selectedIds.map(id => cards.find(c => c.id === id)).filter(Boolean) as Card[];

  const removeCard = (id: number) => setSelectedIds(prev => prev.filter(i => i !== id));
  const addCard = (id: number) => { setSelectedIds(prev => prev.length >= MAX_COMPARE || prev.includes(id) ? prev : [...prev, id]); setShowPicker(null); };
  const replaceCard = (slotIndex: number, newId: number) => { setSelectedIds(prev => { const next = [...prev]; next[slotIndex] = newId; return next; }); setShowPicker(null); };

  const allCategories = Array.from(new Set(selectedCards.flatMap(c => c.benefits.map(b => b.category))));
  const commonCategories = allCategories.filter(cat => selectedCards.every(c => c.benefits.some(b => b.category === cat)));
  const uniqueCategories = allCategories.filter(cat => !commonCategories.includes(cat));

  const getBenefit = (card: Card, category: string) => card.benefits.find(b => b.category === category);
  const getBestValue = (category: string, field: 'discountRate' | 'maxMonthly') => {
    const vals = selectedCards.map(c => getBenefit(c, category)?.[field] || 0);
    return Math.max(...vals);
  };

  const bestFee = Math.min(...selectedCards.map(c => c.annualFee));
  const bestSpending = Math.min(...selectedCards.map(c => c.minSpending));
  const bestBenefit = Math.max(...selectedCards.map(c => c.maxBenefit));
  const bestScore = Math.max(...selectedCards.map(c => c.score));
  const bestRating = Math.max(...selectedCards.map(c => c.rating));

  const numCols = selectedCards.length;

  // 컬럼 너비 스타일
  const colStyle = { width: `${100 / numCols}%` };

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1280px] mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-0.5">카드 비교</h1>
            <p className="text-gray-500 text-sm font-semibold">최대 3개 카드를 한눈에 비교해보세요</p>
          </div>
          <div className="flex items-center gap-2 text-sm font-bold text-gray-500 bg-gray-50 px-4 py-2 rounded-xl border border-gray-200">
            <GitCompare className="w-4 h-4" />
            <span className="text-[#1B3D7B]">{selectedCards.length}</span> / {MAX_COMPARE} 카드 선택됨
          </div>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8">
        {/* ── 카드 선택 슬롯 ── */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${MAX_COMPARE}, 1fr)` }}>
            {Array.from({ length: MAX_COMPARE }).map((_, slotIdx) => {
              const card = selectedCards[slotIdx];
              return (
                <div key={slotIdx} className="relative">
                  {card ? (
                    <div className="border-2 border-[#1B3D7B]/20 rounded-2xl p-5 flex flex-col items-center gap-3 bg-[#1B3D7B]/2">
                      <button onClick={() => removeCard(card.id)} className="absolute top-2 right-2 w-6 h-6 rounded-full bg-gray-100 hover:bg-red-50 hover:text-red-500 text-gray-400 flex items-center justify-center transition-all">
                        <X className="w-3 h-3" />
                      </button>
                      <CardVisual card={card} size="md" />
                      <div className="text-center">
                        <div className="text-xs text-gray-400 mb-0.5 font-semibold">{card.issuer}</div>
                        <div className="text-sm font-bold text-gray-900 leading-snug">{card.name}</div>
                        <div className="flex items-center gap-1 justify-center mt-1.5">
                          <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                          <span className="text-xs font-bold text-gray-600">{card.rating}</span>
                          <span className="text-xs text-gray-400 font-semibold">({card.reviews.toLocaleString()})</span>
                        </div>
                      </div>
                      <button onClick={() => setShowPicker(showPicker === slotIdx ? null : slotIdx)} className="text-xs text-[#1B3D7B] font-bold hover:underline">
                        카드 변경
                      </button>
                    </div>
                  ) : (
                    <button onClick={() => setShowPicker(showPicker === slotIdx ? null : slotIdx)} className="w-full h-full min-h-44 border-2 border-dashed border-gray-200 hover:border-[#1B3D7B] rounded-2xl flex flex-col items-center justify-center gap-2 text-gray-400 hover:text-[#1B3D7B] transition-all">
                      <Plus className="w-8 h-8" />
                      <span className="text-sm font-bold">카드 추가</span>
                      <span className="text-xs font-semibold">클릭해서 선택</span>
                    </button>
                  )}

                  {showPicker === slotIdx && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-100 rounded-2xl shadow-xl z-20 max-h-72 overflow-y-auto">
                      <div className="p-3 sticky top-0 bg-white border-b border-gray-50">
                        <p className="text-xs font-bold text-gray-500">카드 선택</p>
                      </div>
                      {cards.filter(c => !selectedIds.includes(c.id) || c.id === selectedCards[slotIdx]?.id).map(c => (
                        <button key={c.id} onClick={() => card ? replaceCard(slotIdx, c.id) : addCard(c.id)} className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-all">
                          <CardVisual card={c} size="sm" />
                          <div className="text-left">
                            <div className="text-[10px] text-gray-400 font-semibold">{c.issuer}</div>
                            <div className="text-sm font-bold text-gray-900">{c.name}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {selectedCards.length < 2 ? (
          <div className="text-center py-20">
            <GitCompare className="w-12 h-12 text-gray-200 mx-auto mb-3" />
            <p className="text-gray-500 font-semibold">비교할 카드를 2개 이상 선택해주세요</p>
            <Link to="/cards" className="mt-4 inline-flex items-center gap-1 text-sm text-[#1B3D7B] hover:underline font-bold">
              카드 둘러보기 <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <>
            {/* ── 우위 뱃지 ── */}
            <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: `repeat(${numCols}, 1fr)` }}>
              {selectedCards.map(card => {
                const pros: string[] = [];
                if (card.annualFee === bestFee) pros.push('최저 연회비');
                if (card.minSpending === bestSpending) pros.push('낮은 실적 조건');
                if (card.maxBenefit === bestBenefit) pros.push('최대 혜택');
                if (card.rating === bestRating) pros.push('최고 평점');
                return (
                  <div key={card.id} className="bg-white rounded-xl border border-gray-100 px-4 py-3 flex flex-wrap gap-1">
                    {pros.length > 0 ? pros.map(p => (
                      <span key={p} className="text-[10px] bg-[#1B3D7B]/8 text-[#1B3D7B] px-2 py-0.5 rounded-full font-bold">🏆 {p}</span>
                    )) : <span className="text-xs text-gray-400 font-semibold">-</span>}
                  </div>
                );
              })}
            </div>

            {/* ── 통합 비교 테이블 (한 번에 쫙) ── */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden mb-6">

              {/* 고정 컬럼 헤더 */}
              <div className="flex border-b-2 border-gray-100 bg-gray-50/50">
                <div className="w-44 flex-shrink-0 px-6 py-4 border-r border-gray-100">
                  <span className="text-xs font-black text-gray-400 uppercase tracking-wider">항목</span>
                </div>
                {selectedCards.map((card, idx) => (
                  <div key={card.id} className="flex-1 px-5 py-4 border-r border-gray-100 last:border-r-0">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-6 rounded-full" style={{ backgroundColor: ['#1B3D7B', '#0ABFA3', '#F97316'][idx] }} />
                      <div>
                        <div className="text-[10px] text-gray-400 font-bold">{card.issuer}</div>
                        <div className="text-xs font-black text-gray-800 leading-snug">{card.name}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* ══ 공통 혜택 (가장 위) ══ */}
              {commonCategories.length > 0 && (
                <>
                  <SectionDivider label="🔗 공통 혜택" badge={`${commonCategories.length}개 항목`} color="#f0fffe" />
                  {commonCategories.map((cat, i) => {
                    const bestRate = getBestValue(cat, 'discountRate');
                    const bestMax = getBestValue(cat, 'maxMonthly');
                    const icon = getBenefit(selectedCards[0], cat)?.icon || '';
                    return (
                      <div key={cat} className={`flex border-t border-gray-50 ${i % 2 !== 0 ? 'bg-gray-50/30' : ''}`}>
                        <div className="w-44 flex-shrink-0 px-6 py-4 border-r border-gray-50 flex items-center gap-2">
                          <span className="text-base">{icon}</span>
                          <span className="text-sm font-bold text-gray-700">{cat}</span>
                        </div>
                        {selectedCards.map(card => {
                          const b = getBenefit(card, cat);
                          if (!b) return (
                            <div key={card.id} className="flex-1 px-5 py-4 border-r border-gray-50 last:border-r-0 flex items-center text-gray-300">
                              <Minus className="w-4 h-4" />
                            </div>
                          );
                          const isTopRate = b.discountRate === bestRate;
                          const isTopMax = b.maxMonthly === bestMax;
                          return (
                            <div key={card.id} className={`flex-1 px-5 py-4 border-r border-gray-50 last:border-r-0 ${isTopRate ? 'bg-teal-50/40' : ''}`}>
                              <div className="flex items-center gap-2 mb-1.5">
                                <span className={`text-base font-black ${isTopRate ? 'text-teal-600' : 'text-gray-800'}`}>{b.discountRate}%</span>
                                {isTopRate && <Trophy className="w-3.5 h-3.5 text-yellow-500" />}
                                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${benefitTypeColor[b.type]}`}>{benefitTypeLabel[b.type]}</span>
                              </div>
                              <div className="text-xs text-gray-600 font-semibold">
                                월 최대 <span className={`font-black ${isTopMax ? 'text-teal-600' : 'text-gray-800'}`}>{b.maxMonthly.toLocaleString()}원</span>
                                {isTopMax && <span className="ml-1">🏆</span>}
                              </div>
                              <div className="text-[10px] text-gray-400 font-semibold mt-0.5">{b.condition}</div>
                              <div className="text-[10px] text-gray-500 font-semibold mt-0.5 leading-tight">{b.description}</div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </>
              )}

              {/* ══ 기본 정보 ══ */}
              <SectionDivider label="📋 기본 정보" color="#f8fafc" />
              {[
                {
                  label: '카드사',
                  icon: '🏦',
                  render: (card: Card) => <span className="text-sm font-bold text-gray-800">{card.issuer}</span>,
                  highlight: () => false,
                },
                {
                  label: '카드 종류',
                  icon: '💳',
                  render: (card: Card) => (
                    <span className={`text-xs font-bold px-2 py-1 rounded-lg ${card.type === 'credit' ? 'bg-blue-50 text-blue-700' : 'bg-purple-50 text-purple-700'}`}>
                      {card.type === 'credit' ? '신용카드' : '체크카드'}
                    </span>
                  ),
                  highlight: () => false,
                },
                {
                  label: '카드 네트워크',
                  icon: '🌐',
                  render: (card: Card) => <span className="text-sm font-bold text-gray-800">{card.network}</span>,
                  highlight: () => false,
                },
                {
                  label: '연회비',
                  icon: '💰',
                  render: (card: Card) => (
                    <div className="flex items-center gap-1.5">
                      {card.annualFee === bestFee && <Trophy className="w-3.5 h-3.5 text-yellow-500" />}
                      <span className={`text-sm font-black ${card.annualFee === 0 ? 'text-green-600' : card.annualFee === bestFee ? 'text-[#1B3D7B]' : 'text-gray-800'}`}>
                        {card.annualFee === 0 ? '무료' : `${card.annualFee.toLocaleString()}원`}
                      </span>
                    </div>
                  ),
                  highlight: (card: Card) => card.annualFee === bestFee,
                },
                {
                  label: '전월실적',
                  icon: '📊',
                  render: (card: Card) => (
                    <div className="flex items-center gap-1.5">
                      {card.minSpending === bestSpending && <Trophy className="w-3.5 h-3.5 text-yellow-500" />}
                      <span className={`text-sm font-black ${card.minSpending === 0 ? 'text-green-600' : card.minSpending === bestSpending ? 'text-[#1B3D7B]' : 'text-gray-800'}`}>
                        {card.minSpending === 0 ? '무실적' : `${(card.minSpending / 10000).toFixed(0)}만원`}
                      </span>
                    </div>
                  ),
                  highlight: (card: Card) => card.minSpending === bestSpending,
                },
                {
                  label: '월 최대 혜택',
                  icon: '🎁',
                  render: (card: Card) => (
                    <div className="flex items-center gap-1.5">
                      {card.maxBenefit === bestBenefit && <Trophy className="w-3.5 h-3.5 text-yellow-500" />}
                      <span className={`text-sm font-black ${card.maxBenefit === bestBenefit ? 'text-[#1B3D7B]' : 'text-gray-800'}`}>
                        {(card.maxBenefit / 10000).toFixed(0)}만원
                      </span>
                    </div>
                  ),
                  highlight: (card: Card) => card.maxBenefit === bestBenefit,
                },
                {
                  label: '혜택 점수',
                  icon: '🎯',
                  render: (card: Card) => (
                    <div className="flex items-center gap-2">
                      {card.score === bestScore && <Trophy className="w-3.5 h-3.5 text-yellow-500" />}
                      <div className="flex items-center gap-1.5">
                        <div className="w-20 h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${card.score}%`, backgroundColor: card.score === bestScore ? '#1B3D7B' : '#9ca3af' }} />
                        </div>
                        <span className={`text-sm font-black ${card.score === bestScore ? 'text-[#1B3D7B]' : 'text-gray-800'}`}>{card.score}점</span>
                      </div>
                    </div>
                  ),
                  highlight: (card: Card) => card.score === bestScore,
                },
                {
                  label: '사용자 평점',
                  icon: '⭐',
                  render: (card: Card) => (
                    <div className="flex items-center gap-1.5">
                      {card.rating === bestRating && <Trophy className="w-3.5 h-3.5 text-yellow-500" />}
                      <Star className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
                      <span className={`text-sm font-black ${card.rating === bestRating ? 'text-[#1B3D7B]' : 'text-gray-800'}`}>{card.rating}</span>
                      <span className="text-xs text-gray-400 font-semibold">({card.reviews.toLocaleString()})</span>
                    </div>
                  ),
                  highlight: (card: Card) => card.rating === bestRating,
                },
                {
                  label: '이벤트 혜택',
                  icon: '🎉',
                  render: (card: Card) => (
                    <div className="space-y-1">
                      {card.eventBenefits.map((ev, i) => (
                        <div key={i} className="text-[11px] text-gray-600 font-semibold bg-orange-50 px-2 py-1 rounded-lg border border-orange-100">{ev}</div>
                      ))}
                    </div>
                  ),
                  highlight: () => false,
                },
                {
                  label: '태그',
                  icon: '🏷️',
                  render: (card: Card) => (
                    <div className="flex flex-wrap gap-1">
                      {card.tags.map(tag => (
                        <span key={tag} className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-bold">{tag}</span>
                      ))}
                    </div>
                  ),
                  highlight: () => false,
                },
              ].map((row, i) => (
                <div key={row.label} className={`flex border-t border-gray-50 ${i % 2 !== 0 ? 'bg-gray-50/30' : ''}`}>
                  <div className="w-44 flex-shrink-0 px-6 py-4 border-r border-gray-50 flex items-center gap-2">
                    <span className="text-base">{row.icon}</span>
                    <span className="text-sm font-bold text-gray-600">{row.label}</span>
                  </div>
                  {selectedCards.map(card => (
                    <div key={card.id} className={`flex-1 px-5 py-4 border-r border-gray-50 last:border-r-0 flex items-center ${row.highlight(card) ? 'bg-[#1B3D7B]/3' : ''}`}>
                      {row.render(card)}
                    </div>
                  ))}
                </div>
              ))}

              {/* ══ 차별화 혜택 ══ */}
              {uniqueCategories.length > 0 && (
                <>
                  <SectionDivider label="⭐ 차별화 혜택" badge={`${uniqueCategories.length}개 항목`} color="#fff8f3" />
                  {uniqueCategories.map((cat, i) => {
                    const iconCard = selectedCards.find(c => getBenefit(c, cat));
                    const icon = iconCard ? getBenefit(iconCard, cat)?.icon : '';
                    return (
                      <div key={cat} className={`flex border-t border-gray-50 ${i % 2 !== 0 ? 'bg-gray-50/30' : ''}`}>
                        <div className="w-44 flex-shrink-0 px-6 py-4 border-r border-gray-50 flex items-center gap-2">
                          <span className="text-base">{icon}</span>
                          <span className="text-sm font-bold text-gray-700">{cat}</span>
                        </div>
                        {selectedCards.map(card => {
                          const b = getBenefit(card, cat);
                          return (
                            <div key={card.id} className={`flex-1 px-5 py-4 border-r border-gray-50 last:border-r-0 ${b ? 'bg-orange-50/30' : ''}`}>
                              {b ? (
                                <>
                                  <div className="flex items-center gap-2 mb-1.5">
                                    <span className="text-base font-black text-orange-600">{b.discountRate}%</span>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${benefitTypeColor[b.type]}`}>{benefitTypeLabel[b.type]}</span>
                                  </div>
                                  <div className="text-xs text-gray-600 font-semibold">월 최대 <span className="font-black text-gray-800">{b.maxMonthly.toLocaleString()}원</span></div>
                                  <div className="text-[10px] text-gray-400 font-semibold mt-0.5">{b.condition}</div>
                                  <div className="text-[10px] text-gray-500 font-semibold mt-0.5 leading-tight">{b.description}</div>
                                </>
                              ) : (
                                <div className="flex items-center gap-1 text-gray-300">
                                  <Minus className="w-4 h-4" />
                                  <span className="text-xs font-semibold">해당 없음</span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </>
              )}
            </div>

            {/* ── 비교 요약 ── */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h3 className="font-black text-gray-900 mb-5 flex items-center gap-2 text-base">
                <Trophy className="w-4 h-4 text-yellow-500" /> 비교 요약 및 추천
              </h3>
              <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${numCols}, 1fr)` }}>
                {selectedCards.map((card, idx) => {
                  const pros: string[] = [];
                  const cons: string[] = [];
                  if (card.annualFee === bestFee) pros.push('연회비가 가장 낮음');
                  if (card.minSpending === bestSpending) pros.push('전월실적 조건이 낮음');
                  if (card.maxBenefit === bestBenefit) pros.push('월 혜택이 가장 큼');
                  if (card.rating === bestRating) pros.push('사용자 만족도 최고');
                  if (card.score === bestScore) pros.push('혜택 점수 1위');
                  if (card.annualFee > bestFee) cons.push(`연회비 ${(card.annualFee - bestFee).toLocaleString()}원 더 비쌈`);
                  if (card.minSpending > bestSpending) cons.push('전월실적 조건이 높음');
                  const accentColors = ['border-[#1B3D7B]/30 bg-[#1B3D7B]/2', 'border-teal-200 bg-teal-50/30', 'border-orange-200 bg-orange-50/30'];

                  return (
                    <div key={card.id} className={`rounded-2xl border-2 p-5 ${accentColors[idx]}`}>
                      <div className="text-[10px] text-gray-400 font-bold mb-0.5">{card.issuer}</div>
                      <div className="text-sm font-black text-gray-900 mb-4 leading-snug">{card.name}</div>
                      <div className="space-y-1.5 mb-3">
                        {pros.map(p => (
                          <div key={p} className="flex items-start gap-1.5 text-xs text-green-700 font-semibold">
                            <Check className="w-3.5 h-3.5 text-green-500 mt-0.5 flex-shrink-0" /> {p}
                          </div>
                        ))}
                      </div>
                      {cons.length > 0 && (
                        <div className="space-y-1.5 mb-4">
                          {cons.map(c => (
                            <div key={c} className="flex items-start gap-1.5 text-xs text-gray-500 font-semibold">
                              <Info className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" /> {c}
                            </div>
                          ))}
                        </div>
                      )}
                      <Link to={`/cards/${card.id}`} className="mt-2 w-full block text-center py-2 border-2 border-[#1B3D7B] text-[#1B3D7B] rounded-xl text-xs font-black hover:bg-[#1B3D7B] hover:text-white transition-all">
                        상세 보기
                      </Link>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
