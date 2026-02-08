import client from "./client";
import {
  LikeResponse,
  PassResponse,
  MatchListResponse,
  MessageResponse,
  SendMessageRequest,
} from "../types/api";

export async function likeUser(likedUserId: string) {
  const res = await client.post<LikeResponse>("/api/v1/matches/like", {
    liked_user_id: likedUserId,
  });
  return res.data;
}

export async function passUser(passedUserId: string) {
  const res = await client.post<PassResponse>("/api/v1/matches/pass", {
    passed_user_id: passedUserId,
  });
  return res.data;
}

export async function getMatches(limit = 20, offset = 0) {
  const res = await client.get<MatchListResponse>("/api/v1/matches", {
    params: { limit, offset },
  });
  return res.data;
}

export async function getMessages(matchId: string) {
  const res = await client.get<MessageResponse[]>(
    `/api/v1/matches/${matchId}/messages`
  );
  return res.data;
}

export async function sendMessage(matchId: string, content: string) {
  const res = await client.post<MessageResponse>(
    `/api/v1/matches/${matchId}/messages`,
    { content } as SendMessageRequest
  );
  return res.data;
}
