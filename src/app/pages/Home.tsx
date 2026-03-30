import { useState, useEffect, useRef } from 'react';
import { motion } from 'motion/react';
import { Link } from 'react-router';
import {
  ArrowRight, ChevronRight, Star, CreditCard, Zap,
  Crown, BarChart2,
} from 'lucide-react';
import { cards, issuerMeta } from '../data/mockData';
import { CardVisual } from '../components/CardVisual';

const issuers = Object.keys(issuerMeta);

const medalEmoji = ['👑', '🥈', '🥉'];
const medalBg = [
  'border-yellow-300 bg-yellow-50',
  'border-gray-300 bg-gray-50',
  'border-amber-300 bg-amber-50',
];

// 빠른 혜택 검색 카테고리
const quickCategories = [
  { key: '카페/베이커리', icon: '☕', color: '#795548', bg: '#fff8f5' },
  { key: '외식/배달',    icon: '🍕', color: '#e53935', bg: '#fff5f5' },
  { key: '쇼핑',        icon: '🛍️', color: '#8e24aa', bg: '#fdf5ff' },
  { key: '대중교통',    icon: '🚌', color: '#0288d1', bg: '#f0f9ff' },
  { key: '주유',        icon: '⛽', color: '#f57c00', bg: '#fff8f0' },
  { key: '통신',        icon: '📱', color: '#43a047', bg: '#f0faf0' },
  { key: '편의점',      icon: '🏪', color: '#00897b', bg: '#f0fffe' },
  { key: '항공/여행',   icon: '✈️', color: '#1B3D7B', bg: '#f0f4ff' },
  { key: '영화',        icon: '🎬', color: '#c62828', bg: '#fff5f5' },
  { key: '대형마트',    icon: '🏬', color: '#5e35b1', bg: '#f5f0ff' },
  { key: '무실적',      icon: '🎁', color: '#0ABFA3', bg: '#f0fffe' },
  { key: '무연회비',    icon: '💳', color: '#1B3D7B', bg: '#f0f4ff' },
];

