import client from "./client";
import { BlockResponse, BlockedUserListResponse } from "../types/api";

export async function blockUser(blockedUserId: string) {
  const res = await client.post<BlockResponse>("/api/v1/block", {
    blocked_user_id: blockedUserId,
  });
  return res.data;
}

export async function unblockUser(blockedUserId: string) {
  await client.delete(`/api/v1/block/${blockedUserId}`);
}

export async function getBlockedUsers() {
  const res = await client.get<BlockedUserListResponse>("/api/v1/block");
  return res.data;
}
