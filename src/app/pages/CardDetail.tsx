import { useState, useMemo, useEffect, type ReactNode } from "react";
import { useParams, Link, useSearchParams } from "react-router";
import {
  Heart,
  GitCompare,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Share2,
  ExternalLink,
  Monitor,
  ShoppingBag,
  Bus,
  Tv,
  Smartphone,
  Film,
  Zap,
  Store,
  Coffee,
  Package,
  Globe,
  Plane,
  BookOpen,
  Dumbbell,
  Plus,
  MoreHorizontal,
  Building2,
  Shirt,
  Car,
  ShoppingCart,
  Star,
  TrendingUp,
  Info,
} from "lucide-react";
import { getCardDetail } from "../../api/card";
import { CardDetailItem } from "../../types/card";
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

function getCategoryIcon(category: string) {
  const cls = "w-5 h-5 text-gray-500";
  const map: Record<string, ReactNode> = {
    온라인쇼핑: <Monitor className={cls} />,
    "패션/뷰티": <Shirt className={cls} />,
    "슈퍼마켓/생활잡화": <ShoppingBag className={cls} />,
    "백화점/아울렛": <Building2 className={cls} />,
    "대중교통/택시": <Bus className={cls} />,
    "자동차/주유": <Car className={cls} />,
    반려동물: <Heart className={cls} />,
    "구독/스트리밍": <Tv className={cls} />,
    "레저/스포츠": <Dumbbell className={cls} />,
    "페이/간편결제": <Smartphone className={cls} />,
    "문화/엔터": <Film className={cls} />,
    생활비: <Zap className={cls} />,
    편의점: <Store className={cls} />,
    "커피/카페/베이커리": <Coffee className={cls} />,
    배달: <Package className={cls} />,
    외식: <ShoppingCart className={cls} />,
    "여행/숙박": <Globe className={cls} />,
    항공: <Plane className={cls} />,
    해외: <Globe className={cls} />,
    "교육/육아": <BookOpen className={cls} />,
    의료: <Plus className={cls} />,
  };
  return map[category] ?? <MoreHorizontal className={cls} />;
}

interface TitleGroup {
  title: string;
  valueText: string;
  maxLimit: number | null;
  contents: string[];
}

interface CategoryGroup {
  category: string;
  preview: string;
  titleGroups: TitleGroup[];
}

const normalizeNetwork = (
  network: string | null | undefined,
): "VISA" | "Mastercard" | "BC" | "신한" => {
  if (network === "VISA") return "VISA";
  if (network === "Mastercard") return "Mastercard";
  if (network === "BC") return "BC";
  if (network === "신한") return "신한";
  return "VISA";
};

