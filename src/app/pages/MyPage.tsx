import { useState } from 'react';
import { Link } from 'react-router';
import { User, CreditCard, Heart, Clock, BarChart2, Settings, Bell, ChevronRight, Star, Edit2, Trash2, Plus, RefreshCw, TrendingUp, Wallet } from 'lucide-react';
import { cards, userProfile } from '../data/mockData';
import { CardVisual } from '../components/CardVisual';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

const spendingData = userProfile.spendingPattern.map(s => ({
  subject: s.category.replace('/디저트', '').replace('/음식', ''),
  A: s.monthlyAmount / 1000,
}));

export function MyPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'favorites' | 'history' | 'settings'>('overview');
  const [favorites, setFavorites] = useState<number[]>(userProfile.favoriteCards);
  const [editMode, setEditMode] = useState(false);
  const [nickname, setNickname] = useState(userProfile.nickname);

  const favoriteCards = cards.filter(c => favorites.includes(c.id));
  const recentlyViewed = cards.filter(c => userProfile.recentlyViewed.includes(c.id));
  const currentCard = cards.find(c => c.id === userProfile.currentCard);

  const removeFavorite = (id: number) => setFavorites(prev => prev.filter(f => f !== id));
  const addFavorite = (id: number) => setFavorites(prev => [...prev, id]);

  const tabs = [
    { key: 'overview', label: '개요', icon: BarChart2 },
    { key: 'favorites', label: '즐겨찾기', icon: Heart },
    { key: 'history', label: '히스토리', icon: Clock },
    { key: 'settings', label: '설정', icon: Settings },
  ];

  const barData = userProfile.spendingPattern.map(s => ({
    name: s.icon + ' ' + s.category.split('/')[0],
    금액: s.monthlyAmount,
  }));

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* Profile Header */}
      <div className="bg-[#1B3D7B]">
        <div className="max-w-[1280px] mx-auto px-6 py-10">
          <div className="flex items-center gap-6">
            <div className="relative">
              <div className="w-20 h-20 rounded-2xl bg-white/20 flex items-center justify-center">
                <User className="w-10 h-10 text-white" />
              </div>
              <button className="absolute -bottom-1 -right-1 w-7 h-7 bg-[#0ABFA3] rounded-lg flex items-center justify-center shadow">
                <Edit2 className="w-3.5 h-3.5 text-white" />
              </button>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl text-white">{userProfile.name}</h1>
                <span className="text-xs bg-white/20 text-white px-2 py-0.5 rounded-full">{nickname}</span>
              </div>
              <p className="text-white/60 text-sm">{userProfile.email}</p>
              <p className="text-white/40 text-xs mt-1">가입일 {userProfile.joinDate}</p>
            </div>
            <div className="grid grid-cols-3 gap-6 text-center">
              <div>
                <div className="text-2xl text-white">{favoriteCards.length}</div>
                <div className="text-white/60 text-xs mt-0.5">즐겨찾기</div>
              </div>
              <div>
                <div className="text-2xl text-white">{recentlyViewed.length}</div>
                <div className="text-white/60 text-xs mt-0.5">최근 조회</div>
              </div>
              <div>
                <div className="text-2xl text-white">{userProfile.recentlyCompared.length}</div>
                <div className="text-white/60 text-xs mt-0.5">비교 횟수</div>
              </div>
            </div>
          </div>

          {/* Current Card */}
          {currentCard && (
            <div className="mt-6 p-4 bg-white/10 rounded-2xl flex items-center gap-4">
              <CardVisual card={currentCard} size="sm" />
              <div className="flex-1">
                <div className="text-white/60 text-xs mb-0.5">현재 사용 중인 카드</div>
                <div className="text-white font-semibold">{currentCard.name}</div>
                <div className="text-white/60 text-xs mt-0.5">{currentCard.issuer} · 연회비 {currentCard.annualFee.toLocaleString()}원</div>
              </div>
              <Link to="/analysis" className="flex items-center gap-1.5 px-4 py-2 bg-[#0ABFA3] text-white rounded-xl text-sm font-medium hover:bg-[#099d86] transition-all">
                카드 판별하기 <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Tab Nav */}
      <div className="bg-white border-b border-gray-100 sticky top-16 z-10">
        <div className="max-w-[1280px] mx-auto px-6">
          <div className="flex gap-0">
            {tabs.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-all ${
                  activeTab === tab.key
                    ? 'border-[#1B3D7B] text-[#1B3D7B]'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8">
        {/* Overview */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-3 gap-6">
            <div className="col-span-2 space-y-6">
              {/* Spending Analysis */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <h3 className="text-gray-900 font-semibold">월간 소비 패턴</h3>
                    <p className="text-gray-500 text-sm mt-0.5">최근 3개월 평균 소비 데이터</p>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Wallet className="w-4 h-4" />
                    총 <span className="font-semibold text-gray-900 mx-1">
                      {userProfile.spendingPattern.reduce((s, c) => s + c.monthlyAmount, 0).toLocaleString()}원
                    </span>/월
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={barData} barSize={28}>
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} tickFormatter={v => `${v/1000}만`} />
                    <Tooltip formatter={(v: number) => [`${v.toLocaleString()}원`, '소비금액']} />
                    <Bar dataKey="금액" fill="#1B3D7B" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-4 grid grid-cols-5 gap-2">
                  {userProfile.spendingPattern.map(s => (
                    <div key={s.category} className="text-center">
                      <div className="text-lg mb-0.5">{s.icon}</div>
                      <div className="text-xs text-gray-500">{s.category.split('/')[0]}</div>
                      <div className="text-xs font-semibold text-gray-900">{(s.monthlyAmount / 10000).toFixed(0)}만원</div>
                      <div className="mt-1 h-1 bg-gray-100 rounded-full">
                        <div className="h-1 bg-[#1B3D7B] rounded-full" style={{ width: `${s.percentage}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recently Viewed */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-gray-900 font-semibold">최근 본 카드</h3>
                  <Link to="/cards" className="text-xs text-[#1B3D7B] hover:underline flex items-center gap-1">
                    전체보기 <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
                <div className="flex gap-3 overflow-x-auto pb-2">
                  {recentlyViewed.map(card => (
                    <Link key={card.id} to={`/cards/${card.id}`} className="flex-shrink-0 flex flex-col items-center gap-2">
                      <CardVisual card={card} size="sm" />
                      <div className="text-xs text-gray-600 text-center w-28 truncate">{card.name}</div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              {/* Card Load */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h3 className="text-gray-900 font-semibold mb-4">카드 내역 불러오기</h3>
                <p className="text-gray-500 text-xs mb-4 leading-relaxed">
                  연결된 금융기관에서 카드 이용 내역을 가져와 소비 패턴을 자동 분석해드려요.
                </p>
                <div className="space-y-2 mb-4">
                  {['현대카드', '신한카드', 'KB국민카드'].map(bank => (
                    <div key={bank} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                      <div className="flex items-center gap-2">
                        <CreditCard className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-700">{bank}</span>
                      </div>
                      <button className="text-xs text-[#1B3D7B] font-medium hover:underline">연결</button>
                    </div>
                  ))}
                </div>
                <button className="w-full flex items-center justify-center gap-2 py-2.5 border-2 border-dashed border-gray-200 rounded-xl text-sm text-gray-500 hover:border-[#1B3D7B] hover:text-[#1B3D7B] transition-all">
                  <Plus className="w-4 h-4" />
                  카드사 추가 연결
                </button>
              </div>

              {/* Quick Stats */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h3 className="text-gray-900 font-semibold mb-4">이달의 혜택 현황</h3>
                <div className="space-y-3">
                  {[
                    { label: '이번달 할인 받은 금액', value: '28,400원', color: 'text-green-600', icon: TrendingUp },
                    { label: '누적 적립 포인트', value: '12,580P', color: 'text-[#1B3D7B]', icon: Star },
                    { label: '이달 남은 혜택 한도', value: '21,600원', color: 'text-orange-500', icon: Wallet },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <item.icon className="w-3.5 h-3.5 text-gray-400" />
                        {item.label}
                      </div>
                      <span className={`text-sm font-semibold ${item.color}`}>{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Compared */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h3 className="text-gray-900 font-semibold mb-4">최근 비교한 카드</h3>
                <div className="space-y-2">
                  {userProfile.recentlyCompared.map((group, i) => {
                    const groupCards = cards.filter(c => group.includes(c.id));
                    return (
                      <Link key={i} to="/compare" className="flex items-center gap-2 p-2.5 rounded-xl hover:bg-gray-50 transition-all">
                        <div className="flex -space-x-3">
                          {groupCards.slice(0, 3).map(card => (
                            <div key={card.id} className="w-7 h-7 rounded-full border-2 border-white flex items-center justify-center text-xs" style={{ background: card.gradient }}>
                            </div>
                          ))}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-gray-600 truncate">
                            {groupCards.map(c => c.name.split(' ').slice(-1)[0]).join(' vs ')}
                          </div>
                        </div>
                        <ChevronRight className="w-3 h-3 text-gray-400" />
                      </Link>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Favorites */}
        {activeTab === 'favorites' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-gray-900 font-semibold">즐겨찾기 카드 ({favoriteCards.length})</h3>
              <Link to="/compare" className="flex items-center gap-1.5 px-4 py-2 bg-[#1B3D7B] text-white rounded-xl text-sm font-medium">
                선택 카드 비교하기
              </Link>
            </div>
            {favoriteCards.length === 0 ? (
              <div className="text-center py-16">
                <Heart className="w-12 h-12 text-gray-200 mx-auto mb-3" />
                <p className="text-gray-500">즐겨찾기한 카드가 없어요</p>
                <Link to="/cards" className="mt-4 inline-block text-sm text-[#1B3D7B] hover:underline">카드 둘러보기</Link>
              </div>
            ) : (
              <div className="grid grid-cols-4 gap-4">
                {favoriteCards.map(card => (
                  <div key={card.id} className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-all">
                    <div className="p-5 bg-gray-50/50 flex justify-center">
                      <CardVisual card={card} size="md" />
                    </div>
                    <div className="p-4">
                      <div className="text-xs text-gray-400 mb-1">{card.issuer}</div>
                      <div className="text-sm font-semibold text-gray-900 mb-2">{card.name}</div>
                      <div className="flex flex-wrap gap-1 mb-3">
                        {card.tags.map(tag => (
                          <span key={tag} className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{tag}</span>
                        ))}
                      </div>
                      <div className="flex items-center justify-between">
                        <Link to={`/cards/${card.id}`} className="text-xs text-[#1B3D7B] hover:underline">상세보기</Link>
                        <button onClick={() => removeFavorite(card.id)} className="text-xs text-red-400 hover:text-red-600 flex items-center gap-1">
                          <Trash2 className="w-3 h-3" /> 삭제
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                {/* Add more */}
                <Link to="/cards" className="bg-white rounded-2xl border-2 border-dashed border-gray-200 hover:border-[#1B3D7B] flex flex-col items-center justify-center p-6 gap-2 text-gray-400 hover:text-[#1B3D7B] transition-all min-h-[200px]">
                  <Plus className="w-8 h-8" />
                  <span className="text-sm">카드 추가하기</span>
                </Link>
              </div>
            )}

            <div className="mt-8">
              <h3 className="text-gray-900 font-semibold mb-4">즐겨찾기 추가 추천</h3>
              <div className="grid grid-cols-4 gap-4">
                {cards.filter(c => !favorites.includes(c.id)).slice(0, 4).map(card => (
                  <div key={card.id} className="bg-white rounded-2xl border border-gray-100 p-4 flex flex-col items-center gap-3 hover:shadow-sm transition-all">
                    <CardVisual card={card} size="sm" />
                    <div className="text-center">
                      <div className="text-xs font-medium text-gray-900">{card.name}</div>
                      <div className="flex items-center gap-1 justify-center mt-1">
                        <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                        <span className="text-xs text-gray-500">{card.rating}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => addFavorite(card.id)}
                      className="flex items-center gap-1 px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-600 hover:border-[#1B3D7B] hover:text-[#1B3D7B] transition-all"
                    >
                      <Heart className="w-3 h-3" /> 즐겨찾기
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* History */}
        {activeTab === 'history' && (
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 text-gray-400" />
                <h3 className="text-gray-900 font-semibold">최근 본 카드</h3>
              </div>
              <div className="space-y-3">
                {recentlyViewed.map((card, i) => (
                  <Link key={card.id} to={`/cards/${card.id}`} className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-all">
                    <CardVisual card={card} size="sm" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900">{card.name}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{card.issuer} · 연회비 {card.annualFee === 0 ? '무료' : `${card.annualFee.toLocaleString()}원`}</div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                      <span className="text-xs text-gray-500">{card.rating}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <div className="flex items-center gap-2 mb-4">
                <BarChart2 className="w-4 h-4 text-gray-400" />
                <h3 className="text-gray-900 font-semibold">최근 비교 내역</h3>
              </div>
              <div className="space-y-3">
                {userProfile.recentlyCompared.map((group, i) => {
                  const groupCards = cards.filter(c => group.includes(c.id));
                  return (
                    <div key={i} className="p-4 border border-gray-100 rounded-xl hover:border-[#1B3D7B]/20 transition-all">
                      <div className="flex items-center gap-2 mb-3">
                        {groupCards.map(card => (
                          <CardVisual key={card.id} card={card} size="sm" />
                        ))}
                      </div>
                      <div className="text-xs text-gray-500 mb-2">
                        {groupCards.map(c => c.name).join(' vs ')}
                      </div>
                      <div className="flex gap-2">
                        <Link to="/compare" className="text-xs text-[#1B3D7B] hover:underline flex items-center gap-0.5">
                          다시 비교하기 <RefreshCw className="w-3 h-3" />
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Settings */}
        {activeTab === 'settings' && (
          <div className="max-w-2xl">
            <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-4">
              <h3 className="text-gray-900 font-semibold mb-6">개인정보 수정</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-2xl bg-[#1B3D7B]/10 flex items-center justify-center relative">
                    <User className="w-8 h-8 text-[#1B3D7B]" />
                    <button className="absolute -bottom-1 -right-1 w-6 h-6 bg-[#0ABFA3] rounded-full flex items-center justify-center">
                      <Edit2 className="w-3 h-3 text-white" />
                    </button>
                  </div>
                  <div className="text-sm text-gray-500">프로필 이미지 변경<br /><span className="text-xs">JPG, PNG, GIF (최대 5MB)</span></div>
                </div>
                {[
                  { label: '이름', value: userProfile.name, type: 'text' },
                  { label: '이메일', value: userProfile.email, type: 'email' },
                  { label: '닉네임', value: nickname, type: 'text' },
                ].map(field => (
                  <div key={field.label}>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">{field.label}</label>
                    <div className="relative">
                      <input
                        type={field.type}
                        defaultValue={field.value}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#1B3D7B] transition-all"
                      />
                      <button className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-[#1B3D7B]">
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
                <button className="w-full py-3 bg-[#1B3D7B] text-white rounded-xl hover:bg-[#162f5f] transition-all font-medium">
                  변경사항 저장
                </button>
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <h3 className="text-gray-900 font-semibold mb-4">알림 설정</h3>
              {[
                { label: '신규 카드 출시 알림', desc: '새로운 카드가 등록되면 알려드려요' },
                { label: '관심 카드 혜택 변경 알림', desc: '즐겨찾기 카드의 혜택이 변경되면 알려드려요' },
                { label: '마케팅 수신 동의', desc: '이벤트 및 혜택 정보를 받아보세요' },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between py-3 border-b border-gray-50 last:border-0">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{item.label}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{item.desc}</div>
                  </div>
                  <div className="w-10 h-6 bg-[#1B3D7B] rounded-full relative cursor-pointer">
                    <div className="absolute right-0.5 top-0.5 w-5 h-5 bg-white rounded-full shadow" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
