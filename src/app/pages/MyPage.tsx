import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "../../api/axios";
import { useQuery } from "@tanstack/react-query";
import { getRecentCards } from "../../api/card";
import {
  User,
  Mail,
  Phone,
  Lock,
  CreditCard,
  Clock,
  GitCompare,
  ChevronRight,
  Edit3,
  Save,
  X,
  LogOut,
  Eye,
  EyeOff,
  RefreshCw,
  Check,
  AlertCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

// ── 사이드바 메뉴 ──────────────────────────────────
type Section = "edit" | "viewed" | "compared";

function SideNav({
  active,
  onChange,
}: {
  active: Section;
  onChange: (s: Section) => void;
}) {
  const menus = [
    {
      group: "개인정보 관리",
      items: [
        { key: "edit" as Section, icon: Edit3, label: "개인정보 수정" },
      ],
    },
    {
      group: "최근 활동 내역",
      items: [
        { key: "viewed" as Section, icon: Clock, label: "최근 본 카드" },
        { key: "compared" as Section, icon: GitCompare, label: "최근 비교한 카드" },
      ],
    },
  ];

  return (
    <nav className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      {menus.map((group) => (
        <div key={group.group}>
          <div className="px-4 pt-4 pb-1">
            <span className="text-[11px] text-gray-400 font-normal uppercase tracking-wide">
              {group.group}
            </span>
          </div>
          {group.items.map((item) => {
            const Icon = item.icon;
            const isActive = active === item.key;
            return (
              <button
                key={item.key}
                onClick={() => onChange(item.key)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-normal transition-all ${
                  isActive ? "text-[#6667AA]" : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
                style={isActive ? { backgroundColor: "rgba(102,103,170,0.08)" } : {}}
              >
                <Icon
                  className="w-4 h-4 flex-shrink-0"
                  style={isActive ? { color: "#6667AA" } : {}}
                />
                {item.label}
                {isActive && (
                  <div
                    className="ml-auto w-1 h-4 rounded-full"
                    style={{ backgroundColor: "#6667AA" }}
                  />
                )}
              </button>
            );
          })}
          <div className="h-px bg-gray-100 mx-4 my-1" />
        </div>
      ))}
    </nav>
  );
}

// ── 개인정보 수정 섹션 ─────────────────────────────
function EditProfile() {
  const { userInfo, updateUserInfo } = useAuth();
  const [form, setForm] = useState({
    name: userInfo.name,
    email: userInfo.email,
    phone: userInfo.phone,
  });
  const [pwForm, setPwForm] = useState({
    current: "",
    next: "",
    confirm: "",
  });
  const [showPw, setShowPw] = useState({ current: false, next: false, confirm: false });
  const [saved, setSaved] = useState(false);
  const [pwSaved, setPwSaved] = useState(false);
  const [pwError, setPwError] = useState("");

  const handleSave = async () => {
    try {
      await api.put("/api/users/profile", {
        name: form.name,
        email: form.email,
        phoneNumber: form.phone,
      });

      updateUserInfo({
        name: form.name,
        email: form.email,
        phone: form.phone,
      });

      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      console.error(error);
      alert("개인정보 수정에 실패했습니다.");
    }
  };

  const handlePwSave = async () => {
    setPwError("");

    if (!pwForm.current) {
      setPwError("현재 비밀번호를 입력해주세요.");
      return;
    }

    if (pwForm.next.length < 8) {
      setPwError("새 비밀번호를 8자 이상 입력해주세요.");
      return;
    }

    if (pwForm.next !== pwForm.confirm) {
      setPwError("새 비밀번호가 일치하지 않습니다.");
      return;
    }

    try {
      await api.put("/api/users/password", {
        currentPassword: pwForm.current,
        newPassword: pwForm.next,
        newPasswordConfirm: pwForm.confirm,
      });

      setPwSaved(true);
      setPwForm({
        current: "",
        next: "",
        confirm: "",
      });

      setTimeout(() => setPwSaved(false), 2000);
    } catch (error) {
      console.error(error);
      setPwError("비밀번호 변경에 실패했습니다.");
    }
  };

  const fields = [
    { key: "name" as const, label: "이름", icon: User, type: "text", placeholder: "이름 입력" },
    { key: "email" as const, label: "이메일", icon: Mail, type: "email", placeholder: "이메일 주소" },
    { key: "phone" as const, label: "전화번호", icon: Phone, type: "tel", placeholder: "010-0000-0000" },
  ];

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl text-gray-900 mb-1">개인정보 수정</h2>
        <p className="text-sm text-gray-500 font-normal">
          이름, 이메일, 전화번호, 비밀번호를 수정할 수 있습니다
        </p>
      </div>

      {/* 기본 정보 */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-4">
        <h3 className="text-sm font-normal text-gray-700 mb-4 flex items-center gap-2">
          <User className="w-4 h-4" style={{ color: "#6667AA" }} />
          기본 정보
        </h3>
        <div className="space-y-4">
          {fields.map(({ key, label, icon: Icon, type, placeholder }) => (
            <div key={key}>
              <label className="block text-sm font-normal text-gray-600 mb-1.5">{label}</label>
              <div className="relative">
                <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type={type}
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  placeholder={placeholder}
                  className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm font-normal focus:outline-none focus:border-[#6667AA] focus:ring-1 focus:ring-[#6667AA]/20 transition-all"
                />
              </div>
            </div>
          ))}
        </div>
        <button
          onClick={handleSave}
          className="mt-5 flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-normal transition-all hover:opacity-90"
          style={{ backgroundColor: saved ? "#22C55E" : "#6667AA", color: "#FEFEFE" }}
        >
          {saved ? (
            <>
              <Check className="w-4 h-4" /> 저장됨
            </>
          ) : (
            <>
              <Save className="w-4 h-4" /> 변경사항 저장
            </>
          )}
        </button>
      </div>

      {/* 비밀번호 변경 */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h3 className="text-sm font-normal text-gray-700 mb-4 flex items-center gap-2">
          <Lock className="w-4 h-4" style={{ color: "#6667AA" }} />
          비밀번호 변경
        </h3>
        <div className="space-y-4">
          {[
            { key: "current" as const, label: "현재 비밀번호", placeholder: "현재 비밀번호 입력" },
            { key: "next" as const, label: "새 비밀번호", placeholder: "새 비밀번호 (8자 이상)" },
            { key: "confirm" as const, label: "새 비밀번호 확인", placeholder: "새 비밀번호 재입력" },
          ].map(({ key, label, placeholder }) => (
            <div key={key}>
              <label className="block text-sm font-normal text-gray-600 mb-1.5">{label}</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type={showPw[key] ? "text" : "password"}
                  value={pwForm[key]}
                  onChange={(e) => setPwForm({ ...pwForm, [key]: e.target.value })}
                  placeholder={placeholder}
                  className="w-full pl-10 pr-10 py-3 border border-gray-200 rounded-xl text-sm font-normal focus:outline-none focus:border-[#6667AA] focus:ring-1 focus:ring-[#6667AA]/20 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPw({ ...showPw, [key]: !showPw[key] })}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPw[key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          ))}
          {pwError && <p className="text-xs text-red-500 font-normal">{pwError}</p>}
        </div>
        <button
          onClick={handlePwSave}
          className="mt-5 flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-normal transition-all hover:opacity-90 border border-gray-200 text-gray-700 bg-white hover:bg-gray-50"
        >
          {pwSaved ? (
            <span className="text-green-600 flex items-center gap-2">
              <Check className="w-4 h-4" /> 변경 완료
            </span>
          ) : (
            <>
              <Lock className="w-4 h-4" /> 비밀번호 변경
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function RecentlyViewed() {
  const { data: viewedCards = [], isLoading } = useQuery({
    queryKey: ["recentCards"],
    queryFn: getRecentCards,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
        최근 본 카드를 불러오는 중...
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl text-gray-900 mb-1">최근 본 카드</h2>
        <p className="text-sm text-gray-500 font-normal">
          최근 조회한 카드 목록입니다
        </p>
      </div>

      {viewedCards.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
          <p className="text-gray-500 text-sm">
            최근 본 카드가 없습니다
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {viewedCards.map((card: any) => (
            <Link
              key={card.cardId}
              to={`/cards/${card.cardId}`}
              className="block bg-white rounded-2xl border border-gray-100 shadow-sm p-5 hover:border-[#6667AA]/30 transition-all"
            >
              <div className="flex items-center gap-4">
                <img
                  src={card.imageUrl}
                  alt={card.cardName}
                  className="w-16 h-10 object-contain"
                />

                <div className="flex-1">
                  <div className="text-xs text-gray-400 font-normal mb-1">
                    {card.company}
                  </div>

                  <div className="text-sm text-gray-900 font-normal">
                    {card.cardName}
                  </div>
                </div>

                <ChevronRight className="w-4 h-4 text-gray-300" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// ── 최근 비교한 카드 섹션 ──────────────────────────
function RecentlyCompared() {
  const [recentCompares, setRecentCompares] = useState<RecentCompare[]>([]);
  const [loading, setLoading] = useState(true);

  interface ComparedCard {
    cardId: string;
    company: string;
    cardName: string;
    imageUrl: string;
  }

  interface RecentCompare {
    compareId: number;
    comparedAt: string;
    cards: ComparedCard[];
  }

  useEffect(() => {
    const fetchRecentCompares = async () => {
      try {
        const token = localStorage.getItem("token");

        const response = await api.get(
          "/api/users/recent-compares",
          {
            headers: {
              Authorization: token,
            },
          }
        );

        setRecentCompares(response.data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    fetchRecentCompares();
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl text-gray-900 mb-1">최근 비교한 카드</h2>
        <p className="text-sm text-gray-500 font-normal">
          최근 비교 이력을 확인하세요 (최대 5회)
        </p>
      </div>

      {loading ? (
        <div>불러오는 중...</div>
      ) : recentCompares.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 flex flex-col items-center gap-3 text-center">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center"
            style={{ backgroundColor: "rgba(102,103,170,0.08)" }}
          >
            <GitCompare className="w-7 h-7" style={{ color: "#6667AA" }} />
          </div>
          <p className="text-gray-500 font-normal text-sm">아직 비교한 카드가 없습니다</p>
          <Link
            to="/compare"
            className="text-sm font-normal hover:underline flex items-center gap-1"
            style={{ color: "#6667AA" }}
          >
            카드 비교하기 <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {recentCompares.map((compare) => {
            const compareUrl = `/compare?cards=${compare.cards
              .map((card) => card.cardId)
              .join(",")}`;

            return (
              <div
                key={compare.compareId}
                className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5"
              >
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs text-gray-400 font-normal">
                    {new Date(compare.comparedAt).toLocaleString("ko-KR")}
                  </span>
                  <Link
                    to={compareUrl}
                    className="text-xs font-normal hover:underline flex items-center gap-1"
                    style={{ color: "#6667AA" }}
                  >
                    다시 비교하기 <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  {compare.cards.map((card, ci) => (
                    <div key={card.cardId} className="flex items-center gap-3">
                      <Link
                        to={`/cards/${card.cardId}`}
                        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
                      >
                        <img
                          src={card.imageUrl}
                          alt={card.cardName}
                          className="w-10 h-10 object-contain"
                        />

                        <div>
                          <div className="text-[10px] text-gray-400 font-normal">
                            {card.company}
                          </div>

                          <div className="text-xs text-gray-800 font-normal leading-snug max-w-[120px]">
                            {card.cardName}
                          </div>
                        </div>
                      </Link>

                      {ci < compare.cards.length - 1 && (
                        <span className="text-gray-300 text-sm">vs</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── 메인 마이페이지 ────────────────────────────────
export function MyPage() {
  const { isLoggedIn, userInfo, logout } = useAuth();
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState<Section>("edit");

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center px-4">
        <div className="text-center">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ backgroundColor: "rgba(102,103,170,0.08)" }}
          >
            <User className="w-8 h-8" style={{ color: "#6667AA" }} />
          </div>
          <h2 className="text-xl text-gray-900 mb-2">로그인이 필요합니다</h2>
          <p className="text-sm text-gray-500 mb-6 font-normal">
            마이페이지를 이용하려면 로그인해주세요
          </p>
          <div className="flex gap-3 justify-center">
            <Link
              to="/login"
              className="px-6 py-3 rounded-xl text-sm font-normal transition-all hover:opacity-90"
              style={{ backgroundColor: "#6667AA", color: "#FEFEFE" }}
            >
              로그인
            </Link>
            <Link
              to="/signup"
              className="px-6 py-3 rounded-xl text-sm font-normal border border-gray-200 text-gray-700 hover:bg-gray-50 transition-all"
            >
              회원가입
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* 상단 프로필 배너 */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-[1080px] mx-auto px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center"
              style={{ backgroundColor: "#6667AA" }}
            >
              <span className="text-white font-normal text-lg">
                {userInfo.name.charAt(0)}
              </span>
            </div>
            <div>
              <div className="text-lg font-normal text-gray-900">
                {userInfo.name} <span className="text-gray-400 text-sm">님</span>
              </div>
              <div className="text-sm text-gray-500 font-normal">{userInfo.email || "이메일 미설정"}</div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm font-normal text-gray-500 hover:text-red-500 transition-colors px-3 py-2 rounded-lg hover:bg-red-50"
          >
            <LogOut className="w-4 h-4" />
            로그아웃
          </button>
        </div>
      </div>

      <div className="max-w-[1080px] mx-auto px-6 py-8">
        <div className="flex gap-6">
          {/* 사이드바 */}
          <div className="w-56 flex-shrink-0">
            <SideNav active={activeSection} onChange={setActiveSection} />
          </div>

          {/* 콘텐츠 영역 */}
          <div className="flex-1 min-w-0">
            {activeSection === "edit" && <EditProfile />}
            {activeSection === "viewed" && <RecentlyViewed />}
            {activeSection === "compared" && <RecentlyCompared />}
          </div>
        </div>
      </div>
    </div>
  );
}
