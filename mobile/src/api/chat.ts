import client from "./client";
import {
  ChatResponse,
  ChatMessageResponse,
  ChatStatusResponse,
} from "../types/api";

export async function sendChatMessage(message: string) {
  const res = await client.post<ChatResponse>("/api/v1/chat", { message });
  return res.data;
}

export async function getChatHistory() {
  const res = await client.get<ChatMessageResponse[]>("/api/v1/chat/history");
  return res.data;
}

export async function getChatStatus() {
  const res = await client.get<ChatStatusResponse>("/api/v1/chat/status");
  return res.data;
}

export async function getChatIntro() {
  const res = await client.get<{ messages: string[] }>("/api/v1/chat/intro");
  return res.data.messages;
}
