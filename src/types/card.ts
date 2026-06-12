// TYPES/CARD.TS
export interface CardListItem {
  cardId: string;
  company: string;
  cardName: string;
  cardType: string;

  annualFeeDomBasic: number;
  annualFeeDomPremium: number;
  annualFeeForBasic: number;
  annualFeeForPremium: number;

  minPerformance: number;
  totalMaxBenefit: number | null;
  summary: string;
  hasEvent: boolean;
  categoryBenefits: string[] | null;
  imageUrl?: string | null;
  hasTransport: boolean;
}

export interface BenefitDetail {
  categoryName: string;
  targetMerchants?: string | null;

  rowType?: string | null;

  uiTitle: string | null;
  uiContent: string | null;

  effectiveRateText?: string | null;

  benefitValue?: number | null;
  benefitUnit?: string | null;

  maxLimit?: number | null;
  maxLimitUnit?: string | null;
  groupMaxLimit?: number | null;
  groupMaxLimitUnit?: string | null;
}

export interface CardDetailItem {
  cardId: string;
  cardName: string;
  company: string;
  cardType: string;

  network: string;

  annualFeeDomBasic: number;
  annualFeeForBasic: number;

  minPerformance: number;
  totalMaxBenefit: number | null;

  imageUrl?: string | null;
  linkUrl?: string | null;

  hasTransport: boolean;

  feeContent?: string | null;

  benefits: BenefitDetail[];

  notices: NoticeItem[];

  events: EventItem[];
}

export interface CardScore {
  practicality: number;
  annualFee: number;
  performance: number;
  diversity: number;
  limit: number;
}

export type PersonaType =
  | "STUDENT"
  | "SINGLE"
  | "WORKER"
  | "FAMILY"
  | "SENIOR";

export interface CompareCardScore {
  practicality: number;
  annualFee: number;
  performance: number;
  diversity: number;
  limit: number;
}

export interface CompareBenefit {
  categoryName: string;
  benefitType?: string | null;
  benefitValueText: string;
  benefitTitle: string;
  benefitContent: string;
}

export interface CompareCardItem {
  cardId: string;
  company: string;
  cardName: string;
  cardType: string;
  network: string | null;
  minPerformance: number;
  imageUrl: string | null;
  scores: CompareCardScore;
  benefits: CompareBenefit[];
}

export type CardCompareResponse = CompareCardItem[];

export interface CompareSearchCardItem {
  cardId: string;
  imageUrl: string | null;
  cardType: string;
  company: string;
  cardName: string;
  annualFee: number | null;
}

export interface NoticeItem {
  cardId: string;
  noticeContent: string;
}

export interface EventItem {
  eventTitle: string;
  section: string;
  eventContent: string;
  eventLink?: string | null;

  startDate?: string | null;
  endDate?: string | null;
}