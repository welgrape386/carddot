import { Card } from "../data/mockData";

// ── 카드 ID별 고유 그라디언트 ────────────────────────────
const cardGradients: Record<number, string> = {
  // 삼성카드 — 블루 계열 (각기 다른 톤)
  1:  "linear-gradient(135deg, #0F2DA0 0%, #1557E8 55%, #5B8AFF 100%)",   // 밝은 전기 블루
  5:  "linear-gradient(135deg, #0D1B3E 0%, #1B3A7A 50%, #1E5799 100%)",   // 딥 네이비
  9:  "linear-gradient(135deg, #1428A0 0%, #6434CA 55%, #7C3AED 100%)",   // 블루→바이올렛
  10: "linear-gradient(135deg, #003B6F 0%, #005F9E 50%, #0080CC 100%)",   // 오션 네이비
  11: "linear-gradient(135deg, #2563EB 0%, #3B82F6 50%, #93C5FD 100%)",   // 스카이 블루
  // 신한카드 — 레드 계열 (다양한 레드)
  12: "linear-gradient(135deg, #991B1B 0%, #DC2626 50%, #EF4444 100%)",   // 정통 레드
  2:  "linear-gradient(135deg, #3B0000 0%, #7F1D1D 45%, #B91C1C 100%)",   // 딥 버건디
  6:  "linear-gradient(135deg, #C2410C 0%, #EA580C 55%, #FB923C 100%)",   // 오렌지레드
  13: "linear-gradient(135deg, #0C0A2E 0%, #1E0A3C 40%, #6B0000 75%, #C0392B 100%)", // 미드나잇→크림슨
  14: "linear-gradient(135deg, #BE185D 0%, #E11D48 50%, #FB7185 100%)",   // 로즈 핑크
  // 현대카드 — 다크 계열 (개성 강한 어두운 톤)
  3:  "linear-gradient(135deg, #18181B 0%, #27272A 50%, #52525B 100%)",   // 차콜 징크
  7:  "linear-gradient(135deg, #0F0F1A 0%, #1E1B4B 55%, #312E81 100%)",   // 미드나잇 인디고
  15: "linear-gradient(135deg, #1F2937 0%, #374151 50%, #6B7280 100%)",   // 스틸 그레이
  16: "linear-gradient(135deg, #052E16 0%, #14532D 50%, #15803D 100%)",   // 다크 포레스트
  17: "linear-gradient(135deg, #0D0000 0%, #3B0000 40%, #7B0000 70%, #B91C1C 100%)", // 블랙→딥레드
  // KB국민카드 — 앰버/골드 계열
  18: "linear-gradient(135deg, #92400E 0%, #B45309 50%, #D97706 100%)",   // 딥 앰버
  4:  "linear-gradient(135deg, #D97706 0%, #F59E0B 50%, #FCD34D 100%)",   // 브라이트 골드
  8:  "linear-gradient(135deg, #9A3412 0%, #C2410C 50%, #EA580C 100%)",   // 번트 오렌지
  19: "linear-gradient(135deg, #78350F 0%, #92400E 50%, #B45309 100%)",   // 다크 앰버
  20: "linear-gradient(135deg, #365314 0%, #4D7C0F 50%, #84CC16 100%)",   // 라임 (청춘)
  // NH농협카드 — 그린 계열
  21: "linear-gradient(135deg, #064E3B 0%, #047857 50%, #10B981 100%)",   // 에메랄드
  22: "linear-gradient(135deg, #14532D 0%, #15803D 50%, #22C55E 100%)",   // 포레스트 그린
  23: "linear-gradient(135deg, #134E4A 0%, #0F766E 50%, #0D9488 100%)",   // 틸 그린
  24: "linear-gradient(135deg, #166534 0%, #16A34A 55%, #4ADE80 100%)",   // 브라이트 세이지
  25: "linear-gradient(135deg, #1A2E05 0%, #365314 50%, #4D7C0F 100%)",   // 다크 올리브
  // 우리카드 — 블루 계열 (신선한 블루)
  26: "linear-gradient(135deg, #1D4ED8 0%, #2563EB 50%, #60A5FA 100%)",   // 로얄 블루
  27: "linear-gradient(135deg, #0C4A6E 0%, #0369A1 50%, #0284C7 100%)",   // 딥 오션
  28: "linear-gradient(135deg, #1E3A8A 0%, #1D4ED8 55%, #3B82F6 100%)",   // 사파이어
  29: "linear-gradient(135deg, #172554 0%, #1E3A8A 50%, #2563EB 100%)",   // 미드나잇 블루
  30: "linear-gradient(135deg, #0891B2 0%, #06B6D4 50%, #67E8F9 100%)",   // 스카이 시안
  // 하나카드 — 틸 계열
  31: "linear-gradient(135deg, #042F2E 0%, #115E59 50%, #0F766E 100%)",   // 다크 틸
  32: "linear-gradient(135deg, #0D9488 0%, #14B8A6 50%, #5EEAD4 100%)",   // 브라이트 아쿠아
  33: "linear-gradient(135deg, #0C1A1A 0%, #0A3330 40%, #0F766E 80%, #B8860B 100%)", // 다크틸+골드
  34: "linear-gradient(135deg, #FF4400 0%, #FF6600 50%, #FF9500 100%)",   // 제주항공 오렌지
  35: "linear-gradient(135deg, #014451 0%, #065666 50%, #0E7490 100%)",   // 딥 시안틸
  // 롯데카드 — 레드 계열 (다양한 레드)
  36: "linear-gradient(135deg, #B91C1C 0%, #DC2626 50%, #EF4444 100%)",   // 롯데 시그니처 레드
  37: "linear-gradient(135deg, #7F1D1D 0%, #991B1B 50%, #DC2626 100%)",   // 딥 롯데레드
  38: "linear-gradient(135deg, #E11D48 0%, #F43F5E 50%, #FB7185 100%)",   // 로즈레드
  39: "linear-gradient(135deg, #450A0A 0%, #7F1D1D 40%, #C2410C 80%, #EA580C 100%)", // 프리미엄 레드→오렌지
  40: "linear-gradient(135deg, #BE123C 0%, #E11D48 50%, #FDA4AF 100%)",   // 크림슨→핑크
};

