import { useState, useMemo, useEffect } from "react";
import { useParams, Link, useSearchParams } from "react-router";
import {
Heart,
GitCompare,
ChevronRight,
CheckCircle,
AlertCircle,
Info,
TrendingUp,
Share2,
ExternalLink,
Monitor,
Shirt,
ShoppingBag,
Building2,
Bus,
Car,
Tv,
Dumbbell,
Smartphone,
Film,
Zap,
Store,
Coffee,
Package,
Utensils,
Globe,
Plane,
BookOpen,
Plus,
MoreHorizontal,
ChevronDown,
ChevronUp,
} from "lucide-react";
import { getCardDetail } from "../../api/card";
import { CardDetailItem } from "../../types/card";
import { api } from "../../api/axios";

const categoryBenefitMap: Record<string, string[]> = {
  온라인쇼핑: ["쇼핑", "온라인쇼핑"],
  "패션/뷰티": ["쇼핑", "뷰티", "패션"],
  "슈퍼마켓/생활잡화": ["마트", "슈퍼마켓", "생활잡화"],
  "백화점/아울렛": ["마트", "쇼핑", "백화점", "아울렛"],
  "대중교통/택시": ["교통", "대중교통", "택시"],
  "자동차/주유": ["주유", "자동차"],
  반려동물: ["반려동물"],
  "구독/스트리밍": ["구독", "스트리밍"],
  "레저/스포츠": ["레저", "스포츠"],
  "페이/간편결제": ["페이", "간편결제"],
  "문화/엔터": ["영화", "문화", "엔터"],
  생활비: ["통신", "생활비"],
  편의점: ["편의점"],
  "커피/카페/베이커리": ["카페", "커피", "베이커리"],
  배달: ["배달"],
  외식: ["외식"],
  "여행/숙박": ["여행", "숙박"],
  항공: ["항공"],
  해외: ["해외"],
  "교육/육아": ["교육", "육아"],
  의료: ["의료", "병원", "약국"],
  };

  const categoryIconMap: Record<string, React.ElementType> = {
    온라인쇼핑: Monitor,
    "패션/뷰티": Shirt,
    "슈퍼마켓/생활잡화": ShoppingBag,
    "백화점/아울렛": Building2,
    "대중교통/택시": Bus,
    "자동차/주유": Car,
    반려동물: Heart,
    "구독/스트리밍": Tv,
    "레저/스포츠": Dumbbell,
    "페이/간편결제": Smartphone,
    "문화/엔터": Film,
    생활비: Zap,
    편의점: Store,
    "커피/카페/베이커리": Coffee,
    배달: Package,
    외식: Utensils,
    "여행/숙박": Globe,
    항공: Plane,
    해외: Globe,
    "교육/육아": BookOpen,
    의료: Plus,
    기타: MoreHorizontal,
    };

    type Benefit = CardDetailItem["benefits"][number];

    type BenefitGroup = {
      categoryName: string;
      titles: {
        uiTitle: string;
        effectiveRateText: string;

        maxLimit: number | null;
        maxLimitUnit: string | null;

        groupMaxLimit: number | null;
        groupMaxLimitUnit: string | null;

        contents: string[];
        targetMerchants: string | null;

        benefitValue: number | null;
        benefitUnit: string | null;
      }[];
    };

    const conditionKeywords = ["이상", "이하", "회", "자동납부"];
    //const issueKeywords = ["이상", "만 ", "세", "국민", "소득", "등급", "신용"];
    //const cautionKeywords = ["제외", "불가", "적용되지", "단,", "주의", "경우", "중복"];
    //const eventKeywords = ["이벤트", "신규", "특별", "프로모션"];

    function isBenefitMatched(benefitCategory: string, selectedCategory: string) {
    const mapped = categoryBenefitMap[selectedCategory] ?? [selectedCategory];
    if (!mapped.length) return false;

    return mapped.some((m) =>
    benefitCategory.toLowerCase().includes(m.toLowerCase()),
    );
    }

    function getCategoryIcon(categoryName: string) {
    return categoryIconMap[categoryName] ?? MoreHorizontal;
    }

    function getBenefitNumber(value: string | null | undefined) {
    const matched = String(value ?? "").match(/[\d.]+/);
    return matched ? Number(matched[0]) : 0;
    }

    function getBenefitBadge(value: string | null | undefined) {
    const text = String(value ?? "");
    if (text.includes("%")) return "할인/캐시백";
    if (text.includes("원")) return "캐시백";
    return "혜택";
    }

    function formatBenefitValue(value: string | null | undefined) {
    const text = String(value ?? "").trim();
    if (!text) return "";

    return text.replace(/(\d+)\.0+(?=\D|$)/g, "$1").replace(/(\d+\.\d*?[1-9])0+(?=\D|$)/g, "$1");
    }

    function formatNumberWithComma(value: number | string | null | undefined) {
    if (value === null || value === undefined || value === "") return "";

    const text = String(value);
    return text.replace(/\d+(?:\.\d+)?/g, (matched) => {
    const [integerPart, decimalPart] = matched.split(".");
    const formattedInteger = Number(integerPart).toLocaleString("ko-KR");
    return decimalPart ? `${formattedInteger}.${decimalPart}` : formattedInteger;
    });
    }

    function formatDisplayValue(value: string | null | undefined) {
    return formatNumberWithComma(formatBenefitValue(value));
    }



    function uniqueTexts(items: string[]) {
    return Array.from(new Set(items.map((v) => v.trim()).filter(Boolean)));
    }

    function extractByKeywords(benefits: Benefit[], keywords: string[]) {
    return uniqueTexts(
    benefits
    .flatMap((b) => [b.uiTitle, b.uiContent])
    .filter((text): text is string => Boolean(text))
    .filter((text) => keywords.some((keyword) => text.includes(keyword)))
    .map((text) => formatNumberWithComma(text)),
    );
    }

    function formatMoney(value: number | null | undefined) {
    return value ? `${value.toLocaleString()}원` : "한도 없음";
    }
    
    function formatLimit(
      maxLimit?: number | null,
      maxLimitUnit?: string | null,
      groupMaxLimit?: number | null,
      groupMaxLimitUnit?: string | null
    ) {
      if (groupMaxLimit) {
        return `통합 ${groupMaxLimit.toLocaleString()}${groupMaxLimitUnit ?? ""}`;
      }

      if (maxLimit) {
        return `${maxLimit.toLocaleString()}${maxLimitUnit ?? ""}`;
      }

      return "한도 없음";
    }

    function containsHtmlTable(content: string) {
      return content.includes("<table");
    }

    function parseNoticeSections(content: string) {
      const sections: {
        title: string;
        items: {
          content: string;
        }[];
      }[] = [];

      const lines = content.split("\n");

      let currentSection: {
        title: string;
        items: {
          subtitle?: string;
          content: string;
        }[];
      } | null = null;

      for (const rawLine of lines) {
        const line = rawLine.trim();

        if (!line) continue;

        const sectionMatch = line.match(/^\[(.+)\]$/);

        if (sectionMatch) {
          currentSection = {
            title: sectionMatch[1],
            items: [],
          };

          sections.push(currentSection);
          continue;
        }

        if (!currentSection) continue;

        currentSection.items.push({
          content: line,
        });
      }

      return sections;
    }

    function splitParagraphs(content: string) {
      return content
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => line.replace(/^-+\s*/, ""));
    }

    function groupBenefits(benefits: Benefit[]): BenefitGroup[] {
    const categoryMap = new Map<string, Map<string, BenefitGroup["titles"][number]>>();

      benefits.forEach((benefit) => {
      const categoryName = benefit.categoryName || "기타";
      const uiTitle = benefit.uiTitle || "상세 혜택";

      if (!categoryMap.has(categoryName)) {
      categoryMap.set(categoryName, new Map());
      }

      const titleMap = categoryMap.get(categoryName)!;

      if (!titleMap.has(uiTitle)) {
        titleMap.set(uiTitle, {
          uiTitle,
          effectiveRateText: benefit.effectiveRateText || "",

          benefitValue: benefit.benefitValue ?? null,
          benefitUnit: benefit.benefitUnit ?? null,

          maxLimit: benefit.maxLimit ?? null,
          maxLimitUnit: benefit.maxLimitUnit ?? null,

          groupMaxLimit: benefit.groupMaxLimit ?? null,
          groupMaxLimitUnit: benefit.groupMaxLimitUnit ?? null,

          contents: [],
          targetMerchants: benefit.targetMerchants ?? null,
        });
      }

      const group = titleMap.get(uiTitle)!;

      if (!group.effectiveRateText && benefit.effectiveRateText) {
      group.effectiveRateText = benefit.effectiveRateText;
      }

      if ((benefit.maxLimit ?? 0) > (group.maxLimit ?? 0)) {
      group.maxLimit = benefit.maxLimit ?? null;
      }

      if (benefit.uiContent) {
      group.contents.push(benefit.uiContent);
      }
      });

      return Array.from(categoryMap.entries())
      .map(([categoryName, titleMap]) => ({
      categoryName,
      titles: Array.from(titleMap.values()).map((title) => ({
      ...title,
      contents: uniqueTexts(title.contents),
      })),
      }))
      .sort((a, b) => a.categoryName.localeCompare(b.categoryName, "ko-KR"));
      }

      export function CardDetail() {
      const { id } = useParams();
      const cardId = id;
      const [searchParams] = useSearchParams();

      const handleApplyClick = async () => {
        if (!card?.cardId || !card?.linkUrl) return;

        try {
          await api.post(`/api/cards/${card.cardId}/click-url`);
        } catch (error) {
          console.error("urlClick 집계 실패", error);
        }

        window.open(card.linkUrl, "_blank", "noopener,noreferrer");
      };

const [card, setCard] = useState<CardDetailItem | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
const [favorite, setFavorite] = useState(false);
const [activeSection, setActiveSection] = useState<
"benefits" |
"conditions" |
"events"
>("benefits")
const [openBenefitCategories, setOpenBenefitCategories] = useState<Record<string, boolean>>({});

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
  } catch (error) {
  console.error(error);
  setError("카드 상세 정보를 불러오지 못했습니다.");
  } finally {
  setLoading(false);
  }
};

