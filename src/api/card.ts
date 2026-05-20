import { api } from "./axios";
import {
  CardListItem,
  CardDetailItem,
  CardScore,
  PersonaType,
} from "../types/card";

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

export const getCardScores = async (
  cardId: string,
  personaType: PersonaType = "STUDENT"
): Promise<CardScore> => {
  const response = await api.get(`/api/cards/${cardId}/scores`, {
    params: { personaType },
  });

  return response.data;
};