function getGradient(card: Card): string {
  return cardGradients[card.id] ?? card.gradient;
}

interface CardVisualProps {
  card: Card;
  size?: "sm" | "md" | "lg";
  className?: string;
}

// ── 카드 패턴 (id 기반 8종) ──────────────────────────────
function getPattern(id: number): React.ReactNode {
  const t = id % 8;

  // 공통 속성 타입
  type DivStyle = React.CSSProperties;

  switch (t) {
    case 0: // 사선 미세 라인
      return (
        <div
          className="absolute inset-0"
          style={{
            background:
              "repeating-linear-gradient(-48deg, transparent 0px, transparent 9px, rgba(255,255,255,0.07) 9px, rgba(255,255,255,0.07) 10px)",
          } as DivStyle}
        />
      );
    case 1: // 우하단 동심원 호
      return (
        <>
          <div
            className="absolute rounded-full"
            style={{
              width: "200%",
              height: "200%",
              bottom: "-120%",
              right: "-80%",
              border: "40px solid rgba(255,255,255,0.06)",
              borderRadius: "50%",
            } as DivStyle}
          />
          <div
            className="absolute rounded-full"
            style={{
              width: "140%",
              height: "140%",
              bottom: "-90%",
              right: "-50%",
              border: "30px solid rgba(255,255,255,0.05)",
              borderRadius: "50%",
            } as DivStyle}
          />
        </>
      );
    case 2: // 대각선 광폭 밴드
      return (
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(-30deg, transparent 38%, rgba(255,255,255,0.09) 38%, rgba(255,255,255,0.09) 52%, transparent 52%)",
          } as DivStyle}
        />
      );
    case 3: // 도트 그리드
      return (
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(circle, rgba(255,255,255,0.18) 1px, transparent 1px)",
            backgroundSize: "14px 14px",
          } as DivStyle}
        />
      );
    case 4: // 좌상단 삼각 웨지
      return (
        <div
          className="absolute"
          style={{
            top: 0,
            left: 0,
            width: "65%",
            height: "65%",
            background:
              "linear-gradient(135deg, rgba(255,255,255,0.10) 0%, transparent 70%)",
            borderBottomRightRadius: "60%",
          } as DivStyle}
        />
      );
    case 5: // 가로 미세 라인
      return (
        <div
          className="absolute inset-0"
          style={{
            background:
              "repeating-linear-gradient(0deg, transparent 0px, transparent 6px, rgba(255,255,255,0.06) 6px, rgba(255,255,255,0.06) 7px)",
          } as DivStyle}
        />
      );
    case 6: // 물결 (2개 큰 호)
      return (
        <>
          <div
            className="absolute"
            style={{
              width: "180%",
              height: "180%",
              top: "-60%",
              left: "-90%",
              border: "50px solid rgba(255,255,255,0.06)",
              borderRadius: "50%",
            } as DivStyle}
          />
          <div
            className="absolute"
            style={{
              width: "120%",
              height: "120%",
              top: "-30%",
              left: "-60%",
              border: "35px solid rgba(255,255,255,0.05)",
              borderRadius: "50%",
            } as DivStyle}
          />
        </>
      );
    case 7: // 크로스해치
      return (
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              repeating-linear-gradient(45deg, rgba(255,255,255,0.05) 0px, rgba(255,255,255,0.05) 1px, transparent 1px, transparent 12px),
              repeating-linear-gradient(-45deg, rgba(255,255,255,0.05) 0px, rgba(255,255,255,0.05) 1px, transparent 1px, transparent 12px)
            `,
          } as DivStyle}
        />
      );
    default:
      return null;
  }
}

// ── 장식 요소 (id 기반 4종) ──────────────────────────────
function getDecor(id: number, size: "sm" | "md" | "lg"): React.ReactNode {
  const t = Math.floor(id / 8) % 4;
  const isLg = size === "lg";
  const isMd = size === "md";

  switch (t) {
    case 0: // 우하단 겹원 (기존)
      return (
        <>
          <div
            className="absolute rounded-full"
            style={{
              width: isLg ? 96 : isMd ? 64 : 40,
              height: isLg ? 96 : isMd ? 64 : 40,
              bottom: isLg ? -28 : isMd ? -18 : -12,
              right: isLg ? -28 : isMd ? -18 : -12,
              backgroundColor: "rgba(255,255,255,0.06)",
            }}
          />
          <div
            className="absolute rounded-full"
            style={{
              width: isLg ? 60 : isMd ? 40 : 26,
              height: isLg ? 60 : isMd ? 40 : 26,
              bottom: isLg ? -14 : isMd ? -10 : -6,
              right: isLg ? -14 : isMd ? -10 : -6,
              backgroundColor: "rgba(255,255,255,0.07)",
            }}
          />
        </>
      );
    case 1: // 우상단 + 좌하단 장식
      return (
        <>
          <div
            className="absolute rounded-full"
            style={{
              width: isLg ? 80 : isMd ? 52 : 32,
              height: isLg ? 80 : isMd ? 52 : 32,
              top: isLg ? -24 : isMd ? -16 : -10,
              right: isLg ? -24 : isMd ? -16 : -10,
              backgroundColor: "rgba(255,255,255,0.08)",
            }}
          />
          <div
            className="absolute rounded-full"
            style={{
              width: isLg ? 48 : isMd ? 32 : 20,
              height: isLg ? 48 : isMd ? 32 : 20,
              bottom: isLg ? -14 : isMd ? -10 : -6,
              left: isLg ? 60 : isMd ? 40 : 24,
              backgroundColor: "rgba(255,255,255,0.06)",
            }}
          />
        </>
      );
    case 2: // 중앙 큰 원
      return (
        <div
          className="absolute rounded-full"
          style={{
            width: isLg ? 140 : isMd ? 90 : 56,
            height: isLg ? 140 : isMd ? 90 : 56,
            top: "50%",
            right: isLg ? -40 : isMd ? -26 : -16,
            transform: "translateY(-50%)",
            border: "1px solid rgba(255,255,255,0.12)",
            backgroundColor: "rgba(255,255,255,0.04)",
          }}
        />
      );
    case 3: // 두 개의 작은 원 산재
      return (
        <>
          <div
            className="absolute rounded-full"
            style={{
              width: isLg ? 56 : isMd ? 36 : 22,
              height: isLg ? 56 : isMd ? 36 : 22,
              top: isLg ? 16 : isMd ? 10 : 6,
              right: isLg ? 40 : isMd ? 26 : 16,
              backgroundColor: "rgba(255,255,255,0.07)",
            }}
          />
          <div
            className="absolute rounded-full"
            style={{
              width: isLg ? 80 : isMd ? 52 : 32,
              height: isLg ? 80 : isMd ? 52 : 32,
              bottom: isLg ? -20 : isMd ? -14 : -8,
              right: isLg ? -20 : isMd ? -14 : -8,
              backgroundColor: "rgba(255,255,255,0.05)",
            }}
          />
        </>
      );
  }
}

// ── 컨택리스 심볼 ────────────────────────────────────────
function ContactlessIcon({ scale }: { scale: number }) {
  return (
    <svg
      width={14 * scale}
      height={14 * scale}
      viewBox="0 0 14 14"
      fill="none"
      style={{ opacity: 0.5 }}
    >
      <path
        d="M7 1.5C9.2 2.8 10.5 5 10.5 7.5C10.5 10 9.2 12.2 7 13.5"
        stroke="white"
        strokeWidth="1.2"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M7 4C8.4 5 9.2 6.2 9.2 7.5C9.2 8.8 8.4 10 7 11"
        stroke="white"
        strokeWidth="1.2"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M7 6.5C7.6 7 8 7.2 8 7.5C8 7.8 7.6 8 7 8.5"
        stroke="white"
        strokeWidth="1.2"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

export function CardVisual({ card, size = "md", className = "" }: CardVisualProps) {
  const dimensions = {
    sm: {
      width: "w-28",
      height: "h-[70px]",
      textName: "text-[9px]",
      textNum: "text-[8px]",
      chip: "w-5 h-3.5",
      radius: "rounded-xl",
      contactlessScale: 0.75,
    },
    md: {
      width: "w-48",
      height: "h-[115px]",
      textName: "text-[11px]",
      textNum: "text-[10px]",
      chip: "w-8 h-6",
      radius: "rounded-xl",
      contactlessScale: 1,
    },
    lg: {
      width: "w-72",
      height: "h-[172px]",
      textName: "text-sm",
      textNum: "text-xs",
      chip: "w-12 h-9",
      radius: "rounded-2xl",
      contactlessScale: 1.4,
    },
  };

  const d = dimensions[size];

  // 칩 위치 변형 (id 기반)
  const chipPosition = card.id % 3;
  // 0: 왼쪽 중앙, 1: 왼쪽 하단, 2: 왼쪽 상단
  const chipTop =
    chipPosition === 0
      ? "top-1/2 -translate-y-1/2"
      : chipPosition === 1
        ? "bottom-6"
        : "top-4";

  // 컨택리스 표시 여부 (type=credit인 카드만)
  const showContactless = card.type === "credit" && card.id % 2 === 0;

  return (
    <div
      className={`${d.width} ${d.height} ${d.radius} relative overflow-hidden shadow-lg flex-shrink-0 ${className}`}
      style={{ background: getGradient(card) }}
    >
      {/* ── 패턴 레이어 ── */}
      {getPattern(card.id)}

      {/* ── 상단 글로우 (빛 반사) ── */}
      <div
        className="absolute inset-0 opacity-25"
        style={{
          background:
            "radial-gradient(ellipse at 15% 15%, rgba(255,255,255,0.55) 0%, transparent 55%)",
        }}
      />

      {/* ── 장식 요소 ── */}
      {getDecor(card.id, size)}

      {/* ── 네트워크 로고 ── */}
      <div className={`absolute top-2.5 right-3 ${d.textNum} font-normal tracking-wider`}
        style={{ color: "rgba(255,255,255,0.75)" }}
      >
        {card.network}
      </div>

      {/* ── 컨택리스 심볼 ── */}
      {showContactless && size !== "sm" && (
        <div className="absolute top-2.5 right-3 mt-4">
          <ContactlessIcon scale={d.contactlessScale} />
        </div>
      )}

      {/* ── 칩 ── */}
      <div
        className={`absolute left-4 ${chipTop} ${d.chip} rounded-sm`}
        style={{
          background: "linear-gradient(135deg, #f9e784 0%, #e6c84f 40%, #cfab30 60%, #f9e784 100%)",
          boxShadow: "inset 0 0 0 0.5px rgba(0,0,0,0.12)",
        }}
      >
        {/* 칩 내부 라인 */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            background:
              "linear-gradient(180deg, transparent 30%, rgba(0,0,0,0.25) 50%, transparent 70%)",
          }}
        />
        <div
          className="absolute"
          style={{
            top: "50%",
            left: 0,
            right: 0,
            height: 1,
            backgroundColor: "rgba(0,0,0,0.2)",
            transform: "translateY(-50%)",
          }}
        />
      </div>

      {/* ── 카드 번호 ── */}
      {size !== "sm" && (
        <div
          className={`absolute bottom-8 left-4 right-4 ${d.textNum} font-normal tracking-widest`}
          style={{ color: "rgba(255,255,255,0.5)" }}
        >
          •••• •••• •••• {String(card.id).padStart(4, "0")}
        </div>
      )}

      {/* ── 카드명 ── */}
      <div className="absolute bottom-2.5 left-4 right-4">
        <div className={`${d.textName} font-normal truncate`}
          style={{ color: "rgba(255,255,255,0.90)" }}
        >
          {card.name}
        </div>
      </div>
    </div>
  );
}