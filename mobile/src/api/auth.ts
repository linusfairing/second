import client from "./client";
import { TokenResponse } from "../types/api";

export async function login(email: string, password: string) {
  const res = await client.post<TokenResponse>("/api/v1/auth/login", {
    email: email.toLowerCase(),
    password,
  });
  return res.data;
}

export async function signup(email: string, password: string) {
  const res = await client.post<TokenResponse>("/api/v1/auth/signup", {
    email: email.toLowerCase(),
    password,
  });
  return res.data;
}
