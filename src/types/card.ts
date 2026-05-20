export interface CardListItem {
  cardId: string;
  company: string;
  cardName: string;
  cardType: string;
  annualFee: number;
  minPerformance: number;
  totalMaxBenefit: number | null;
  summary: string;
  hasEvent: boolean;
  categoryBenefits: string[] | null;
}

export interface BenefitDetail {
  categoryName: string;
  benefitTitle: string;
  benefitContent: string;
  benefitValueText: string;
  maxLimit: number | null;
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
  benefits: BenefitDetail[];
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