export function Home() {
  const [activeIssuer, setActiveIssuer] = useState(issuers[0]);
  const [isSpread, setIsSpread] = useState(false);
  const heroCardRef = useRef<HTMLDivElement>(null);

  // IntersectionObserver: 뷰포트 진입 시 펼침, 나가면 접힘 → 재진입 시 다시 펼침
  useEffect(() => {
    const el = heroCardRef.current;
    if (!el) return;
    let timer: ReturnType<typeof setTimeout>;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          // 잠깐 접힌 상태 유지 후 펼치기
          timer = setTimeout(() => setIsSpread(true), 350);
        } else {
          clearTimeout(timer);
          setIsSpread(false);
        }
      },
      { threshold: 0.4 },
    );
    observer.observe(el);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, []);

  const rankedCards = cards
    .filter(c => c.issuer === activeIssuer)
    .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99))
    .slice(0, 3);

  const meta = issuerMeta[activeIssuer];

  return (
    <div className="bg-[#F8FAFC] min-h-screen">

      {/* ── Hero ── */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-[1280px] mx-auto px-6 py-20 flex items-center gap-16">
          <div className="flex-1 max-w-xl">
            <div className="inline-flex items-center gap-2 bg-[#1B3D7B]/8 text-[#1B3D7B] px-3 py-1.5 rounded-full text-sm font-bold mb-6">
              <Zap className="w-3.5 h-3.5" />
              2025년 3월 최신 카드 정보 업데이트
            </div>
            <h1 className="text-4xl text-gray-900 mb-5 leading-tight font-black">
              내 소비패턴에 딱 맞는<br />
              <span className="text-[#1B3D7B]">카드를 찾아드려요</span>
            </h1>
            <p className="text-gray-500 mb-8 leading-relaxed font-semibold">
              500개 이상의 신용·체크카드를 한눈에 비교하세요.<br />
              혜택 활용도와 소비패턴 분석으로 최적의 카드를 추천해드립니다.
            </p>
            <div className="flex items-center gap-3">
              <Link to="/cards" className="flex items-center gap-2 px-6 py-3 bg-[#1B3D7B] text-white rounded-xl hover:bg-[#162f5f] transition-all shadow-sm font-black">
                카드 조회하기 <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to="/analysis" className="flex items-center gap-2 px-6 py-3 border-2 border-gray-200 text-gray-700 rounded-xl hover:border-[#1B3D7B] hover:text-[#1B3D7B] transition-all font-black">
                카드 판별하기
              </Link>
            </div>
          </div>
          {/* 히어로 카드 3장 애니메이션 */}
          <div className="hidden lg:flex flex-1 justify-center items-center">
            <div ref={heroCardRef} className="relative w-96 h-72">
              {cards.slice(0, 3).map((card, i) => {
                // 더 극적인 부채꼴 펼침
                const spreadPos = [
                  { top: 55, left: -45, rotate: -18 }, // 뒤 카드 – 왼쪽으로
                  { top: 12, left: 28, rotate: 1 },     // 가운데 카드
                  { top: 55, left: 100, rotate: 20 },   // 앞 카드 – 오른쪽으로
                ][i];
                const stackedPos = { top: 28, left: 28, rotate: 0 };
                return (
                  <motion.div
                    key={card.id}
                    className="absolute"
                    style={{ zIndex: 3 - i }}
                    animate={
                      isSpread
                        ? { top: spreadPos.top, left: spreadPos.left, rotate: spreadPos.rotate, opacity: 1 }
                        : { top: stackedPos.top, left: stackedPos.left, rotate: stackedPos.rotate, opacity: 1 }
                    }
                    initial={{ top: stackedPos.top, left: stackedPos.left, rotate: 0, opacity: 0 }}
                    transition={{
                      type: 'spring',
                      stiffness: 95,
                      damping: 15,
                      delay: isSpread ? i * 0.10 : (2 - i) * 0.06,
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

      {/* ── 빠른 혜택 카테고리 탐색 ── */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-[1280px] mx-auto px-6 py-8">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-black text-gray-900">혜택별 빠른 카드 탐색</h2>
              <p className="text-sm text-gray-400 font-semibold mt-0.5">원하는 혜택 카테고리를 선택하면 해당 카드를 바로 확인하세요</p>
            </div>
          </div>
          <div className="grid grid-cols-12 gap-2.5">
            {quickCategories.map(cat => (
              <Link
                key={cat.key}
                to={`/cards?benefit=${encodeURIComponent(cat.key)}`}
                className="flex flex-col items-center gap-2 py-4 rounded-2xl border-2 border-transparent hover:border-gray-200 transition-all group cursor-pointer"
                style={{ backgroundColor: cat.bg }}
              >
                <span className="text-2xl">{cat.icon}</span>
                <span className="text-[11px] font-black text-gray-700 text-center leading-tight group-hover:text-gray-900">{cat.key}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── 카드사별 이번달 랭킹 ── */}
      <section className="max-w-[1280px] mx-auto px-6 py-12">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Crown className="w-5 h-5 text-yellow-500" />
            <div>
              <h2 className="text-xl text-gray-900 font-black">카드사별 이번 달 랭킹</h2>
              <p className="text-gray-500 text-sm font-semibold mt-0.5">2025년 3월 기준 · 조회수·발급수·리뷰 종합 집계</p>
            </div>
          </div>
          <Link to="/ranking" className="flex items-center gap-1 text-sm text-[#1B3D7B] hover:underline font-black">
            전체 보기 <ChevronRight className="w-4 h-4" />
          </Link>
        </div>

        {/* 카드사 탭 */}
        <div className="flex items-center gap-2 mb-5 flex-wrap">
          {issuers.map(issuer => (
            <button
              key={issuer}
              onClick={() => setActiveIssuer(issuer)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl border-2 text-sm font-black transition-all ${
                activeIssuer === issuer ? 'text-white border-transparent shadow-md' : 'border-gray-200 text-gray-600 bg-white hover:border-gray-300'
              }`}
              style={activeIssuer === issuer ? { backgroundColor: issuerMeta[issuer].color } : {}}
            >
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: activeIssuer === issuer ? 'rgba(255,255,255,0.7)' : issuerMeta[issuer].color }} />
              {issuer}
            </button>
          ))}
        </div>

        {/* 랭킹 패널 */}
        <div className="rounded-2xl border-2 overflow-hidden" style={{ borderColor: `${meta.color}30` }}>
          <div className="px-6 py-4 flex items-center justify-between" style={{ backgroundColor: meta.bg }}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-xs font-black" style={{ backgroundColor: meta.color }}>
                {meta.logo}
              </div>
              <div>
                <span className="font-black text-gray-900">{activeIssuer}</span>
                <span className="text-gray-400 text-xs font-bold ml-2">{meta.desc}</span>
              </div>
            </div>
            <Link to={`/cards?issuer=${encodeURIComponent(activeIssuer)}`} className="text-xs font-black flex items-center gap-1 hover:underline" style={{ color: meta.color }}>
              전체 카드 보기 <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="bg-white divide-y divide-gray-50">
            {rankedCards.map((card, idx) => (
              <Link key={card.id} to={`/cards/${card.id}`}>
                <div className="px-6 py-5 flex items-center gap-5 hover:bg-gray-50/60 transition-all group">
                  <div className={`flex-shrink-0 w-10 h-10 rounded-xl border-2 flex items-center justify-center text-base ${medalBg[idx]}`}>
                    {idx === 0 ? <span>{medalEmoji[0]}</span> : <span className="font-black text-gray-600">{idx + 1}</span>}
                  </div>
                  <div className="flex-shrink-0"><CardVisual card={card} size="sm" /></div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${card.type === 'credit' ? 'bg-blue-50 text-blue-600' : 'bg-purple-50 text-purple-600'}`}>
                        {card.type === 'credit' ? '신용' : '체크'}
                      </span>
                      {card.tags.slice(0, 2).map(tag => (
                        <span key={tag} className="text-[10px] font-bold bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{tag}</span>
                      ))}
                    </div>
                    <div className="text-sm font-black text-gray-900 group-hover:text-[#1B3D7B] transition-colors mb-1.5">{card.name}</div>
                    <div className="flex items-center gap-4 text-xs text-gray-500 font-bold">
                      <span>연회비 <span className={card.annualFee === 0 ? 'text-green-600 font-black' : 'text-gray-800 font-black'}>{card.annualFee === 0 ? '무료' : `${card.annualFee.toLocaleString()}원`}</span></span>
                      <span>전월실적 <span className="text-gray-800 font-black">{card.minSpending === 0 ? '무실적' : `${(card.minSpending / 10000).toFixed(0)}만원`}</span></span>
                      <span>월최대 <span className="text-[#1B3D7B] font-black">{(card.maxBenefit / 10000).toFixed(0)}만원 혜택</span></span>
                    </div>
                  </div>
                  <div className="hidden lg:flex flex-col gap-1.5 w-52">
                    {card.benefits.slice(0, 2).map((b, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-xs text-gray-600 font-bold">
                        <span>{b.icon}</span>
                        <span>{b.category} <span className="text-[#1B3D7B] font-black">{b.discountRate}%</span> {b.type === 'cashback' ? '캐시백' : b.type === 'point' ? '적립' : '할인'}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <div className="flex items-center gap-1 justify-end mb-0.5">
                      <Star className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
                      <span className="text-sm font-black text-gray-800">{card.rating}</span>
                    </div>
                    <div className="text-[10px] text-gray-400 font-bold">{card.reviews.toLocaleString()}개 리뷰</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-[#1B3D7B] transition-colors flex-shrink-0" />
                </div>
              </Link>
            ))}
          </div>

          <div className="px-6 py-3 flex justify-center" style={{ backgroundColor: meta.bg }}>
            <Link to="/ranking" className="flex items-center gap-1.5 text-sm font-black hover:underline" style={{ color: meta.color }}>
              전체 카드사 랭킹 보기 <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── 카드 비교 CTA ── */}
      <section className="max-w-[1280px] mx-auto px-6 pb-10">
        <div className="bg-[#1B3D7B] rounded-3xl overflow-hidden">
          <div className="px-12 py-10 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <BarChart2 className="w-5 h-5 text-[#0ABFA3]" />
                <span className="text-white/70 text-sm font-bold">지금 바로 비교해보세요</span>
              </div>
              <h2 className="text-2xl text-white font-black mb-2">고민 중인 카드들, 한번에 비교하기</h2>
              <p className="text-white/60 font-semibold text-sm">공통 혜택부터 차별화 혜택까지 항목별로 나란히 확인하세요</p>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              <div className="flex -space-x-3">
                {cards.slice(0, 3).map(c => (
                  <div key={c.id} className="w-12 h-8 rounded-md overflow-hidden border-2 border-white/30 shadow">
                    <div className="w-full h-full" style={{ background: c.gradient }} />
                  </div>
                ))}
              </div>
              <Link to="/compare" className="flex items-center gap-2 px-6 py-3 bg-[#0ABFA3] text-white rounded-xl hover:bg-[#099d86] transition-all font-black text-sm">
                카드 비교 시작 <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="max-w-[1280px] mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded flex items-center justify-center" style={{ backgroundColor: '#4E40EF' }}>
                <CreditCard className="w-3 h-3 text-white" />
              </div>
              <span className="font-black" style={{ color: '#4E40EF' }}>카드닷</span>
            </div>
            <p className="text-gray-400 text-xs font-semibold">© 2025 카드닷. 본 서비스는 금융상품 비교 정보 제공 목적으로 운영됩니다.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}