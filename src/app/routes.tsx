import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { SignUp } from "./pages/SignUp";
import { MyPage } from "./pages/MyPage";
import { CardList } from "./pages/CardList";
import { CardDetail } from "./pages/CardDetail";
import { CardComparison } from "./pages/CardComparison";
import { CardAnalysis } from "./pages/CardAnalysis";
import { IssuerRanking } from "./pages/IssuerRanking";
import { NotFound } from "./pages/NotFound";

export const router = createBrowserRouter([
  {
    Component: Layout,
    children: [
      { index: true, Component: Home },
      { path: "login", Component: Login },
      { path: "signup", Component: SignUp },
      { path: "mypage", Component: MyPage },
      { path: "cards", Component: CardList },
      { path: "cards/:id", Component: CardDetail },
      { path: "compare", Component: CardComparison },
      { path: "analysis", Component: CardAnalysis },
      { path: "ranking", Component: IssuerRanking },
      { path: "*", Component: NotFound },
    ],
  },
]);
