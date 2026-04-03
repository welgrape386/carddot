import { Link } from "react-router";
import { CreditCard, ArrowLeft } from "lucide-react";

export function NotFound() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
      <div className="text-center">
        <div className="text-6xl text-gray-200 font-normal mb-4">404</div>
        <h1 className="text-xl text-gray-700 mb-2">
          페이지를 찾을 수 없습니다
        </h1>
        <p className="text-gray-400 text-sm mb-8">
          요청하신 페이지가 존재하지 않거나 이동되었습니다.
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-[#1B3D7B] text-white rounded-xl hover:bg-[#162f5f] transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          메인으로 돌아가기
        </Link>
      </div>
    </div>
  );
}
