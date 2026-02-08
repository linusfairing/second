import client from "./client";
import { DiscoverResponse } from "../types/api";

export async function getDiscoverUsers(limit = 10, offset = 0) {
  const res = await client.get<DiscoverResponse>("/api/v1/discover", {
    params: { limit, offset },
  });
  return res.data;
}