export function CardDetail() {
  const { id } = useParams();
  const cardId = id;
  const [searchParams] = useSearchParams();

  const [card, setCard] = useState<CardDetailItem | null>(null);
  //const [scores, setScores] = useState<CardScore | null>(null);
  //const [personaType, setPersonaType] = useState<PersonaType>("STUDENT");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [favorite, setFavorite] = useState(false);
  const [openCategories, setOpenCategories] = useState<Set<string>>(new Set());

  const selectedCategories = (
    searchParams.get("benefits")?.split(",").filter(Boolean) || []
  ).map((v) => decodeURIComponent(v));

  useEffect(() => {
    const fetchCardDetail = async () => {
      if (!cardId) return;

      try {
        setLoading(true);
        setError(null);

        const detailData = await getCardDetail(cardId);
        setCard(detailData);

        //const scoreData = await getCardScores(cardId, personaType);
        //setScores(scoreData);

        //addRecentlyViewed(cardId);
      } catch (error) {
        console.error(error);
        setError("카드 상세 정보를 불러오지 못했습니다.");
      } finally {
        setLoading(false);
      }
    };

    fetchCardDetail();
  }, [cardId]);

  const typeLabel = card?.cardType === "신용" ? "신용카드" : "체크카드";

  const matchedSelectedCategories = selectedCategories.filter((selected) =>
    card?.benefits?.some((benefit) =>
      isBenefitMatched(benefit.categoryName, selected),
    ),
  );

  // Group benefits by categoryName (excluding 기타), then by benefitTitle
  const benefitGroups = useMemo((): CategoryGroup[] => {
    if (!card?.benefits) return [];

    const seenCats = new Set<string>();
    const catOrder: string[] = [];
    card.benefits.forEach((b) => {
      if (b.categoryName !== "기타" && !seenCats.has(b.categoryName)) {
        seenCats.add(b.categoryName);
        catOrder.push(b.categoryName);
      }
    });

    return catOrder.map((cat) => {
      const catItems = card.benefits.filter((b) => b.categoryName === cat);

      const titleMap = new Map<
        string,
        { valueText: string; maxLimit: number | null; contents: string[] }
      >();
      catItems.forEach((item) => {
        const title = item.benefitTitle || item.benefitContent || "기타 혜택";

        if (!titleMap.has(title)) {
          titleMap.set(title, {
            valueText: item.benefitValueText || "",
            maxLimit: item.maxLimit,
            contents: [],
          });
        }

        const content = item.benefitContent;

        if (content && !titleMap.get(title)!.contents.includes(content)) {
          titleMap.get(title)!.contents.push(content);
        }
      });

      const titleGroups: TitleGroup[] = Array.from(titleMap.entries()).map(
        ([title, data]) => ({ title, ...data }),
      );

      return { category: cat, preview: titleGroups[0]?.title || "", titleGroups };
    });
  }, [card]);

  // Auto-open matched categories
  useEffect(() => {
  if (benefitGroups.length === 0 || matchedSelectedCategories.length === 0) return;

  setOpenCategories((prev) => {
    const next = new Set(prev);

    benefitGroups.forEach((g) => {
      if (matchedSelectedCategories.some((sel) => isBenefitMatched(g.category, sel))) {
        next.add(g.category);
      }
    });

    return next;
  });
}, [benefitGroups, matchedSelectedCategories]);

  const toggleCategory = (cat: string) => {
    setOpenCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const eventBenefits: string[] = [];

  if (loading) {
    return (
      <div className="bg-[#F8FAFC] min-h-screen flex items-center justify-center">
        <div className="text-sm text-gray-400">카드 상세 정보를 불러오는 중...</div>
      </div>
    );
  }

  if (error || !card) {
    return (
      <div className="bg-[#F8FAFC] min-h-screen flex items-center justify-center">
        <div className="text-sm text-gray-400">카드 상세 정보를 불러오지 못했습니다.</div>
      </div>
    );
  }

  return (
    <div className="bg-[#F8FAFC] min-h-screen">
      {/* Breadcrumb */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-[1280px] mx-auto px-6 py-3">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Link to="/" className="hover:text-[#1B3D7B]">홈</Link>
            <ChevronRight className="w-3 h-3" />
            <Link to="/cards" className="hover:text-[#1B3D7B]">카드 조회</Link>
            <ChevronRight className="w-3 h-3" />
            <span className="text-gray-700">{card.cardName}</span>
          </div>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8">
        <div className="grid grid-cols-[1fr_320px] gap-8">

          {/* ── Left column ── */}
          <div className="space-y-5">

            {/* Hero */}
            <div className="bg-white rounded-2xl border border-gray-100 p-8">
  <div className="flex gap-8 items-start">
    <div className="flex flex-col items-center gap-4">
      {card.imageUrl ? (
  <div className="w-72 h-[172px] flex items-center justify-center flex-shrink-0">
    <img
      src={card.imageUrl}
      alt={card.cardName}
      className="max-w-full max-h-full object-contain drop-shadow-md"
      loading="lazy"
    />
  </div>
) : (
  <CardVisual
    card={{
      id: 1,
      name: card.cardName,
      issuer: `${card.company}카드`,
      type: card.cardType === "신용" ? "credit" : "debit",
      network: normalizeNetwork(card.network),
      annualFee: card.annualFeeDomBasic,
      minSpending: card.minPerformance,
      maxBenefit: card.totalMaxBenefit ?? 0,
      rating: 0,
      reviews: 0,
      popularity: 0,
      rank: 0,
      views: 0,
      clicks: 0,
      tags: [],
      color: "#111827",
      gradient: "linear-gradient(135deg, #111827 0%, #374151 100%)",
      benefits: [],
      eventBenefits: [],
    }}
    size="lg"
  />
)}

                  <div className="flex gap-2">
                    <button
                      onClick={() => setFavorite(!favorite)}
                      className={`flex items-center gap-1.5 px-4 py-2 rounded-xl border text-sm transition-all ${
                        favorite
                          ? "bg-red-50 border-red-200 text-red-500"
                          : "border-gray-200 text-gray-600 hover:border-red-200 hover:text-red-400"
                      }`}
                    >
                      <Heart className={`w-4 h-4 ${favorite ? "fill-red-500" : ""}`} />
                      {favorite ? "즐겨찾기 됨" : "즐겨찾기"}
                    </button>

                    <Link
                      to={
                        selectedCategories.length > 0
                          ? `/compare?cards=${card.cardId}&benefits=${encodeURIComponent(selectedCategories.join(","))}`
                          : `/compare?cards=${card.cardId}`
                      }
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-200 text-sm text-gray-600 hover:border-[#1B3D7B] hover:text-[#1B3D7B] transition-all"
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
                    <span className="text-sm text-gray-500">{card.company}카드</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-normal ${
                        card.cardType === "신용"
                          ? "bg-blue-50 text-blue-600"
                          : "bg-purple-50 text-purple-600"
                      }`}
                    >
                      {typeLabel}
                    </span>
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">
                      {card.network || "VISA"}
                    </span>
                  </div>

                  <h1 className="text-2xl text-gray-900 mb-3">{card.cardName}</h1>

                  <div className="flex items-center gap-1 mb-5">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <Star key={i} className="w-4 h-4 text-gray-200 fill-gray-200" />
                    ))}
                    <span className="text-gray-400 text-sm ml-2">평점 정보 없음</span>
                  </div>

                  <div className="grid grid-cols-3 gap-3 mb-5">
                    {[
                      {
                        label: "연회비",
                        value: card.annualFeeDomBasic === 0 ? "없음" : `${card.annualFeeDomBasic.toLocaleString()}원`,
                        highlight: card.annualFeeDomBasic === 0,
                      },
                      {
                        label: "전월실적",
                        value: card.minPerformance === 0 ? "무실적" : `${(card.minPerformance / 10000).toFixed(0)}만원 이상`,
                        highlight: card.minPerformance === 0,
                      },
                      {
                        label: "월 최대 혜택",
                        value: card.totalMaxBenefit
                          ? `${(card.totalMaxBenefit / 10000).toFixed(0)}만원`
                          : "정보 없음",
                        highlight: false,
                      },
                    ].map((spec) => (
                      <div key={spec.label} className="p-3 bg-gray-50 rounded-xl">
                        <div className="text-xs text-gray-500 mb-0.5">{spec.label}</div>
                        <div className={`font-normal ${spec.highlight ? "text-green-600" : "text-gray-900"}`}>
                          {spec.value}
                        </div>
                      </div>
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

                  {eventBenefits.length > 0 && (
                    <div className="p-3 mt-4 bg-orange-50 border border-orange-100 rounded-xl">
                      <div className="flex items-center gap-2 mb-1">
                        <TrendingUp className="w-3.5 h-3.5 text-orange-500" />
                        <span className="text-xs font-normal text-orange-600">이벤트 혜택</span>
                      </div>
                      {eventBenefits.map((e, i) => (
                        <p key={i} className="text-xs text-orange-700">{e}</p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* ── 주요혜택 accordion ── */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
              <div className="px-6 pt-5 pb-4 border-b border-gray-50">
                <h2 className="text-base font-semibold text-gray-900">주요혜택</h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  항목을 클릭하면 상세 혜택 내용을 확인할 수 있습니다
                </p>
              </div>

              {benefitGroups.length === 0 ? (
                <div className="px-6 py-10 text-sm text-gray-400 text-center">
                  혜택 정보가 없습니다.
                </div>
              ) : (
                <div>
                  {benefitGroups.map((group, idx) => {
                    const isOpen = openCategories.has(group.category);
                    const isMatched = matchedSelectedCategories.some((sel) =>
                      isBenefitMatched(group.category, sel),
                    );

                    return (
                      <div
                        key={group.category}
                        className={idx > 0 ? "border-t border-gray-50" : ""}
                      >
                        {/* Row header */}
                        <button
                          onClick={() => toggleCategory(group.category)}
                          className={`w-full flex items-center gap-4 px-6 py-4 text-left transition-colors ${
                            isOpen ? "bg-gray-50/70" : "hover:bg-gray-50/60"
                          }`}
                        >
                          {/* Icon box */}
                          <div
                            className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors ${
                              isMatched ? "bg-[#6667AA]/10" : isOpen ? "bg-gray-100" : "bg-gray-50"
                            }`}
                          >
                            {getCategoryIcon(group.category)}
                          </div>

                          {/* Text */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span
                                className={`text-sm font-semibold ${
                                  isMatched ? "text-[#6667AA]" : "text-gray-900"
                                }`}
                              >
                                {group.category}
                              </span>
                              {isMatched && (
                                <span className="text-[10px] bg-[#6667AA]/10 text-[#6667AA] px-1.5 py-0.5 rounded-full whitespace-nowrap">
                                  선택 혜택
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-gray-400 truncate">{group.preview}</p>
                          </div>

                          {/* Chevron */}
                          <div className="flex-shrink-0 text-gray-400">
                            {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </div>
                        </button>

                        {/* Expanded content */}
                        {isOpen && (
                          <div className="bg-gray-50/80 border-t border-gray-100 px-6 py-5">
                            <div className="space-y-5">
                              {group.titleGroups.map((tg, ti) => (
                                <div key={ti}>
                                  {/* Title + badges */}
                                  <div className="flex flex-wrap items-center gap-2 mb-2">
                                    <span className="text-sm text-gray-800">{tg.title}</span>
                                    {tg.valueText && (
                                      <span className="text-[11px] bg-[#1B3D7B]/10 text-[#1B3D7B] px-1.5 py-0.5 rounded">
                                        {tg.valueText}
                                      </span>
                                    )}
                                    {tg.maxLimit && (
                                      <span className="text-[11px] bg-green-50 text-green-700 px-1.5 py-0.5 rounded">
                                        최대 {tg.maxLimit.toLocaleString()}원
                                      </span>
                                    )}
                                  </div>

                                  {/* Content items */}
                                  <ul className="space-y-1.5">
                                    {tg.contents.map((content, ci) => (
                                      <li
                                        key={ci}
                                        className="flex items-start gap-2 text-sm text-gray-600 leading-relaxed"
                                      >
                                        <span className="text-gray-300 mt-px flex-shrink-0">–</span>
                                        <span>{content}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Notice footer */}
              <div className="px-6 py-4 border-t border-gray-50 flex items-start gap-2">
                <Info className="w-3.5 h-3.5 text-gray-300 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-gray-400">
                  혜택 정보는 카드사 사정에 의해 변경될 수 있습니다. 정확한 내용은 카드사 공식 홈페이지를 확인해주세요.
                </p>
              </div>
            </div>

          </div>

          {/* ── Right sidebar ── */}
          <div className="space-y-4">
            <div className="bg-[#1B3D7B] rounded-2xl p-5 sticky top-24">
              <p className="text-white/80 text-xs mb-2">바로 발급 신청</p>
              <h3 className="text-white font-normal mb-3">{card.cardName}</h3>
              <a
                href={card.linkUrl ?? "#"}
                target="_blank"
                rel="noreferrer"
                className="w-full py-2.5 bg-[#0ABFA3] text-white rounded-xl text-sm font-normal hover:bg-[#099d86] transition-all flex items-center justify-center gap-2"
              >
                발급 신청하기 <ExternalLink className="w-3.5 h-3.5" />
              </a>
              <p className="text-white/40 text-[10px] mt-2 text-center">
                카드사 공식 페이지로 이동합니다
              </p>
            </div>

            {/* Category quick nav */}
            {benefitGroups.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-100 p-5">
                <p className="text-xs font-semibold text-gray-500 mb-3">혜택 카테고리</p>
                <div className="flex flex-wrap gap-1.5">
                  {benefitGroups.map((g) => {
                    const isMatched = matchedSelectedCategories.some((sel) =>
                      isBenefitMatched(g.category, sel),
                    );
                    const isOpen = openCategories.has(g.category);
                    return (
                      <button
                        key={g.category}
                        onClick={() => toggleCategory(g.category)}
                        className={`text-xs px-2.5 py-1 rounded-full border transition-all ${
                          isMatched
                            ? "bg-[#6667AA]/10 border-[#6667AA]/20 text-[#6667AA]"
                            : isOpen
                            ? "bg-[#1B3D7B]/10 border-[#1B3D7B]/15 text-[#1B3D7B]"
                            : "bg-gray-50 border-gray-100 text-gray-500 hover:border-gray-200"
                        }`}
                      >
                        {g.category}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
