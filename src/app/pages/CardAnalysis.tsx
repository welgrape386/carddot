import { useState } from 'react';
import { Link } from 'react-router';
import { ChevronRight, CheckCircle, AlertTriangle, TrendingUp, TrendingDown, Star, ArrowRight, RotateCcw, Zap, BarChart2, Target, DollarSign, Sparkles } from 'lucide-react';
import { cards, userProfile } from '../data/mockData';
import { CardVisual } from '../components/CardVisual';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

const STEP_LABELS = ['카드 선택', '소비 입력', '분석 결과'];

interface SpendingInput {
  category: string;
  icon: string;
  monthly: number;
}

export function CardAnalysis() {
  const [step, setStep] = useState(0);
  const [selectedCardId, setSelectedCardId] = useState<number>(userProfile.currentCard);
  const [spending, setSpending] = useState<SpendingInput[]>([
    { category: '카페/디저트', icon: '☕', monthly: 85000 },
    { category: '배달/음식', icon: '🍕', monthly: 120000 },
    { category: '교통', icon: '🚌', monthly: 65000 },
    { category: '쇼핑', icon: '🛒', monthly: 90000 },
    { category: '통신', icon: '📱', monthly: 27000 },
    { category: '편의점', icon: '🏪', monthly: 35000 },
    { category: '스트리밍', icon: '📺', monthly: 15000 },
  ]);

  const selectedCard = cards.find(c => c.id === selectedCardId) || cards[0];

  // Compute analysis
  const totalMonthly = spending.reduce((s, sp) => s + sp.monthly, 0);

  const computeUtilization = () => {
    let total = 0;
    let gained = 0;
    selectedCard.benefits.forEach(benefit => {
      const matchSpending = spending.find(s => s.category.includes(benefit.category) || benefit.category.includes(s.category.split('/')[0]));
      const spend = matchSpending?.monthly || 0;
      if (spend > 0) {
        total += benefit.maxMonthly;
        gained += Math.min(benefit.maxMonthly, spend * benefit.discountRate / 100);
      }
    });
    return total > 0 ? (gained / total) * 100 : 0;
  };

  const utilizationRate = computeUtilization();
  const meetsCondition = totalMonthly >= selectedCard.minSpending;
  const costEfficiency = selectedCard.annualFee === 0 ? 100 : Math.min(100, (selectedCard.maxBenefit * 12 / selectedCard.annualFee) * 10);

  const spendingFit = spending.filter(s => {
    return selectedCard.benefits.some(b => b.category.toLowerCase().includes(s.category.split('/')[0].toLowerCase()) || s.category.toLowerCase().includes(b.category.toLowerCase()));
  }).length / Math.max(1, spending.length) * 100;

  const overallScore = Math.round((utilizationRate * 0.4 + costEfficiency * 0.3 + spendingFit * 0.3));
  const recommendation: 'keep' | 'switch' = overallScore >= 70 ? 'keep' : 'switch';

  // Best alternative cards
  const alternativeCards = cards
    .filter(c => c.id !== selectedCardId)
    .map(c => {
      let fit = 0;
      spending.forEach(s => {
        if (c.benefits.some(b => b.category.toLowerCase().includes(s.category.split('/')[0].toLowerCase()))) {
          fit += (s.monthly / totalMonthly) * 100;
        }
      });
      return { ...c, fit };
    })
    .sort((a, b) => b.fit - a.fit)
    .slice(0, 3);

  const radarData = [
    { subject: '혜택활용도', A: Math.round(utilizationRate), fullMark: 100 },
    { subject: '소비패턴적합', A: Math.round(spendingFit), fullMark: 100 },
    { subject: '비용효율', A: Math.round(costEfficiency), fullMark: 100 },
    { subject: '실적충족', A: meetsCondition ? 90 : 40, fullMark: 100 },
    { subject: '종합만족도', A: selectedCard.rating * 20, fullMark: 100 },
  ];

  const benefitBarData = spending.map(sp => {
    const matchBenefit = selectedCard.benefits.find(b =>
      b.category.toLowerCase().includes(sp.category.split('/')[0].toLowerCase()) ||
      sp.category.toLowerCase().includes(b.category.toLowerCase())
    );
    const earned = matchBenefit ? Math.min(matchBenefit.maxMonthly, sp.monthly * matchBenefit.discountRate / 100) : 0;
    return {
      name: sp.icon + ' ' + sp.category.split('/')[0],
      지출: sp.monthly,
      혜택: Math.round(earned),
    };
  });

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* Header */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-[1280px] mx-auto px-6 py-6">
          <h1 className="text-2xl text-gray-900 mb-1">카드 판별</h1>
          <p className="text-gray-500 text-sm">현재 카드가 나에게 맞는지 분석해드려요</p>

          {/* Progress */}
          <div className="mt-5 flex items-center gap-0 max-w-md">
            {STEP_LABELS.map((label, i) => (
              <div key={i} className="flex items-center flex-1 last:flex-none">
                <div className={`flex items-center gap-2 ${i <= step ? '' : 'opacity-40'}`}>
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    i < step ? 'bg-[#0ABFA3] text-white' : i === step ? 'bg-[#1B3D7B] text-white' : 'bg-gray-200 text-gray-500'
                  }`}>
                    {i < step ? <CheckCircle className="w-4 h-4" /> : i + 1}
                  </div>
                  <span className={`text-xs font-medium ${i === step ? 'text-[#1B3D7B]' : 'text-gray-400'}`}>{label}</span>
                </div>
                {i < STEP_LABELS.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-2 ${i < step ? 'bg-[#0ABFA3]' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8">
        {/* Step 0: Card Selection */}
        {step === 0 && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-2xl border border-gray-100 p-8">
              <h2 className="text-xl text-gray-900 mb-2">현재 사용하는 카드를 선택해주세요</h2>
              <p className="text-gray-500 text-sm mb-6">현재 주로 사용 중인 신용카드 또는 체크카드를 선택해주세요</p>

              <div className="grid grid-cols-2 gap-3 mb-6">
                {cards.map(card => (
                  <button
                    key={card.id}
                    onClick={() => setSelectedCardId(card.id)}
                    className={`flex items-center gap-3 p-4 border-2 rounded-xl transition-all text-left ${
                      selectedCardId === card.id
                        ? 'border-[#1B3D7B] bg-[#1B3D7B]/3'
                        : 'border-gray-100 hover:border-gray-200'
                    }`}
                  >
                    <CardVisual card={card} size="sm" />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-gray-400">{card.issuer}</div>
                      <div className="text-sm font-medium text-gray-900 truncate">{card.name}</div>
                      <div className="text-xs text-gray-500 mt-0.5">연회비 {card.annualFee === 0 ? '무료' : `${card.annualFee.toLocaleString()}원`}</div>
                    </div>
                    {selectedCardId === card.id && (
                      <CheckCircle className="w-5 h-5 text-[#1B3D7B] flex-shrink-0" />
                    )}
                  </button>
                ))}
              </div>

              <button
                onClick={() => setStep(1)}
                disabled={!selectedCardId}
                className="w-full py-3 bg-[#1B3D7B] text-white rounded-xl font-medium hover:bg-[#162f5f] transition-all flex items-center justify-center gap-2 disabled:opacity-40"
              >
                다음 단계 <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Spending Input */}
        {step === 1 && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-2xl border border-gray-100 p-8">
              <div className="flex items-center gap-3 mb-6">
                <CardVisual card={selectedCard} size="sm" />
                <div>
                  <div className="text-xs text-gray-400">{selectedCard.issuer}</div>
                  <div className="text-sm font-semibold text-gray-900">{selectedCard.name}</div>
                </div>
              </div>

              <h2 className="text-xl text-gray-900 mb-2">월간 소비 패턴을 입력해주세요</h2>
              <p className="text-gray-500 text-sm mb-6">카테고리별 월 평균 소비 금액을 입력하면 혜택 활용도를 분석해드려요</p>

              <div className="space-y-4 mb-6">
                {spending.map((sp, i) => (
                  <div key={sp.category}>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                        <span>{sp.icon}</span> {sp.category}
                      </label>
                      <span className="text-sm font-semibold text-[#1B3D7B]">{sp.monthly.toLocaleString()}원</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min={0}
                        max={500000}
                        step={5000}
                        value={sp.monthly}
                        onChange={e => {
                          const updated = [...spending];
                          updated[i] = { ...sp, monthly: Number(e.target.value) };
                          setSpending(updated);
                        }}
                        className="flex-1 accent-[#1B3D7B]"
                      />
                      <input
                        type="number"
                        value={sp.monthly}
                        onChange={e => {
                          const updated = [...spending];
                          updated[i] = { ...sp, monthly: Number(e.target.value) };
                          setSpending(updated);
                        }}
                        className="w-28 px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-right focus:outline-none focus:border-[#1B3D7B] transition-all"
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl mb-6">
                <span className="text-sm text-gray-600">월 총 소비 합계</span>
                <span className="font-bold text-gray-900">{totalMonthly.toLocaleString()}원</span>
              </div>

              <div className="flex gap-3">
                <button onClick={() => setStep(0)} className="flex-1 py-3 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 transition-all text-sm font-medium">
                  이전
                </button>
                <button
                  onClick={() => setStep(2)}
                  className="flex-2 flex-1 py-3 bg-[#1B3D7B] text-white rounded-xl font-medium hover:bg-[#162f5f] transition-all flex items-center justify-center gap-2"
                >
                  분석하기 <Zap className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Analysis Result */}
        {step === 2 && (
          <div>
            {/* Result Banner */}
            <div className={`rounded-2xl p-8 mb-6 ${recommendation === 'keep' ? 'bg-green-50 border-2 border-green-200' : 'bg-orange-50 border-2 border-orange-200'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${recommendation === 'keep' ? 'bg-green-100' : 'bg-orange-100'}`}>
                    {recommendation === 'keep'
                      ? <CheckCircle className="w-8 h-8 text-green-600" />
                      : <AlertTriangle className="w-8 h-8 text-orange-500" />
                    }
                  </div>
                  <div>
                    <div className={`text-xs font-bold mb-1 ${recommendation === 'keep' ? 'text-green-600' : 'text-orange-500'}`}>
                      {recommendation === 'keep' ? '✅ 유지 추천' : '🔄 갈아타기 추천'}
                    </div>
                    <h2 className="text-2xl text-gray-900">
                      {recommendation === 'keep'
                        ? '현재 카드를 계속 사용하세요!'
                        : '더 적합한 카드가 있어요'
                      }
                    </h2>
                    <p className={`text-sm mt-1 ${recommendation === 'keep' ? 'text-green-700' : 'text-orange-700'}`}>
                      {recommendation === 'keep'
                        ? `${selectedCard.name}은 내 소비패턴과 잘 맞고, 혜택 활용도가 높습니다.`
                        : `자주 사용하는 소비처에서 혜택이 부족하고, 더 적합한 카드가 있습니다.`
                      }
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500 mb-1">종합 점수</div>
                  <div className={`text-5xl font-black ${recommendation === 'keep' ? 'text-green-600' : 'text-orange-500'}`}>
                    {overallScore}
                  </div>
                  <div className="text-sm text-gray-400">/ 100점</div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-6 mb-6">
              {/* Score Details */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Target className="w-4 h-4 text-[#1B3D7B]" />
                  항목별 점수
                </h3>
                <div className="space-y-4">
                  {[
                    { label: '혜택 활용도', value: Math.round(utilizationRate), color: 'bg-[#1B3D7B]', desc: `소비패턴에서 혜택 활용 ${Math.round(utilizationRate)}%` },
                    { label: '소비패턴 적합도', value: Math.round(spendingFit), color: 'bg-teal-500', desc: '주요 소비처 혜택 일치도' },
                    { label: '비용 효율성', value: Math.round(costEfficiency), color: 'bg-purple-500', desc: '연회비 대비 혜택 가치' },
                    { label: '전월실적 충족', value: meetsCondition ? 90 : 40, color: meetsCondition ? 'bg-green-500' : 'bg-orange-400', desc: meetsCondition ? '조건 충족 중' : '조건 미달 (낮은 소비 시)' },
                  ].map(item => (
                    <div key={item.label}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-600">{item.label}</span>
                        <span className="text-xs font-bold text-gray-900">{item.value}점</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full mb-0.5">
                        <div className={`h-2 ${item.color} rounded-full transition-all`} style={{ width: `${item.value}%` }} />
                      </div>
                      <div className="text-[10px] text-gray-400">{item.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Radar Chart */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-[#1B3D7B]" />
                  종합 분석 차트
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#f3f4f6" />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: '#6B7280' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar name="점수" dataKey="A" stroke="#1B3D7B" fill="#1B3D7B" fillOpacity={0.2} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              {/* Monthly Benefit */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-[#1B3D7B]" />
                  혜택 현황
                </h3>
                <div className="space-y-3 mb-4">
                  {[
                    { label: '이달 예상 혜택', value: `${Math.round(selectedCard.maxBenefit * utilizationRate / 100).toLocaleString()}원`, color: 'text-green-600', bg: 'bg-green-50' },
                    { label: '연간 예상 절감', value: `${Math.round(selectedCard.maxBenefit * utilizationRate / 100 * 12 - selectedCard.annualFee).toLocaleString()}원`, color: 'text-[#1B3D7B]', bg: 'bg-blue-50' },
                    { label: '혜택 대비 연회비', value: selectedCard.annualFee === 0 ? '무료 ✅' : `${((selectedCard.annualFee / (selectedCard.maxBenefit * 12)) * 100).toFixed(1)}%`, color: 'text-purple-600', bg: 'bg-purple-50' },
                  ].map(item => (
                    <div key={item.label} className={`p-3 rounded-xl ${item.bg}`}>
                      <div className="text-xs text-gray-500 mb-0.5">{item.label}</div>
                      <div className={`font-bold ${item.color}`}>{item.value}</div>
                    </div>
                  ))}
                </div>

                <div className="p-3 bg-gray-50 rounded-xl">
                  <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
                    <CardVisual card={selectedCard} size="sm" className="!w-8 !h-5 !rounded" />
                    <span className="truncate">{selectedCard.name}</span>
                  </div>
                  <div className="text-xs text-gray-400">전월실적 {selectedCard.minSpending === 0 ? '무실적' : `${(selectedCard.minSpending/10000).toFixed(0)}만원`} / 연회비 {selectedCard.annualFee === 0 ? '무료' : `${selectedCard.annualFee.toLocaleString()}원`}</div>
                </div>
              </div>
            </div>

            {/* Category Benefit Chart */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
              <h3 className="font-semibold text-gray-900 mb-4">카테고리별 혜택 현황</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={benefitBarData} barGap={4}>
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v: number, name: string) => [`${v.toLocaleString()}원`, name]} />
                  <Bar dataKey="지출" fill="#E5E7EB" radius={[4, 4, 0, 0]} barSize={20} />
                  <Bar dataKey="혜택" fill="#1B3D7B" radius={[4, 4, 0, 0]} barSize={20} />
                </BarChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-4 mt-2 justify-center">
                <div className="flex items-center gap-1.5 text-xs text-gray-500"><div className="w-3 h-3 bg-gray-200 rounded" /> 월 지출</div>
                <div className="flex items-center gap-1.5 text-xs text-gray-500"><div className="w-3 h-3 bg-[#1B3D7B] rounded" /> 혜택 금액</div>
              </div>
            </div>

            {/* Analysis Detail */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
              <h3 className="font-semibold text-gray-900 mb-4">
                {recommendation === 'keep' ? '유지를 추천하는 이유' : '갈아타기를 추천하는 이유'}
              </h3>
              <div className={`space-y-3 p-4 rounded-xl ${recommendation === 'keep' ? 'bg-green-50' : 'bg-orange-50'}`}>
                {recommendation === 'keep' ? [
                  '현재 카드의 주요 혜택 카테고리와 소비패턴이 잘 일치합니다.',
                  `전월실적(${selectedCard.minSpending === 0 ? '무실적' : `${(selectedCard.minSpending/10000).toFixed(0)}만원`})을 ${meetsCondition ? '충족하고 있어' : '어느 정도 충족할 수 있어'} 혜택을 온전히 받을 수 있습니다.`,
                  `연회비 대비 혜택 가치가 충분하여 교체 비용이 혜택을 초과합니다.`,
                ] : [
                  '주요 소비 카테고리(배달, 카페)에서 혜택이 부족합니다.',
                  `현재 소비 패턴 기준 월 예상 혜택이 ${Math.round(selectedCard.maxBenefit * utilizationRate / 100).toLocaleString()}원으로 낮습니다.`,
                  '소비패턴에 더 적합한 대안 카드가 존재합니다.',
                ].map((reason, i) => (
                  <div key={i} className={`flex items-start gap-2 text-sm ${recommendation === 'keep' ? 'text-green-800' : 'text-orange-800'}`}>
                    <span className="mt-0.5 flex-shrink-0">{recommendation === 'keep' ? '✅' : '⚠️'}</span>
                    {reason}
                  </div>
                ))}
              </div>
            </div>

            {/* Alternative Cards */}
            {recommendation === 'switch' && (
              <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
                <h3 className="font-semibold text-gray-900 mb-1 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-orange-500" />
                  추천 대안 카드
                </h3>
                <p className="text-gray-500 text-sm mb-4">내 소비패턴에 더 잘 맞는 카드입니다</p>
                <div className="grid grid-cols-3 gap-4">
                  {alternativeCards.map((card, i) => (
                    <div key={card.id} className="border border-gray-100 rounded-xl p-4 hover:border-orange-200 hover:shadow-sm transition-all">
                      <div className="flex items-center gap-1 mb-3">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${i === 0 ? 'bg-orange-100 text-orange-600' : 'bg-gray-100 text-gray-600'}`}>
                          #{i + 1} 추천
                        </span>
                        <span className="text-xs text-gray-400">적합도 {Math.round(card.fit)}%</span>
                      </div>
                      <div className="flex justify-center mb-3">
                        <CardVisual card={card} size="sm" />
                      </div>
                      <div className="text-xs text-gray-400 mb-0.5">{card.issuer}</div>
                      <div className="text-sm font-semibold text-gray-900 mb-2">{card.name}</div>
                      <div className="space-y-1 mb-3">
                        {card.benefits.slice(0, 2).map((b, bi) => (
                          <div key={bi} className="text-xs text-gray-600 flex items-center gap-1">
                            <span>{b.icon}</span> {b.category} {b.discountRate}% {b.type === 'cashback' ? '캐시백' : '할인'}
                          </div>
                        ))}
                      </div>
                      <div className="h-1 bg-gray-100 rounded-full mb-3">
                        <div className="h-1 bg-orange-400 rounded-full" style={{ width: `${Math.round(card.fit)}%` }} />
                      </div>
                      <Link
                        to={`/cards/${card.id}`}
                        className="block text-center py-2 bg-orange-500 text-white rounded-xl text-xs font-medium hover:bg-orange-600 transition-all"
                      >
                        상세보기 <ArrowRight className="w-3 h-3 inline" />
                      </Link>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setStep(0)}
                className="flex items-center gap-2 px-6 py-3 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 transition-all text-sm font-medium"
              >
                <RotateCcw className="w-4 h-4" /> 다시 분석하기
              </button>
              <Link to="/compare" className="flex items-center gap-2 px-6 py-3 border border-[#1B3D7B] text-[#1B3D7B] rounded-xl hover:bg-[#1B3D7B] hover:text-white transition-all text-sm font-medium">
                카드 비교하기
              </Link>
              <Link to="/cards" className="flex items-center gap-2 px-6 py-3 bg-[#1B3D7B] text-white rounded-xl hover:bg-[#162f5f] transition-all text-sm font-medium">
                카드 둘러보기 <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
