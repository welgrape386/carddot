import { Link, useLocation, useNavigate } from "react-router";
import { CreditCard, User, Menu, X, LogOut } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { isLoggedIn, userInfo, logout } = useAuth();

  const navLinks = [
    { href: "/cards", label: "카드 조회" },
    { href: "/ranking", label: "카드 랭킹" },
    { href: "/compare", label: "카드 비교" },
    { href: "/analysis", label: "카드 판별" },
  ];

  const isActive = (href: string) => location.pathname.startsWith(href);

  const handleLogout = () => {
    logout();
    navigate("/");
    setMobileOpen(false);
  };

  return (
    <nav
      className="sticky top-0 z-50 shadow-md"
      style={{ backgroundColor: "#6667AA" }}
    >
      <div className="max-w-[1280px] mx-auto px-6">
        <div className="flex items-center h-16 gap-8">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: "rgba(255,255,255,0.2)" }}
            >
              <CreditCard className="w-4 h-4" style={{ color: "#FEFEFE" }} />
            </div>
            <span
              className="text-lg font-normal tracking-tight"
              style={{ color: "#FEFEFE" }}
            >
              카드닷
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1 flex-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className={`px-4 py-2 rounded-lg text-sm font-normal transition-all ${
                  isActive(link.href)
                    ? "text-[#FEFEFE]"
                    : "hover:text-[#FEFEFE]"
                }`}
                style={
                  isActive(link.href)
                    ? {
                        backgroundColor: "rgba(255,255,255,0.2)",
                        color: "#FEFEFE",
                      }
                    : { color: "rgba(254,254,254,0.75)" }
                }
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Right */}
          <div className="hidden md:flex items-center gap-2 ml-auto">
            {isLoggedIn ? (
              <>
                <Link
                  to="/mypage"
                  className="flex items-center gap-2 px-3 py-2 rounded-lg transition-all"
                  style={{ color: "#FEFEFE" }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.backgroundColor =
                      "rgba(255,255,255,0.12)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.backgroundColor = "transparent")
                  }
                >
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: "rgba(255,255,255,0.25)" }}
                  >
                    <span className="text-white text-xs font-normal">
                      {userInfo.name.charAt(0)}
                    </span>
                  </div>
                  <span
                    className="text-sm font-normal"
                    style={{ color: "#FEFEFE" }}
                  >
                    마이페이지
                  </span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-normal transition-all"
                  style={{ color: "rgba(254,254,254,0.75)" }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.12)";
                    e.currentTarget.style.color = "#FEFEFE";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "transparent";
                    e.currentTarget.style.color = "rgba(254,254,254,0.75)";
                  }}
                >
                  <LogOut className="w-4 h-4" />
                  로그아웃
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="px-4 py-2 text-sm font-normal rounded-lg border transition-all"
                  style={{
                    color: "#FEFEFE",
                    borderColor: "rgba(254,254,254,0.4)",
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.backgroundColor =
                      "rgba(255,255,255,0.12)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.backgroundColor = "transparent")
                  }
                >
                  로그인
                </Link>
                <Link
                  to="/signup"
                  className="px-4 py-2 text-sm font-normal rounded-lg transition-all"
                  style={{ backgroundColor: "#FEFEFE", color: "#6667AA" }}
                  onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.9")}
                  onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
                >
                  회원가입
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden ml-auto p-2 rounded-lg transition-all"
            style={{ color: "#FEFEFE" }}
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? (
              <X className="w-5 h-5" />
            ) : (
              <Menu className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div
          className="md:hidden px-4 py-3 space-y-1"
          style={{
            backgroundColor: "#5556A0",
            borderTop: "1px solid rgba(255,255,255,0.12)",
          }}
        >
          {navLinks.map((link) => (
            <Link
              key={link.href}
              to={link.href}
              onClick={() => setMobileOpen(false)}
              className="block px-4 py-2.5 rounded-lg text-sm font-normal transition-all"
              style={
                isActive(link.href)
                  ? {
                      backgroundColor: "rgba(255,255,255,0.2)",
                      color: "#FEFEFE",
                    }
                  : { color: "rgba(254,254,254,0.8)" }
              }
            >
              {link.label}
            </Link>
          ))}
          <div
            className="pt-2 flex gap-2"
            style={{ borderTop: "1px solid rgba(255,255,255,0.12)" }}
          >
            {isLoggedIn ? (
              <>
                <Link
                  to="/mypage"
                  onClick={() => setMobileOpen(false)}
                  className="flex-1 text-center py-2 text-sm font-normal rounded-lg"
                  style={{ backgroundColor: "rgba(255,255,255,0.15)", color: "#FEFEFE" }}
                >
                  마이페이지
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex-1 text-center py-2 text-sm font-normal rounded-lg border"
                  style={{ color: "#FEFEFE", borderColor: "rgba(254,254,254,0.4)" }}
                >
                  로그아웃
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="flex-1 text-center py-2 text-sm font-normal rounded-lg border"
                  style={{ color: "#FEFEFE", borderColor: "rgba(254,254,254,0.4)" }}
                >
                  로그인
                </Link>
                <Link
                  to="/signup"
                  onClick={() => setMobileOpen(false)}
                  className="flex-1 text-center py-2 text-sm font-normal rounded-lg"
                  style={{ backgroundColor: "#FEFEFE", color: "#6667AA" }}
                >
                  회원가입
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
