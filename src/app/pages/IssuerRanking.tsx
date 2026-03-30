import { useState } from 'react';
import { Link } from 'react-router';
import { Star, Crown, ChevronRight, CreditCard, Filter } from 'lucide-react';
import { cards, issuerMeta } from '../data/mockData';
import { CardVisual } from '../components/CardVisual';

const issuers = Object.keys(issuerMeta);

const medalColors = ['text-yellow-500', 'text-gray-400', 'text-amber-600'];
const medalBg    = ['bg-yellow-50 border-yellow-200', 'bg-gray-50 border-gray-200', 'bg-amber-50 border-amber-200'];
const medals     = ['👑', '🥈', '🥉'];

export function IssuerRanking() {
  const [selectedIssuer, setSelectedIssuer] = useState<string>('전체');
  const [cardType, setCardType] = useState<'all' | 'credit' | 'debit'>('all');

  const displayIssuers = selectedIssuer === '전체' ? issuers : [selectedIssuer];

  const getRankedCards = (issuer: string) =>
    cards
      .filter(c => c.issuer === issuer)
      .filter(c => cardType === 'all' || c.type === cardType)
      .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99))
      .slice(0, 3);

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1280px] mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-2">
            <Crown className="w-6 h-6 text-yellow-500" />
            <h1 className="text-2xl font-bold text-gray-900">카드사별 이번 달 랭킹</h1>
          </div>
          <p className="text-gray-500 font-medium ml-9">2025년 3월 기준 · 조회수·발급수·리뷰 종합 집계</p>
        </div>
      </div>

      {/* 필터 바 */}
      <div className="bg-white border-b border-gray-100 sticky top-16 z-30 shadow-sm">
        <div className="max-w-[1280px] mx-auto px-6 py-3 flex items-center gap-4">
          <Filter className="w-4 h-4 text-gray-400 flex-shrink-0" />

          {/* 카드 종류 */}
          <div className="flex rounded-xl overflow-hidden border border-gray-200">
            {(['all', 'credit', 'debit'] as const).map(t => (
              <button
                key={t}
                onClick={() => setCardType(t)}
                className={`px-4 py-1.5 text-sm font-bold transition-all ${
                  cardType === t ? 'bg-[#1B3D7B] text-white' : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                {t === 'all' ? '전체' : t === 'credit' ? '신용카드' : '체크카드'}
              </button>
            ))}
          </div>

          <div className="w-px h-5 bg-gray-200" />

          {/* 카드사 선택 */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              onClick={() => setSelectedIssuer('전체')}
              className={`px-3 py-1.5 rounded-lg text-sm font-bold transition-all ${
                selectedIssuer === '전체'
                  ? 'bg-[#1B3D7B] text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              전체
            </button>
            {issuers.map(issuer => (
              <button
                key={issuer}
                onClick={() => setSelectedIssuer(issuer)}
                className={`px-3 py-1.5 rounded-lg text-sm font-bold transition-all flex items-center gap-1.5 ${
                  selectedIssuer === issuer
                    ? 'text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
                style={
                  selectedIssuer === issuer
                    ? { backgroundColor: issuerMeta[issuer].color }
                    : {}
                }
              >
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: issuerMeta[issuer].color }}
                />
                {issuer.replace('카드', '').replace('NH농협', 'NH')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 컨텐츠 */}
      <div className="max-w-[1280px] mx-auto px-6 py-8 space-y-8">
        {displayIssuers.map(issuer => {
          const ranked = getRankedCards(issuer);
          if (ranked.length === 0) return null;
          const meta = issuerMeta[issuer];

          return (
            <div key={issuer} className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
              {/* 카드사 헤더 */}
              <div
                className="px-6 py-4 flex items-center justify-between"
                style={{ backgroundColor: meta.bg, borderBottom: `2px solid ${meta.color}20` }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-white text-sm font-black shadow-sm"
                    style={{ backgroundColor: meta.color }}
                  >
                    {meta.logo}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-gray-900">{issuer}</h2>
                      <span className="text-xs font-semibold text-gray-400">{meta.desc}</span>
                    </div>
                    <div className="text-xs text-gray-500 font-semibold mt-0.5">
                      이번 달 인기 카드 TOP {ranked.length}
                    </div>
                  </div>
                </div>
                <Link
                  to={`/cards?issuer=${encodeURIComponent(issuer)}`}
                  className="flex items-center gap-1 text-sm font-bold hover:underline transition-colors"
                  style={{ color: meta.color }}
                >
                  전체 카드보기 <ChevronRight className="w-4 h-4" />
                </Link>
              </div>

              {/* 카드 목록 */}
              <div className="divide-y divide-gray-50">
                {ranked.map((card, idx) => (
                  <Link key={card.id} to={`/cards/${card.id}`}>
                    <div className="px-6 py-5 flex items-center gap-5 hover:bg-gray-50/70 transition-all group">
                      {/* 순위 */}
                      <div className={`flex-shrink-0 w-10 h-10 rounded-xl border-2 flex items-center justify-center text-lg font-black ${medalBg[idx]}`}>
                        {idx === 0 ? (
                          <span>{medals[0]}</span>
                        ) : (
                          <span className={`text-sm font-black ${medalColors[idx]}`}>{idx + 1}</span>
                        )}
                      </div>

                      {/* 카드 이미지 */}
                      <div className="flex-shrink-0">
                        <CardVisual card={card} size="sm" />
                      </div>

                      {/* 카드 정보 */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${card.type === 'credit' ? 'bg-blue-50 text-blue-600' : 'bg-purple-50 text-purple-600'}`}>
                            {card.type === 'credit' ? '신용' : '체크'}
                          </span>
                          {card.tags.slice(0, 2).map(tag => (
                            <span key={tag} className="text-[10px] font-bold bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                        <div className="text-sm font-bold text-gray-900 group-hover:text-[#1B3D7B] transition-colors mb-1.5">
                          {card.name}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-gray-500 font-semibold">
                          <span>연회비 <span className={card.annualFee === 0 ? 'text-green-600 font-bold' : 'text-gray-700 font-bold'}>{card.annualFee === 0 ? '무료' : `${card.annualFee.toLocaleString()}원`}</span></span>
                          <span>전월실적 <span className="text-gray-700 font-bold">{card.minSpending === 0 ? '무실적' : `${(card.minSpending / 10000).toFixed(0)}만원`}</span></span>
                          <span>월최대 <span className="text-[#1B3D7B] font-bold">{(card.maxBenefit / 10000).toFixed(0)}만원 혜택</span></span>
                        </div>
                      </div>

                      {/* 대표 혜택 */}
                      <div className="hidden xl:flex flex-col gap-1 w-52">
                        {card.benefits.slice(0, 2).map((b, i) => (
                          <div key={i} className="flex items-center gap-1.5 text-xs text-gray-600 font-semibold">
                            <span>{b.icon}</span>
                            <span>{b.category} <span className="text-[#1B3D7B] font-bold">{b.discountRate}%</span> {b.type === 'cashback' ? '캐시백' : b.type === 'point' ? '적립' : '할인'}</span>
                          </div>
                        ))}
                      </div>

                      {/* 평점 + 화살표 */}
                      <div className="flex-shrink-0 flex items-center gap-3">
                        <div className="text-right">
                          <div className="flex items-center gap-1 justify-end mb-0.5">
                            <Star className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
                            <span className="text-sm font-bold text-gray-800">{card.rating}</span>
                          </div>
                          <div className="text-[10px] text-gray-400 font-semibold">{card.reviews.toLocaleString()}개 리뷰</div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-[#1B3D7B] transition-colors" />
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* 하단 안내 */}
      <div className="max-w-[1280px] mx-auto px-6 pb-12">
        <div className="flex items-center gap-2 text-xs text-gray-400 font-semibold justify-center">
          <CreditCard className="w-3.5 h-3.5" />
          랭킹은 카드고릴라 조회수, 발급수, 사용자 리뷰를 종합하여 산정되며, 매월 1일 갱신됩니다.
        </div>
      </div>
    </div>
  );
}
