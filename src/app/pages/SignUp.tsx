import { useState } from "react";
import { Link, useNavigate } from "react-router";
import {
  Eye,
  EyeOff,
  CreditCard,
  Check,
  Lock,
  Mail,
  User,
  ChevronRight,
  Phone,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function SignUp() {
  const navigate = useNavigate();
  const { login, updateUserInfo } = useAuth();

  const [step, setStep] = useState(1);
  const [showPw, setShowPw] = useState(false);
  const [showPwConfirm, setShowPwConfirm] = useState(false);
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    password: "",
    passwordConfirm: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [agreed, setAgreed] = useState({
    all: false,
    terms: false,
    privacy: false,
    marketing: false,
  });

  const handleAllAgree = () => {
    const newVal = !agreed.all;
    setAgreed({ all: newVal, terms: newVal, privacy: newVal, marketing: newVal });
  };

  const handleAgree = (key: "terms" | "privacy" | "marketing") => {
    const updated = { ...agreed, [key]: !agreed[key] };
    updated.all = updated.terms && updated.privacy && updated.marketing;
    setAgreed(updated);
  };

  const validateStep1 = () => {
    const errs: Record<string, string> = {};
    if (!form.name.trim() || form.name.length < 2) errs.name = "이름을 2자 이상 입력해주세요.";
    if (!form.email.trim() || !form.email.includes("@")) errs.email = "올바른 이메일을 입력해주세요.";
    if (!form.password || form.password.length < 8) errs.password = "비밀번호를 8자 이상 입력해주세요.";
    if (form.password !== form.passwordConfirm) errs.passwordConfirm = "비밀번호가 일치하지 않습니다.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleNext = () => {
    if (validateStep1()) setStep(2);
  };

  const handleSubmit = () => {
    if (!agreed.terms || !agreed.privacy) {
      setErrors({ agree: "필수 약관에 동의해주세요." });
      return;
    }
    setLoading(true);
    setTimeout(() => {
      updateUserInfo({ name: form.name, email: form.email, phone: form.phone });
      login(form.email);
      navigate("/mypage");
    }, 700);
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
              className="flex-1 py-4 text-sm font-normal text-center transition-all text-gray-400 hover:text-gray-600"
            >
              로그인
            </Link>
            <Link
              to="/signup"
              className="flex-1 py-4 text-sm font-normal text-center transition-all text-[#6667AA] border-b-2 border-[#6667AA]"
            >
              회원가입
            </Link>
          </div>

          <div className="p-8">
            {/* Step indicator */}
            <div className="flex items-center gap-2 mb-6">
              {[1, 2].map((s) => (
                <div key={s} className="flex items-center gap-2">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-normal transition-all ${
                      step >= s
                        ? "text-white"
                        : "bg-gray-100 text-gray-400"
                    }`}
                    style={step >= s ? { backgroundColor: "#6667AA" } : {}}
                  >
                    {step > s ? <Check className="w-3.5 h-3.5" /> : s}
                  </div>
                  <span
                    className={`text-xs font-normal ${step === s ? "text-gray-700" : "text-gray-400"}`}
                  >
                    {s === 1 ? "기본 정보" : "약관 동의"}
                  </span>
                  {s < 2 && <div className="w-8 h-px bg-gray-200 mx-1" />}
                </div>
              ))}
            </div>

            {step === 1 && (
              <>
                <h2 className="text-xl text-gray-900 mb-1">회원가입</h2>
                <p className="text-gray-500 text-sm mb-6">
                  이메일로 간편하게 가입하세요
                </p>

                <div className="space-y-3 mb-6">
                  <div>
                    <label className="block text-sm font-normal text-gray-700 mb-1.5">
                      이름
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        placeholder="실명 입력"
                        className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#6667AA] focus:ring-1 focus:ring-[#6667AA]/20 transition-all"
                      />
                    </div>
                    {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name}</p>}
                  </div>

                  <div>
                    <label className="block text-sm font-normal text-gray-700 mb-1.5">
                      이메일
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        placeholder="이메일 주소"
                        className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#6667AA] focus:ring-1 focus:ring-[#6667AA]/20 transition-all"
                      />
                    </div>
                    {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email}</p>}
                  </div>

                  <div>
                    <label className="block text-sm font-normal text-gray-700 mb-1.5">
                      전화번호 <span className="text-gray-400">(선택)</span>
                    </label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="tel"
                        value={form.phone}
                        onChange={(e) => setForm({ ...form, phone: e.target.value })}
                        placeholder="010-0000-0000"
                        className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#6667AA] focus:ring-1 focus:ring-[#6667AA]/20 transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-normal text-gray-700 mb-1.5">
                      비밀번호
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type={showPw ? "text" : "password"}
                        value={form.password}
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                        placeholder="비밀번호 (8자 이상)"
                        className="w-full pl-10 pr-10 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#6667AA] focus:ring-1 focus:ring-[#6667AA]/20 transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPw(!showPw)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password}</p>}
                  </div>

                  <div>
                    <label className="block text-sm font-normal text-gray-700 mb-1.5">
                      비밀번호 확인
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type={showPwConfirm ? "text" : "password"}
                        value={form.passwordConfirm}
                        onChange={(e) => setForm({ ...form, passwordConfirm: e.target.value })}
                        placeholder="비밀번호 재입력"
                        className="w-full pl-10 pr-10 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#6667AA] focus:ring-1 focus:ring-[#6667AA]/20 transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPwConfirm(!showPwConfirm)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showPwConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    {errors.passwordConfirm && (
                      <p className="text-xs text-red-500 mt-1">{errors.passwordConfirm}</p>
                    )}
                  </div>
                </div>

                <button
                  onClick={handleNext}
                  className="w-full py-3 rounded-xl hover:opacity-90 transition-all font-normal flex items-center justify-center gap-2"
                  style={{ backgroundColor: "#6667AA", color: "#FEFEFE" }}
                >
                  다음 단계 <ChevronRight className="w-4 h-4" />
                </button>
              </>
            )}

            {step === 2 && (
              <>
                <h2 className="text-xl text-gray-900 mb-1">약관 동의</h2>
                <p className="text-gray-500 text-sm mb-6">
                  서비스 이용을 위한 약관에 동의해주세요
                </p>

                <div className="space-y-3 mb-6">
                  <div
                    onClick={handleAllAgree}
                    className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl cursor-pointer hover:bg-gray-100 transition-all"
                  >
                    <div
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                        agreed.all ? "border-[#6667AA]" : "border-gray-300"
                      }`}
                      style={agreed.all ? { backgroundColor: "#6667AA" } : {}}
                    >
                      {agreed.all && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <span className="text-sm font-normal text-gray-900">
                      전체 동의
                    </span>
                  </div>

                  {[
                    { key: "terms" as const, label: "이용약관 동의", required: true },
                    { key: "privacy" as const, label: "개인정보 처리방침 동의", required: true },
                    { key: "marketing" as const, label: "마케팅 정보 수신 동의", required: false },
                  ].map((item) => (
                    <div
                      key={item.key}
                      onClick={() => handleAgree(item.key)}
                      className="flex items-center gap-3 px-2 cursor-pointer py-1"
                    >
                      <div
                        className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all`}
                        style={
                          agreed[item.key]
                            ? { backgroundColor: "#6667AA", borderColor: "#6667AA" }
                            : { borderColor: "#D1D5DB" }
                        }
                      >
                        {agreed[item.key] && <Check className="w-2.5 h-2.5 text-white" />}
                      </div>
                      <span className="text-sm text-gray-700 flex-1">{item.label}</span>
                      <span
                        className={`text-xs px-1.5 py-0.5 rounded`}
                        style={
                          item.required
                            ? { backgroundColor: "rgba(102,103,170,0.1)", color: "#6667AA" }
                            : { backgroundColor: "#F3F4F6", color: "#6B7280" }
                        }
                      >
                        {item.required ? "필수" : "선택"}
                      </span>
                    </div>
                  ))}

                  {errors.agree && (
                    <p className="text-xs text-red-500">{errors.agree}</p>
                  )}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => { setStep(1); setErrors({}); }}
                    className="flex-1 py-3 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 transition-all text-sm font-normal"
                  >
                    이전
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={loading}
                    className="flex-1 py-3 rounded-xl hover:opacity-90 transition-all font-normal text-sm flex items-center justify-center gap-2 disabled:opacity-60"
                    style={{ backgroundColor: "#6667AA", color: "#FEFEFE" }}
                  >
                    {loading ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                        가입 중...
                      </>
                    ) : (
                      "가입 완료"
                    )}
                  </button>
                </div>
              </>
            )}

            {/* Non-member notice */}
            <div className="mt-6 p-3 bg-gray-50 rounded-xl">
              <p className="text-xs text-gray-500 text-center">
                💡 비회원도 카드 조회, 비교, 판별 등 대부분의 서비스를 이용할 수
                있어요.
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
