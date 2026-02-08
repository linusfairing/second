import client from "./client";
import { AccountStatusResponse } from "../types/api";

export async function deactivateAccount() {
  const res = await client.post<AccountStatusResponse>("/api/v1/account/deactivate");
  return res.data;
}

export async function reactivateAccount() {
  const res = await client.post<AccountStatusResponse>("/api/v1/account/reactivate");
  return res.data;
}

export async function getAccountStatus() {
  const res = await client.get<AccountStatusResponse>("/api/v1/account/status");
  return res.data;
}
