import { api } from "./axios";
import { CardListItem, CardDetailItem } from "../types/card";

export const getCards = async (): Promise<CardListItem[]> => {
  const response = await api.get("/api/cards");
  return response.data;
};

export const getCardDetail = async (
  cardId: string
): Promise<CardDetailItem> => {
  const response = await api.get(`/api/cards/${cardId}`);
  return response.data;
};