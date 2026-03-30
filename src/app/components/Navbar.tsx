import { Link, useLocation } from 'react-router';
import { CreditCard, Bell, User, Menu, X } from 'lucide-react';
import { useState } from 'react';

export function Navbar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isLoggedIn] = useState(true);

  const navLinks = [
    { href: '/cards', label: '카드 조회' },
    { href: '/ranking', label: '카드사별 랭킹' },
    { href: '/compare', label: '카드 비교' },
    { href: '/analysis', label: '카드 판별' },
  ];

  const isActive = (href: string) => location.pathname.startsWith(href);

  return (
    <nav className="sticky top-0 z-50 shadow-md" style={{ backgroundColor: '#4E40EF' }}>
      <div className="max-w-[1280px] mx-auto px-6">
        <div className="flex items-center h-16 gap-8">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: 'rgba(255,255,255,0.2)' }}>
              <CreditCard className="w-4 h-4" style={{ color: '#FEFEFE' }} />
            </div>
            <span className="text-lg font-black tracking-tight" style={{ color: '#FEFEFE' }}>카드닷</span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1 flex-1">
            {navLinks.map(link => (
              <Link
                key={link.href}
                to={link.href}
                className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                  isActive(link.href)
                    ? 'text-[#FEFEFE]'
                    : 'hover:text-[#FEFEFE]'
                }`}
                style={
                  isActive(link.href)
                    ? { backgroundColor: 'rgba(255,255,255,0.2)', color: '#FEFEFE' }
                    : { color: 'rgba(254,254,254,0.75)' }
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
                <button
                  className="relative p-2 rounded-lg transition-all"
                  style={{ color: 'rgba(254,254,254,0.75)' }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.12)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <Bell className="w-5 h-5" />
                  <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-400 rounded-full"></span>
                </button>
                <Link
                  to="/mypage"
                  className="flex items-center gap-2 px-3 py-2 rounded-lg transition-all"
                  style={{ color: '#FEFEFE' }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.12)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div className="w-7 h-7 rounded-full flex items-center justify-center" style={{ backgroundColor: 'rgba(255,255,255,0.25)' }}>
                    <User className="w-3.5 h-3.5" style={{ color: '#FEFEFE' }} />
                  </div>
                  <span className="text-sm font-bold" style={{ color: '#FEFEFE' }}>마이페이지</span>
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="px-4 py-2 text-sm font-bold rounded-lg border transition-all"
                  style={{ color: '#FEFEFE', borderColor: 'rgba(254,254,254,0.4)' }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.12)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  로그인
                </Link>
                <Link
                  to="/signup"
                  className="px-4 py-2 text-sm font-bold rounded-lg transition-all"
                  style={{ backgroundColor: '#FEFEFE', color: '#4E40EF' }}
                  onMouseEnter={e => (e.currentTarget.style.opacity = '0.9')}
                  onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
                >
                  회원가입
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden ml-auto p-2 rounded-lg transition-all"
            style={{ color: '#FEFEFE' }}
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden px-4 py-3 space-y-1" style={{ backgroundColor: '#4E40EF', borderTop: '1px solid rgba(255,255,255,0.12)' }}>
          {navLinks.map(link => (
            <Link
              key={link.href}
              to={link.href}
              onClick={() => setMobileOpen(false)}
              className="block px-4 py-2.5 rounded-lg text-sm font-bold transition-all"
              style={
                isActive(link.href)
                  ? { backgroundColor: 'rgba(255,255,255,0.2)', color: '#FEFEFE' }
                  : { color: 'rgba(254,254,254,0.8)' }
              }
            >
              {link.label}
            </Link>
          ))}
          <div className="pt-2 flex gap-2" style={{ borderTop: '1px solid rgba(255,255,255,0.12)' }}>
            <Link
              to="/login"
              className="flex-1 text-center py-2 text-sm font-bold rounded-lg border"
              style={{ color: '#FEFEFE', borderColor: 'rgba(254,254,254,0.4)' }}
            >
              로그인
            </Link>
            <Link
              to="/signup"
              className="flex-1 text-center py-2 text-sm font-bold rounded-lg"
              style={{ backgroundColor: '#FEFEFE', color: '#4E40EF' }}
            >
              회원가입
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