fetchCardDetail();
}, [cardId]);

const typeLabel =
card?.cardType === "신용" || card?.cardType === "CREDIT"
? "신용카드"
: "체크카드";

const isVerticalCard =
  card?.company?.includes("삼성") ||
  card?.company?.includes("현대");

const mainBenefits = useMemo(
  () =>
    (card?.benefits ?? []).filter(
      (benefit) => benefit.rowType !== "안내",
    ),
  [card],
);

const orderedBenefits = useMemo(() => {
if (!card?.benefits) return [];

if (selectedCategories.length === 0) return mainBenefits;

return [...mainBenefits].sort((a, b) => {
const aMatched = selectedCategories.some((cat) =>
isBenefitMatched(a.categoryName, cat),
);
const bMatched = selectedCategories.some((cat) =>
isBenefitMatched(b.categoryName, cat),
);

if (aMatched && !bMatched) return -1;
if (!aMatched && bMatched) return 1;
return 0;
});
}, [card, selectedCategories]);

const matchedSelectedCategories = selectedCategories.filter((selected) =>
card?.benefits?.some((benefit) =>
isBenefitMatched(benefit.categoryName, selected),
),
);

const topBenefits = useMemo(() => {
return orderedBenefits
.filter((benefit) => benefit.categoryName !== "기타")
.sort((a, b) => {
const limitDiff = (b.maxLimit ?? 0) - (a.maxLimit ?? 0);
if (limitDiff !== 0) return limitDiff;
return getBenefitNumber(b.effectiveRateText) - getBenefitNumber(a.effectiveRateText);
})
.slice(0, 3);
}, [orderedBenefits]);

