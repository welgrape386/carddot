import { useMemo, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router";
import {
  Star,
  Heart,
  GitCompare,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  Info,
  TrendingUp,
  Share2,
  ExternalLink,
} from "lucide-react";
import { cards } from "../data/mockData";
import { CardVisual } from "../components/CardVisual";

const categoryBenefitMap: Record<string, string[]> = {
  온라인쇼핑: ["쇼핑"],
  "패션/뷰티": ["쇼핑", "뷰티"],
  "슈퍼마켓/생활잡화": ["마트"],
  "백화점/아울렛": ["마트", "쇼핑"],
  "대중교통/택시": ["교통"],
  "자동차/주유": ["주유"],
  반려동물: [],
  "구독/스트리밍": [],
  "레저/스포츠": [],
  "페이/간편결제": [],
  "문화/엔터": ["영화"],
  생활비: ["통신"],
  편의점: ["편의점"],
  "커피/카페/베이커리": ["카페"],
  배달: ["배달"],
  외식: ["외식"],
  "여행/숙박": ["여행"],
  항공: ["항공"],
  해외: ["해외"],
  "교육/육아": [],
  의료: ["의료", "병원", "약국"],
};

function isBenefitMatched(benefitCategory: string, selectedCategory: string) {
  const mapped = categoryBenefitMap[selectedCategory] ?? [selectedCategory];
  if (!mapped.length) return false;

  return mapped.some((m) =>
    benefitCategory.toLowerCase().includes(m.toLowerCase()),
  );
}

export function CardDetail() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();

  const card = cards.find((c) => c.id === Number(id)) || cards[0];
  const [favorite, setFavorite] = useState(false);
  const [activeSection, setActiveSection] = useState<
    "benefits" | "conditions" | "events"
  >("benefits");

  const selectedCategories = (
    searchParams.get("benefits")?.split(",").filter(Boolean) || []
  ).map((v) => decodeURIComponent(v));

  const benefitTypeLabel: Record<
    string,
    { label: string; color: string; bg: string }
  > = {
    discount: { label: "할인", color: "text-blue-600", bg: "bg-blue-50" },
    cashback: { label: "캐시백", color: "text-green-600", bg: "bg-green-50" },
    point: { label: "포인트", color: "text-purple-600", bg: "bg-purple-50" },
  };

  const typeLabel = card.type === "credit" ? "신용카드" : "체크카드";

  const orderedBenefits = useMemo(() => {
    if (selectedCategories.length === 0) return card.benefits;

    const prioritized = [...card.benefits].sort((a, b) => {
      const aMatched = selectedCategories.some((cat) =>
        isBenefitMatched(a.category, cat),
      );
      const bMatched = selectedCategories.some((cat) =>
        isBenefitMatched(b.category, cat),
      );

      if (aMatched && !bMatched) return -1;
      if (!aMatched && bMatched) return 1;
      return 0;
    });

    return prioritized;
  }, [card.benefits, selectedCategories]);

  const matchedSelectedCategories = selectedCategories.filter((selected) =>
    card.benefits.some((benefit) =>
      isBenefitMatched(benefit.category, selected),
    ),
  );

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* Breadcrumb */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-[1280px] mx-auto px-6 py-3">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Link to="/" className="hover:text-[#1B3D7B]">
              홈
            </Link>
            <ChevronRight className="w-3 h-3" />
            <Link to="/cards" className="hover:text-[#1B3D7B]">
              카드 조회
            </Link>
            <ChevronRight className="w-3 h-3" />
            <span className="text-gray-700">{card.name}</span>
          </div>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8">
        <div className="grid grid-cols-[1fr_320px] gap-8">
          {/* Left */}
          <div className="space-y-6">
            {/* Hero */}
            <div className="bg-white rounded-2xl border border-gray-100 p-8">
              <div className="flex gap-8 items-start">
                <div className="flex flex-col items-center gap-4">
                  <CardVisual card={card} size="lg" />

                  <div className="flex gap-2">
                    <button
                      onClick={() => setFavorite(!favorite)}
                      className={`flex items-center gap-1.5 px-4 py-2 rounded-xl border text-sm font-normal transition-all ${
                        favorite
                          ? "bg-red-50 border-red-200 text-red-500"
                          : "border-gray-200 text-gray-600 hover:border-red-200 hover:text-red-400"
                      }`}
                    >
                      <Heart
                        className={`w-4 h-4 ${favorite ? "fill-red-500" : ""}`}
                      />
                      {favorite ? "즐겨찾기 됨" : "즐겨찾기"}
                    </button>

                    <Link
                      to={
                        selectedCategories.length > 0
                          ? `/compare?cards=${card.id}&benefits=${encodeURIComponent(
                              selectedCategories.join(","),
                            )}`
                          : `/compare?cards=${card.id}`
                      }
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-200 text-sm font-normal text-gray-600 hover:border-[#1B3D7B] hover:text-[#1B3D7B] transition-all"
                    >
                      <GitCompare className="w-4 h-4" />
                      비교하기
                    </Link>

                    <button className="p-2 rounded-xl border border-gray-200 text-gray-400 hover:text-[#1B3D7B] hover:border-[#1B3D7B] transition-all">
                      <Share2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm text-gray-500">{card.issuer}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-normal ${
                        card.type === "credit"
                          ? "bg-blue-50 text-blue-600"
                          : "bg-purple-50 text-purple-600"
                      }`}
                    >
                      {typeLabel}
                    </span>
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">
                      {card.network}
                    </span>
                  </div>

                  <h1 className="text-2xl text-gray-900 mb-3">{card.name}</h1>

                  <div className="flex items-center gap-3 mb-5">
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((i) => (
                        <Star
                          key={i}
                          className={`w-4 h-4 ${
                            i <= Math.round(card.rating)
                              ? "text-yellow-400 fill-yellow-400"
                              : "text-gray-200 fill-gray-200"
                          }`}
                        />
                      ))}
                    </div>
                    <span className="text-gray-900 font-normal">
                      {card.rating}
                    </span>
                    <span className="text-gray-400 text-sm">
                      ({card.reviews.toLocaleString()}개 리뷰)
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-3 mb-5">
                    {[
                      {
                        label: "연회비",
                        value:
                          card.annualFee === 0
                            ? "없음"
                            : `${card.annualFee.toLocaleString()}원`,
                        highlight: card.annualFee === 0,
                      },
                      {
                        label: "전월실적",
                        value:
                          card.minSpending === 0
                            ? "무실적"
                            : `${(card.minSpending / 10000).toFixed(0)}만원 이상`,
                        highlight: card.minSpending === 0,
                      },
                      {
                        label: "월 최대 혜택",
                        value: `${(card.maxBenefit / 10000).toFixed(0)}만원`,
                        highlight: false,
                      },
                    ].map((spec) => (
                      <div
                        key={spec.label}
                        className="p-3 bg-gray-50 rounded-xl"
                      >
                        <div className="text-xs text-gray-500 mb-0.5">
                          {spec.label}
                        </div>
                        <div
                          className={`font-normal ${
                            spec.highlight ? "text-green-600" : "text-gray-900"
                          }`}
                        >
                          {spec.value}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-wrap gap-1.5 mb-5">
                    {card.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs bg-[#1B3D7B]/8 text-[#1B3D7B] px-2.5 py-1 rounded-full font-normal"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  {matchedSelectedCategories.length > 0 && (
                    <div className="p-4 rounded-xl border border-[#6667AA]/15 bg-[#6667AA]/5">
                      <div className="text-xs text-[#6667AA] font-normal mb-2">
                        조회에서 선택한 혜택
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {matchedSelectedCategories.map((cat) => (
                          <span
                            key={cat}
                            className="text-xs bg-white text-[#6667AA] border border-[#6667AA]/15 px-2.5 py-1 rounded-full font-normal"
                          >
                            {cat}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {card.eventBenefits.length > 0 && (
                    <div className="p-3 mt-4 bg-orange-50 border border-orange-100 rounded-xl">
                      <div className="flex items-center gap-2 mb-1">
                        <TrendingUp className="w-3.5 h-3.5 text-orange-500" />
                        <span className="text-xs font-normal text-orange-600">
                          이벤트 혜택
                        </span>
                      </div>
                      {card.eventBenefits.map((e, i) => (
                        <p key={i} className="text-xs text-orange-700">
                          {e}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Benefits */}
            <div className="bg-white rounded-2xl border border-gray-100">
              <div className="flex border-b border-gray-100">
                {[
                  { key: "benefits", label: "주요 혜택" },
                  { key: "conditions", label: "이용 조건" },
                  { key: "events", label: "이벤트" },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveSection(tab.key as any)}
                    className={`flex-1 py-4 text-sm font-normal transition-all ${
                      activeSection === tab.key
                        ? "text-[#1B3D7B] border-b-2 border-[#1B3D7B]"
                        : "text-gray-400"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="p-6">
                {activeSection === "benefits" && (
                  <>
                    <div className="grid grid-cols-3 gap-3 mb-6">
                      {orderedBenefits.slice(0, 3).map((b, i) => {
                        const highlighted = selectedCategories.some((cat) =>
                          isBenefitMatched(b.category, cat),
                        );

                        return (
                          <div
                            key={i}
                            className={`p-4 border rounded-xl transition-all ${
                              highlighted
                                ? "border-[#6667AA]/30 bg-[#6667AA]/4"
                                : "border-gray-100 hover:border-[#1B3D7B]/20"
                            }`}
                          >
                            <div className="text-2xl mb-2">{b.icon}</div>
                            <div className="text-xs text-gray-500 mb-1">
                              {b.category}
                            </div>
                            <div className="font-normal text-[#1B3D7B]">
                              {b.discountRate}%
                            </div>
                            <div
                              className={`inline-flex mt-1 text-[10px] px-1.5 py-0.5 rounded font-normal ${benefitTypeLabel[b.type].bg} ${benefitTypeLabel[b.type].color}`}
                            >
                              {benefitTypeLabel[b.type].label}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div className="overflow-hidden rounded-xl border border-gray-100">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-gray-50 text-left">
                            <th className="px-4 py-3 text-xs font-normal text-gray-500 w-[18%]">
                              혜택 분류
                            </th>
                            <th className="px-4 py-3 text-xs font-normal text-gray-500 w-[28%]">
                              적용 가맹점 / 혜택 내용
                            </th>
                            <th className="px-4 py-3 text-xs font-normal text-gray-500 text-center w-[12%]">
                              할인율
                            </th>
                            <th className="px-4 py-3 text-xs font-normal text-gray-500 text-center w-[14%]">
                              월 최대
                            </th>
                            <th className="px-4 py-3 text-xs font-normal text-gray-500">
                              이용 조건
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {orderedBenefits.map((b, i) => {
                            const highlighted = selectedCategories.some((cat) =>
                              isBenefitMatched(b.category, cat),
                            );

                            return (
                              <tr
                                key={i}
                                className={`border-t transition-colors ${
                                  highlighted
                                    ? "bg-[#6667AA]/3 border-[#6667AA]/10"
                                    : "border-gray-50 hover:bg-gray-50/50"
                                }`}
                              >
                                <td className="px-4 py-4 align-top">
                                  <div className="flex items-center gap-2">
                                    <span>{b.icon}</span>
                                    <div>
                                      <div className="text-gray-900 font-normal">
                                        {b.category}
                                      </div>
                                      {highlighted && (
                                        <div className="text-[10px] text-[#6667AA] mt-1">
                                          선택 혜택 우선 노출
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </td>

                                <td className="px-4 py-4 align-top">
                                  <div className="text-xs text-gray-700 leading-relaxed">
                                    {b.description}
                                  </div>
                                </td>

                                <td className="px-4 py-4 text-center align-top">
                                  <span
                                    className={`text-sm font-normal ${
                                      b.type === "cashback"
                                        ? "text-green-600"
                                        : b.type === "point"
                                          ? "text-purple-600"
                                          : "text-[#1B3D7B]"
                                    }`}
                                  >
                                    {b.discountRate}%
                                  </span>
                                </td>

                                <td className="px-4 py-4 text-center align-top">
                                  <span className="text-sm font-normal text-gray-900">
                                    {b.maxMonthly.toLocaleString()}원
                                  </span>
                                </td>

                                <td className="px-4 py-4 align-top">
                                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                                    {b.condition}
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}

                {activeSection === "conditions" && (
                  <div className="space-y-4">
                    {[
                      {
                        title: "발급 기준",
                        icon: CheckCircle,
                        color: "text-green-500",
                        items: [
                          "만 19세 이상 대한민국 국민",
                          "신용등급 1~6등급 (카드사별 상이)",
                          "연간 소득 1,500만원 이상 권장",
                        ],
                      },
                      {
                        title: "유의사항",
                        icon: AlertCircle,
                        color: "text-orange-500",
                        items: [
                          "혜택 한도는 전월 실적 충족 여부에 따라 달라질 수 있습니다",
                          "동일 가맹점 중복 할인은 적용되지 않습니다",
                          "일부 혜택은 해당 카드사 앱 또는 웹사이트 사전 등록 필요",
                        ],
                      },
                      {
                        title: "안내 사항",
                        icon: Info,
                        color: "text-blue-500",
                        items: [
                          "이 페이지의 혜택 정보는 2025년 3월 기준입니다",
                          "카드사 사정에 의해 혜택이 변경될 수 있습니다",
                          "정확한 정보는 해당 카드사 공식 홈페이지를 확인해주세요",
                        ],
                      },
                    ].map((section) => (
                      <div
                        key={section.title}
                        className="p-4 border border-gray-100 rounded-xl"
                      >
                        <div className="flex items-center gap-2 mb-3">
                          <section.icon
                            className={`w-4 h-4 ${section.color}`}
                          />
                          <span className="text-sm font-normal text-gray-900">
                            {section.title}
                          </span>
                        </div>
                        <ul className="space-y-1.5">
                          {section.items.map((item, i) => (
                            <li
                              key={i}
                              className="flex items-start gap-2 text-sm text-gray-600"
                            >
                              <span className="w-1 h-1 rounded-full bg-gray-400 mt-2 flex-shrink-0" />
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}

                {activeSection === "events" && (
                  <div className="space-y-3">
                    {card.eventBenefits.length > 0 ? (
                      <>
                        {card.eventBenefits.map((evt, i) => (
                          <div
                            key={i}
                            className="p-4 bg-orange-50 border border-orange-100 rounded-xl flex items-start gap-3"
                          >
                            <TrendingUp className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
                            <div>
                              <p className="text-sm text-orange-800 font-normal">
                                {evt}
                              </p>
                              <p className="text-xs text-orange-600 mt-1">
                                이벤트 기간: 2025.03.01 ~ 2025.05.31
                              </p>
                            </div>
                          </div>
                        ))}
                      </>
                    ) : (
                      <div className="p-6 bg-gray-50 rounded-xl text-sm text-gray-500">
                        현재 진행 중인 이벤트 혜택이 없습니다.
                      </div>
                    )}

                    <div className="p-4 bg-gray-50 rounded-xl flex items-start gap-3">
                      <Info className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-gray-500">
                        이벤트 혜택은 조기 종료될 수 있습니다. 자세한 내용은
                        카드사 공식 페이지를 확인해주세요.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right */}
          <div className="space-y-4">
            <div className="bg-[#1B3D7B] rounded-2xl p-5 sticky top-24">
              <p className="text-white/80 text-xs mb-2">바로 발급 신청</p>
              <h3 className="text-white font-normal mb-3">{card.name}</h3>
              <button className="w-full py-2.5 bg-[#0ABFA3] text-white rounded-xl text-sm font-normal hover:bg-[#099d86] transition-all flex items-center justify-center gap-2">
                발급 신청하기 <ExternalLink className="w-3.5 h-3.5" />
              </button>
              <p className="text-white/40 text-[10px] mt-2 text-center">
                카드사 공식 페이지로 이동합니다
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
