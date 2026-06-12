// API/CARDS.TS
import { api } from "./axios";
import {
  CardListItem,
  CardDetailItem,
  CardScore,
  PersonaType,
  CardCompareResponse,
  CompareSearchCardItem,
} from "../types/card";

const unwrapResponseData = <T>(raw: any): T => {
  return raw?.data ?? raw?.card ?? raw?.result ?? raw;
};

const normalizeImageUrl = (data: any): string | null => {
  return (
    data?.imageUrl ??
    data?.imgUrl ??
    data?.image_url ??
    data?.cardImageUrl ??
    data?.cardImgUrl ??
    null
  );
};

export const getCards = async (): Promise<CardListItem[]> => {
  const response = await api.get("/api/cards");
  const data = unwrapResponseData<CardListItem[]>(response.data);

  return Array.isArray(data)
    ? data.map((card) => ({
        ...card,
        imageUrl: normalizeImageUrl(card),
      }))
    : [];
};

export const getCardDetail = async (cardId: string) => {
  const token = localStorage.getItem("token");

  const response = await api.get(
    `/api/cards/${cardId}`,
    {
      headers: token
        ? {
            Authorization: token,
          }
        : {},
    }
  );

  return response.data;
};

export const getCardScores = async (
  cardId: string,
  personaType: PersonaType = "STUDENT",
): Promise<CardScore> => {
  const response = await api.get(`/api/cards/${encodeURIComponent(cardId)}/scores`, {
    params: { personaType },
  });

  return unwrapResponseData<CardScore>(response.data);
};

export const compareCards = async (
  cardIds: string[],
  personaType: PersonaType = "STUDENT",
): Promise<CardCompareResponse> => {
  const token = localStorage.getItem("token");

  const response = await api.get<CardCompareResponse>(
    "/api/cards/compare",
    {
      params: {
        ids: cardIds.join(","),
        personaType,
      },
      headers: token
        ? {
            Authorization: token,
          }
        : undefined,
    }
  );

  const data = unwrapResponseData<CardCompareResponse>(response.data);

  if (Array.isArray(data)) {
    return data.map((card) => ({
      ...card,
      imageUrl: normalizeImageUrl(card),
    })) as unknown as CardCompareResponse;
  }

  return data;
};

export const searchCompareCards = async (
  keyword = "",
): Promise<CompareSearchCardItem[]> => {
  const response = await api.get<CompareSearchCardItem[]>("/api/cards/search", {
    params: keyword.trim() ? { keyword } : {},
  });

  const data = unwrapResponseData<CompareSearchCardItem[]>(response.data);

  return Array.isArray(data)
    ? data.map((card) => ({
        ...card,
        imageUrl: normalizeImageUrl(card),
      }))
    : [];
};

export const filterCards = async (filters: any) => {
  const response = await api.post("/api/cards/filter", filters);

  const data = unwrapResponseData<CardListItem[]>(response.data);

  return Array.isArray(data)
    ? data.map((card) => ({
        ...card,
        imageUrl: normalizeImageUrl(card),
      }))
    : [];
};

export const getRecentCards = async () => {
  const response = await api.get("/api/users/recent-cards");

  console.log("recent cards", response.data);

  return response.data;
};