const benefitGroups = useMemo(
() => groupBenefits(orderedBenefits),
[orderedBenefits],
);

useEffect(() => {
setOpenBenefitCategories((prev) => {
const next = { ...prev };
benefitGroups.forEach((group) => {
if (next[group.categoryName] === undefined) {
next[group.categoryName] = false;
}
});
return next;
});
}, [benefitGroups]);

const toggleBenefitCategory = (categoryName: string) => {
setOpenBenefitCategories((prev) => ({
...prev,
[categoryName]: !prev[categoryName],
}));
};

const limitRows = useMemo(() => {
return (card?.benefits ?? []).filter(
(benefit) =>
(benefit.uiTitle?.includes("통합") ||
benefit.uiTitle?.includes("한도")) &&
benefit.maxLimit,
);
}, [card]);

if (loading) {
return (
<div className="bg-[#F8FAFC] min-h-screen p-10 text-sm text-gray-500">
  카드 상세 정보를 불러오는 중...
</div>
);
}

if (error || !card) {
return (
<div className="bg-[#F8FAFC] min-h-screen p-10 text-sm text-gray-500">
  카드 상세 정보를 불러오지 못했습니다.
</div>
);
}

return (
<div className="bg-[#F8FAFC] min-h-screen">
  <div className="bg-white border-b border-gray-300">
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
        <span className="text-gray-700">{card.cardName}</span>
      </div>
    </div>
  </div>

  <div className="max-w-[1280px] mx-auto px-6 py-8">
    <div className="grid grid-cols-[1fr_320px] gap-8">
      <div className="space-y-6">
        <div className="bg-white rounded-2xl border border-gray-300 p-8">
          <div className="flex gap-8 items-start">
            <div className="flex flex-col items-center gap-4">
              <div
                className="w-[230px] h-[145px] rounded-2xl bg-gray-100 border border-gray-300 overflow-hidden flex items-center justify-center shadow-sm">
                {card.imageUrl ? (
                  <img
                    src={card.imageUrl}
                    alt={card.cardName}
                    className="w-full h-full object-cover"
                  />
                ) : (
                <div className="text-sm text-gray-400">카드 이미지 없음</div>
                )}
              </div>

              <div className="flex gap-2">
                <button onClick={()=> setFavorite(!favorite)}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-xl border text-sm font-normal
                  transition-all ${
                  favorite
                  ? "bg-red-50 border-red-300 text-red-500"
                  : "border-gray-300 text-gray-600 hover:border-red-300 hover:text-red-400"
                  }`}
                  >
                  <Heart className={`w-4 h-4 ${favorite ? "fill-red-500" : "" }`} />
                  {favorite ? "즐겨찾기 됨" : "즐겨찾기"}
                </button>

                <Link to={ selectedCategories.length> 0
                ? `/compare?cards=${card.cardId}&benefits=${encodeURIComponent(
                selectedCategories.join(","),
                )}`
                : `/compare?cards=${card.cardId}`
                }
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-300 text-sm
                font-normal text-gray-600 hover:border-[#1B3D7B] hover:text-[#1B3D7B] transition-all"
                >
                <GitCompare className="w-4 h-4" />
                비교하기
                </Link>

                <button
                  className="p-2 rounded-xl border border-gray-300 text-gray-400 hover:text-[#1B3D7B] hover:border-[#1B3D7B] transition-all">
                  <Share2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm text-gray-500">{card.company}</span>
                <span className={`text-xs px-2 py-0.5 rounded font-normal ${ typeLabel==="신용카드"
                  ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600" }`}>
                  {typeLabel}
                </span>
                {card.network && (
                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">
                  {card.network}
                </span>
                )}
              </div>

              <h1 className="text-2xl text-gray-900 mb-5">{card.cardName}</h1>

              <div className="grid grid-cols-3 gap-3 mb-5">
                {[
                {
                label: "연회비",
                value:
                card.annualFeeDomBasic === 0
                ? "없음"
                : `${card.annualFeeDomBasic.toLocaleString()}원`,
                highlight: card.annualFeeDomBasic === 0,
                },
                {
                label: "전월실적",
                value:
                card.minPerformance === 0
                ? "무실적"
                : `${(card.minPerformance / 10000).toFixed(0)}만원 이상`,
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
                <div key={spec.label} className="p-3 bg-gray-100 rounded-xl">
                  <div className="text-xs text-gray-500 mb-0.5">{spec.label}</div>
                  <div className={`font-normal ${ spec.highlight ? "text-green-600" : "text-gray-900" }`}>
                    {spec.value}
                  </div>
                </div>
                ))}
              </div>

              {matchedSelectedCategories.length > 0 && (
              <div className="p-4 rounded-xl border border-[#6667AA]/30 bg-[#6667AA]/5">
                <div className="text-xs text-[#6667AA] font-normal mb-2">
                  조회에서 선택한 혜택
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {matchedSelectedCategories.map((cat) => (
                  <span key={cat}
                    className="text-xs bg-white text-[#6667AA] border border-[#6667AA]/30 px-2.5 py-1 rounded-full font-normal">
                    {cat}
                  </span>
                  ))}
                </div>
              </div>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-gray-300">
          <div className="flex border-b border-gray-300">
            {[
            { key: "benefits", label: "주요 혜택" },
            { key: "conditions", label: "이용 조건" },
            { key: "events", label: "이벤트" },
            ].map((tab) => (
            <button key={tab.key} onClick={()=> setActiveSection(tab.key as typeof activeSection)}
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
                {topBenefits.map((benefit, i) => {
                const Icon = getCategoryIcon(benefit.categoryName);
                const highlighted = selectedCategories.some((cat) =>
                isBenefitMatched(benefit.categoryName, cat),
                );

                return (
                <div key={`${benefit.categoryName}-${benefit.uiTitle}-${i}`} className={`p-4 border
                  rounded-xl transition-all shadow-sm ${ highlighted
                  ? "border-[#6667AA]/60 bg-gradient-to-br from-[#6667AA]/12 to-white"
                  : "border-[#1B3D7B]/25 bg-gradient-to-br from-[#1B3D7B]/8 to-white hover:border-[#1B3D7B]/50 hover:shadow-md"
                  }`}>
                  <div
                    className="w-10 h-10 rounded-xl bg-white/80 border border-[#1B3D7B]/15 flex items-center justify-center mb-3">
                    <Icon className="w-5 h-5 text-[#1B3D7B]" />
                  </div>
                  <div className="text-xs text-gray-500 mb-1">
                    {benefit.categoryName}
                  </div>
                  <div className="font-normal text-[#1B3D7B]">
                    {formatDisplayValue(benefit.effectiveRateText) || "정보 없음"}
                  </div>
                  <div
                    className="inline-flex mt-1 text-[10px] px-1.5 py-0.5 rounded font-normal bg-blue-50 text-blue-600">
                    {getBenefitBadge(formatDisplayValue(benefit.effectiveRateText))}
                  </div>
                </div>
                );
                })}
              </div>

              <div className="overflow-hidden rounded-xl border border-gray-300">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-100 text-left">
                      <th className="px-4 py-3 text-xs font-normal text-gray-500 w-[20%]">
                        혜택 분류
                      </th>
                      <th className="px-4 py-3 text-xs font-normal text-gray-500 w-[20%]">
                        할인대상
                      </th>
                      <th className="px-4 py-3 text-xs font-normal text-gray-500 w-[45%]">
                        혜택내용
                      </th>
                      <th className="px-4 py-3 text-xs font-normal text-gray-500 text-center w-[15%]">
                        혜택
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {benefitGroups.map((group) => {
                    const Icon = getCategoryIcon(group.categoryName);
                    const highlighted = selectedCategories.some((cat) =>
                    isBenefitMatched(group.categoryName, cat),
                    );
                    const isOpen = openBenefitCategories[group.categoryName] ?? false;
                    const representative = group.titles[0];
                    const totalCount = group.titles.reduce(
                    (sum, title) => sum + Math.max(title.contents.length, 1),
                    0,
                    );

                    return (
                    <>
                      <tr key={`${group.categoryName}-summary`} onClick={()=>
                        toggleBenefitCategory(group.categoryName)}
                        className={`border-t cursor-pointer transition-colors ${
                        highlighted
                        ? "bg-[#6667AA]/3 border-[#6667AA]/25"
                        : "border-gray-300 hover:bg-gray-100/60"
                        }`}
                        >
                        <td className="px-4 py-4 align-top">
                          <div className="flex items-start gap-2">
                            <Icon className="w-4 h-4 mt-0.5 text-[#1B3D7B]" />
                            <div>
                              <div className="text-gray-900 font-normal">
                                {group.categoryName}
                              </div>
                              {highlighted && (
                              <div className="text-[10px] text-[#6667AA] mt-1">
                                선택 혜택 우선 노출
                              </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 align-top text-xs text-gray-600">
                          {representative?.targetMerchants ?? "-"}
                        </td>
                        <td className="px-4 py-4 align-top">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <div className="text-xs text-gray-800">
                                {representative?.uiTitle || "상세 혜택"}
                              </div>
                              <div className="text-[11px] text-gray-400 mt-1">
                                총 {totalCount}개 혜택 보기
                              </div>
                            </div>
                            {isOpen ? (
                            <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            ) : (
                            <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4 text-center align-top">
                        <span
                          className={`text-sm font-normal ${
                            representative?.benefitUnit === "%"
                              ? "text-[#1B3D7B]"
                              : representative?.benefitUnit === "원"
                              ? "text-green-600"
                              : "text-gray-400"
                          }`}
                        >
                          {representative?.benefitUnit === "원"
                            ? `${Number(representative?.benefitValue ?? 0).toLocaleString()}원`
                            : formatDisplayValue(representative?.effectiveRateText) || "–"}
                        </span>
                      </td>
                      </tr>

                      {isOpen &&
                      group.titles.map((title, index) => {
                      const conditionItems = title.contents.filter((content) =>
                      conditionKeywords.some((keyword) =>
                      content.includes(keyword),
                      ),
                      );

                      return (
                      <tr key={`${group.categoryName}-${title.uiTitle}-${index}`}
                        className="border-t border-gray-300 bg-white hover:bg-gray-100/60 transition-colors">
                        <td className="px-4 py-4 align-top">
                          <div className="pl-6 text-xs text-gray-400">
                            상세
                          </div>
                        </td>
                        <td className="px-4 py-4 align-top text-xs text-gray-600">
                          {title.targetMerchants ?? "-"}
                        </td>
                        <td className="px-4 py-4 align-top">
                          <div className="text-xs text-gray-700 leading-relaxed">
                            <div className="mb-1 text-gray-800">
                              {title.uiTitle}
                            </div>
                            <div className="space-y-0.5">
                              {title.contents.map((content) => (
                                <div key={content}>
                                  {containsHtmlTable(content) ? (
                                    <div
                                      className="benefit-html-content"
                                      dangerouslySetInnerHTML={{
                                        __html: content,
                                      }}
                                    />
                                  ) : (
                                    <div className="whitespace-pre-line">
                                      {content}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-center align-top">
                          <span
                            className={`text-sm font-normal ${
                              title.benefitUnit === "%"
                                ? "text-[#1B3D7B]"
                                : title.benefitUnit === "원"
                                ? "text-green-600"
                                : "text-gray-400"
                            }`}
                          >
                            {title.benefitUnit === "원"
                              ? `${Number(title.benefitValue ?? 0).toLocaleString()}원`
                              : formatDisplayValue(title.effectiveRateText) || "–"}
                          </span>
                        </td>
                      </tr>
                      );
                      })}
                    </>
                    );
                    })}
                  </tbody>
                </table>
              </div>
            </>
            )}

            {activeSection === "conditions" && (
              <div className="space-y-6">
                {card.notices.map((notice, noticeIndex) =>
                  parseNoticeSections(notice.noticeContent).map(
                    (section, sectionIndex) => (
                      <div
                        key={`${noticeIndex}-${sectionIndex}`}
                        className="
                          bg-slate-50
                          border
                          border-slate-200
                          rounded-2xl
                          p-5
                        "
                      >
                        <div className="flex items-center gap-2 mb-5">
                          <Info className="w-4 h-4 text-blue-500" />
                          <h3 className="text-base text-gray-900">
                            {section.title}
                          </h3>
                        </div>

                        <div className="space-y-4">
                          {section.items.map((item, itemIndex) => (
                            <div
                              key={itemIndex}
                              className="
                                bg-white
                                border
                                border-slate-200
                                rounded-xl
                                p-4
                              "
                            >
                              {containsHtmlTable(item.content) ? (
                                <div
                                  className="notice-table"
                                  dangerouslySetInnerHTML={{
                                    __html: item.content,
                                  }}
                                />
                              ) : (
                                <div className="space-y-2">
                                  {splitParagraphs(item.content).map(
                                    (paragraph, idx) => (
                                      <div
                                        key={idx}
                                        className="
                                          flex
                                          items-start
                                          gap-2
                                        "
                                      >
                                        <div
                                          className="
                                            w-1.5
                                            h-1.5
                                            rounded-full
                                            bg-slate-400
                                            mt-2
                                            flex-shrink-0
                                          "
                                        />

                                        <p
                                          className="
                                            text-sm
                                            text-gray-600
                                            leading-relaxed
                                          "
                                        >
                                          {paragraph}
                                        </p>
                                      </div>
                                    )
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  )
                )}
              </div>
            )}

            {activeSection === "events" && (
            <div className="space-y-3">
              {card.events.length > 0 ? (
              card.events.map((event, i) => (
              <div key={`${event.eventTitle}-${i}`}
                className="p-4 bg-orange-50 border border-orange-200 rounded-xl">
                <div className="font-medium text-orange-800">
                  {event.eventTitle}
                </div>

                <div className="text-sm text-orange-700 mt-2">
                  {event.eventContent}
                </div>

                {event.startDate && (
                <div className="text-xs text-orange-600 mt-2">
                  기간 :
                  {event.startDate}
                  {" ~ "}
                  {event.endDate ?? "미정"}
                </div>
                )}

                {event.eventLink && (
                <a href={event.eventLink} target="_blank" rel="noreferrer"
                  className="text-xs text-blue-600 underline mt-2 block">
                  이벤트 바로가기
                </a>
                )}
              </div>
              ))
              ) : (
              <div className="p-6 bg-gray-100 rounded-xl text-sm text-gray-500">
                현재 진행 중인 이벤트 혜택이 없습니다.
              </div>
              )}

              <div className="p-4 bg-gray-100 rounded-xl flex items-start gap-3">
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

      <div className="space-y-4">
        <div className="bg-[#1B3D7B] rounded-2xl p-5 sticky top-24">
          <p className="text-white/80 text-xs mb-2">바로 발급 신청</p>
          <h3 className="text-white font-normal mb-3">{card.cardName}</h3>
          <button
            onClick={handleApplyClick}
            disabled={!card?.linkUrl}
            className={`w-full py-2.5 rounded-xl text-sm font-normal transition-all flex items-center justify-center gap-2 ${
              card?.linkUrl
                ? "bg-[#0ABFA3] text-white hover:bg-[#099d86]"
                : "bg-white/20 text-white/50 cursor-not-allowed"
            }`}
          >
            발급 신청하기
            <ExternalLink className="w-3.5 h-3.5" />
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