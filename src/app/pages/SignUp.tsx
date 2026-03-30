import { useState } from 'react';
import { Link } from 'react-router';
import { Eye, EyeOff, CreditCard, Check, Lock, Mail, User, ChevronRight } from 'lucide-react';

export function SignUp() {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [showPw, setShowPw] = useState(false);
  const [agreed, setAgreed] = useState({ all: false, terms: false, privacy: false, marketing: false });
  const [step, setStep] = useState(1);

  const handleAllAgree = () => {
    const newVal = !agreed.all;
    setAgreed({ all: newVal, terms: newVal, privacy: newVal, marketing: newVal });
  };

  const handleAgree = (key: 'terms' | 'privacy' | 'marketing') => {
    const updated = { ...agreed, [key]: !agreed[key] };
    updated.all = updated.terms && updated.privacy && updated.marketing;
    setAgreed(updated);
  };

  const socialBtns = [
    {
      name: '카카오',
      bg: 'bg-[#FEE500]',
      textColor: 'text-[#3C1E1E]',
      border: 'border-[#FEE500]',
      icon: (
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M9 1.5C4.86 1.5 1.5 4.1 1.5 7.3C1.5 9.28 2.74 11.03 4.66 12.04L3.9 14.85C3.86 15 4.03 15.12 4.16 15.04L7.44 12.98C7.95 13.05 8.47 13.1 9 13.1C13.14 13.1 16.5 10.5 16.5 7.3C16.5 4.1 13.14 1.5 9 1.5Z" fill="#3C1E1E" />
        </svg>
      ),
    },
    {
      name: '구글',
      bg: 'bg-white',
      textColor: 'text-gray-700',
      border: 'border-gray-200',
      icon: (
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M16.51 9.19c0-.6-.05-1.17-.14-1.72H9v3.26h4.2c-.18.97-.73 1.79-1.56 2.34v1.94h2.53c1.48-1.36 2.34-3.37 2.34-5.82z" fill="#4285F4"/>
          <path d="M9 17c2.13 0 3.92-.7 5.23-1.9l-2.53-1.95c-.71.47-1.61.75-2.7.75-2.08 0-3.84-1.4-4.47-3.28H1.93v2.02A8 8 0 0 0 9 17z" fill="#34A853"/>
          <path d="M4.53 10.62A4.8 4.8 0 0 1 4.28 9c0-.57.1-1.12.25-1.62V5.36H1.93A8 8 0 0 0 1 9c0 1.29.31 2.51.93 3.64l2.6-2.02z" fill="#FBBC05"/>
          <path d="M9 3.86c1.17 0 2.22.4 3.05 1.2l2.29-2.29C12.91 1.43 11.12.71 9 .71A8 8 0 0 0 1.93 5.36L4.53 7.38C5.16 5.5 6.92 3.86 9 3.86z" fill="#EA4335"/>
        </svg>
      ),
    },
    {
      name: '네이버',
      bg: 'bg-[#03C75A]',
      textColor: 'text-white',
      border: 'border-[#03C75A]',
      icon: (
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M10.1 9.54L7.78 6H6v6h1.9V8.46L10.22 12H12V6h-1.9v3.54z" fill="white"/>
        </svg>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-4">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ backgroundColor: '#4E40EF' }}>
              <CreditCard className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-black" style={{ color: '#4E40EF' }}>카드닷</span>
          </Link>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          {/* Tab */}
          <div className="flex border-b border-gray-100">
            <button
              onClick={() => setMode('login')}
              className={`flex-1 py-4 text-sm font-semibold transition-all ${
                mode === 'login' ? 'text-[#4E40EF] border-b-2 border-[#4E40EF]' : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              로그인
            </button>
            <button
              onClick={() => setMode('signup')}
              className={`flex-1 py-4 text-sm font-semibold transition-all ${
                mode === 'signup' ? 'text-[#4E40EF] border-b-2 border-[#4E40EF]' : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              회원가입
            </button>
          </div>

          <div className="p-8">
            {mode === 'login' ? (
              <>
                <h2 className="text-xl text-gray-900 mb-1">다시 오셨군요!</h2>
                <p className="text-gray-500 text-sm mb-6">이메일로 로그인하거나 소셜 계정을 이용해주세요</p>

                <div className="space-y-4 mb-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">이메일</label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="email"
                        placeholder="이메일 주소 입력"
                        className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#4E40EF] focus:ring-1 focus:ring-[#4E40EF]/20 transition-all"
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-sm font-medium text-gray-700">비밀번호</label>
                      <button className="text-xs text-[#4E40EF] hover:underline">비밀번호 찾기</button>
                    </div>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type={showPw ? 'text' : 'password'}
                        placeholder="비밀번호 입력"
                        className="w-full pl-10 pr-10 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#4E40EF] focus:ring-1 focus:ring-[#4E40EF]/20 transition-all"
                      />
                      <button
                        onClick={() => setShowPw(!showPw)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                <Link to="/" className="w-full block text-center py-3 rounded-xl hover:opacity-90 transition-all font-medium mb-4" style={{ backgroundColor: '#4E40EF', color: '#FEFEFE' }}>
                  로그인
                </Link>

                <div className="flex items-center gap-3 mb-4">
                  <div className="flex-1 h-px bg-gray-100" />
                  <span className="text-xs text-gray-400">또는</span>
                  <div className="flex-1 h-px bg-gray-100" />
                </div>

                <div className="space-y-2">
                  {socialBtns.map(btn => (
                    <button
                      key={btn.name}
                      className={`w-full flex items-center justify-center gap-3 py-3 border rounded-xl text-sm font-medium transition-all hover:shadow-sm ${btn.bg} ${btn.textColor} ${btn.border}`}
                    >
                      {btn.icon}
                      {btn.name}로 로그인
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <>
                {step === 1 && (
                  <>
                    <h2 className="text-xl text-gray-900 mb-1">회원가입</h2>
                    <p className="text-gray-500 text-sm mb-6">소셜 계정으로 간편하게 가입하세요</p>

                    <div className="space-y-2 mb-6">
                      {socialBtns.map(btn => (
                        <button
                          key={btn.name}
                          onClick={() => setStep(2)}
                          className={`w-full flex items-center justify-center gap-3 py-3 border rounded-xl text-sm font-medium transition-all hover:shadow-sm ${btn.bg} ${btn.textColor} ${btn.border}`}
                        >
                          {btn.icon}
                          {btn.name}로 회원가입
                        </button>
                      ))}
                    </div>

                    <div className="flex items-center gap-3 mb-4">
                      <div className="flex-1 h-px bg-gray-100" />
                      <span className="text-xs text-gray-400">또는 이메일로 가입</span>
                      <div className="flex-1 h-px bg-gray-100" />
                    </div>

                    <div className="space-y-3 mb-6">
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input type="text" placeholder="닉네임 (2~10자)" className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#4E40EF] transition-all" />
                      </div>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input type="email" placeholder="이메일 주소" className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#4E40EF] transition-all" />
                      </div>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input type="password" placeholder="비밀번호 (8자 이상)" className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#4E40EF] transition-all" />
                      </div>
                    </div>

                    <button
                      onClick={() => setStep(2)}
                      className="w-full py-3 rounded-xl hover:opacity-90 transition-all font-medium flex items-center justify-center gap-2"
                      style={{ backgroundColor: '#4E40EF', color: '#FEFEFE' }}
                    >
                      다음 단계 <ChevronRight className="w-4 h-4" />
                    </button>
                  </>
                )}

                {step === 2 && (
                  <>
                    <h2 className="text-xl text-gray-900 mb-1">약관 동의</h2>
                    <p className="text-gray-500 text-sm mb-6">서비스 이용을 위한 약관에 동의해주세요</p>

                    <div className="space-y-3 mb-6">
                      <div
                        onClick={handleAllAgree}
                        className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl cursor-pointer hover:bg-gray-100 transition-all"
                      >
                        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${agreed.all ? 'bg-[#4E40EF] border-[#4E40EF]' : 'border-gray-300'}`}>
                          {agreed.all && <Check className="w-3 h-3 text-white" />}
                        </div>
                        <span className="text-sm font-semibold text-gray-900">전체 동의</span>
                      </div>

                      {[
                        { key: 'terms' as const, label: '이용약관 동의', required: true },
                        { key: 'privacy' as const, label: '개인정보 처리방침 동의', required: true },
                        { key: 'marketing' as const, label: '마케팅 정보 수신 동의', required: false },
                      ].map(item => (
                        <div key={item.key} onClick={() => handleAgree(item.key)} className="flex items-center gap-3 px-2 cursor-pointer">
                          <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${agreed[item.key] ? 'bg-[#4E40EF] border-[#4E40EF]' : 'border-gray-300'}`} style={agreed[item.key] ? { backgroundColor: '#4E40EF' } : {}}>
                            {agreed[item.key] && <Check className="w-2.5 h-2.5 text-white" />}
                          </div>
                          <span className="text-sm text-gray-700 flex-1">{item.label}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${item.required ? 'text-[#4E40EF]' : 'bg-gray-100 text-gray-500'}`} style={item.required ? { backgroundColor: 'rgba(78,64,239,0.1)' } : {}}>
                            {item.required ? '필수' : '선택'}
                          </span>
                          <button className="text-xs text-gray-400 hover:text-gray-600">보기</button>
                        </div>
                      ))}
                    </div>

                    <div className="flex gap-2">
                      <button onClick={() => setStep(1)} className="flex-1 py-3 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 transition-all text-sm font-medium">
                        이전
                      </button>
                      <Link to="/" className="flex-2 flex-1 text-center py-3 rounded-xl hover:opacity-90 transition-all font-medium text-sm" style={{ backgroundColor: '#4E40EF', color: '#FEFEFE' }}>
                        가입 완료
                      </Link>
                    </div>
                  </>
                )}
              </>
            )}

            {/* Non-member notice */}
            <div className="mt-6 p-3 bg-gray-50 rounded-xl">
              <p className="text-xs text-gray-500 text-center">
                💡 비회원도 카드 조회, 비교, 판별 등 대부분의 서비스를 이용할 수 있어요.<br />
                로그인 시 즐겨찾기, 히스토리 저장 등 개인화 기능이 추가됩니다.
              </p>
            </div>
          </div>
        </div>

        <div className="text-center mt-6">
          <Link to="/" className="text-sm text-gray-500 hover:text-[#4E40EF]">
            ← 메인으로 돌아가기
          </Link>
        </div>
      </div>
    </div>
  );
}