import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { cards } from "../data/mockData";

export interface UserInfo {
  name: string;
  email: string;
  phone: string;
}

export interface AuthContextType {
  isLoggedIn: boolean;
  userInfo: UserInfo;
  login: (email: string) => void;
  logout: () => void;
  updateUserInfo: (info: Partial<UserInfo>) => void;
  recentlyViewedIds: number[];
  addRecentlyViewed: (cardId: number) => void;
  recentlyComparedIds: number[][];
  addRecentlyCompared: (cardIds: number[]) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const DEFAULT_USER: UserInfo = {
  name: "홍길동",
  email: "",
  phone: "010-0000-0000",
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    return localStorage.getItem("isLoggedIn") === "true";
  });

  const [userInfo, setUserInfo] = useState<UserInfo>(() => {
    const stored = localStorage.getItem("userInfo");
    return stored ? JSON.parse(stored) : DEFAULT_USER;
  });

  const [recentlyViewedIds, setRecentlyViewedIds] = useState<number[]>(() => {
    const stored = localStorage.getItem("recentlyViewed");
    return stored ? JSON.parse(stored) : [];
  });

  const [recentlyComparedIds, setRecentlyComparedIds] = useState<number[][]>(() => {
    const stored = localStorage.getItem("recentlyCompared");
    return stored ? JSON.parse(stored) : [];
  });

  useEffect(() => {
    localStorage.setItem("isLoggedIn", String(isLoggedIn));
  }, [isLoggedIn]);

  useEffect(() => {
    localStorage.setItem("userInfo", JSON.stringify(userInfo));
  }, [userInfo]);

  useEffect(() => {
    localStorage.setItem("recentlyViewed", JSON.stringify(recentlyViewedIds));
  }, [recentlyViewedIds]);

  useEffect(() => {
    localStorage.setItem("recentlyCompared", JSON.stringify(recentlyComparedIds));
  }, [recentlyComparedIds]);

  const login = (email: string) => {
    setIsLoggedIn(true);
    setUserInfo((prev) => ({ ...prev, email: email || prev.email }));
  };

  const logout = () => {
    setIsLoggedIn(false);
  };

  const updateUserInfo = (info: Partial<UserInfo>) => {
    setUserInfo((prev) => ({ ...prev, ...info }));
  };

  const addRecentlyViewed = (cardId: number) => {
    setRecentlyViewedIds((prev) => {
      const filtered = prev.filter((id) => id !== cardId);
      return [cardId, ...filtered].slice(0, 10);
    });
  };

  const addRecentlyCompared = (cardIds: number[]) => {
    if (cardIds.length < 2) return;
    setRecentlyComparedIds((prev) => {
      const sorted = [...cardIds].sort((a, b) => a - b);
      const filtered = prev.filter(
        (group) => JSON.stringify([...group].sort((a, b) => a - b)) !== JSON.stringify(sorted)
      );
      return [cardIds, ...filtered].slice(0, 5);
    });
  };

  return (
    <AuthContext.Provider
      value={{
        isLoggedIn,
        userInfo,
        login,
        logout,
        updateUserInfo,
        recentlyViewedIds,
        addRecentlyViewed,
        recentlyComparedIds,
        addRecentlyCompared,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
