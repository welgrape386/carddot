import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { Eye, EyeOff, CreditCard, Lock, Mail } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email.trim()) {
      setError("이메일을 입력해주세요.");
      return;
    }
    if (!password.trim()) {
      setError("비밀번호를 입력해주세요.");
      return;
    }

    setLoading(true);
    // 현재는 어떤 이메일/비밀번호든 로그인 허용 (추후 DB 연결 예정)
    setTimeout(() => {
      login(email);
      navigate("/mypage");
    }, 600);
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-4">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ backgroundColor: "#6667AA" }}
            >
              <CreditCard className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-normal" style={{ color: "#6667AA" }}>
              카드닷
            </span>
          </Link>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          {/* Tab */}
          <div className="flex border-b border-gray-100">
            <Link
              to="/login"
              className="flex-1 py-4 text-sm font-normal text-center transition-all text-[#6667AA] border-b-2 border-[#6667AA]"
            >
              로그인
            </Link>
            <Link
              to="/signup"
              className="flex-1 py-4 text-sm font-normal text-center transition-all text-gray-400 hover:text-gray-600"
            >
              회원가입
            </Link>
          </div>

          <div className="p-8">
            <h2 className="text-xl text-gray-900 mb-1">다시 오셨군요!</h2>
            <p className="text-gray-500 text-sm mb-6">
              이메일과 비밀번호로 로그인해주세요
            </p>

            <form onSubmit={handleLogin} className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-normal text-gray-700 mb-1.5">
                  이메일
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="이메일 주소 입력"
                    className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#6667AA] focus:ring-1 focus:ring-[#6667AA]/20 transition-all"
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-sm font-normal text-gray-700">
                    비밀번호
                  </label>
                  <button
                    type="button"
                    className="text-xs text-[#6667AA] hover:underline"
                  >
                    비밀번호 찾기
                  </button>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type={showPw ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="비밀번호 입력"
                    className="w-full pl-10 pr-10 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#6667AA] focus:ring-1 focus:ring-[#6667AA]/20 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(!showPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPw ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {error && (
                <p className="text-xs text-red-500 font-normal">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl hover:opacity-90 transition-all font-normal mt-2 flex items-center justify-center gap-2 disabled:opacity-60"
                style={{ backgroundColor: "#6667AA", color: "#FEFEFE" }}
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    로그인 중...
                  </>
                ) : (
                  "로그인"
                )}
              </button>
            </form>

            {/* Non-member notice */}
            <div className="mt-4 p-3 bg-gray-50 rounded-xl">
              <p className="text-xs text-gray-500 text-center">
                💡 비회원도 카드 조회, 비교, 판별 등 대부분의 서비스를 이용할 수
                있어요.
                <br />
                로그인 시 즐겨찾기, 히스토리 저장 등 개인화 기능이 추가됩니다.
              </p>
            </div>
          </div>
        </div>

        <div className="text-center mt-6">
          <Link to="/" className="text-sm text-gray-500 hover:text-[#6667AA]">
            ← 메인으로 돌아가기
          </Link>
        </div>
      </div>
    </div>
  );
}
