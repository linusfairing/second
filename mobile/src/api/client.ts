import axios from "axios";
import * as SecureStore from "expo-secure-store";
import { router } from "expo-router";
import { API_BASE_URL } from "../config";

let onForceSignOut: (() => void) | null = null;
let cachedToken: string | null = null;
let isSigningOut = false;

export function setForceSignOut(fn: () => void) {
  onForceSignOut = fn;
}

export function setCachedToken(token: string | null) {
  cachedToken = token;
}

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use(async (config) => {
  // Use in-memory cached token to avoid async SecureStore reads on every request
  if (!cachedToken) {
    cachedToken = await SecureStore.getItemAsync("token");
  }
  if (cachedToken) {
    config.headers.Authorization = `Bearer ${cachedToken}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const url = error.config?.url || "";
    const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/signup");
    if (error.response?.status === 401 && !isAuthEndpoint && !isSigningOut) {
      // Guard against concurrent 401s triggering multiple sign-outs
      isSigningOut = true;
      try {
        cachedToken = null;
        await SecureStore.deleteItemAsync("token");
        await SecureStore.deleteItemAsync("userId");
        await SecureStore.deleteItemAsync("profileSetupComplete");
        await SecureStore.deleteItemAsync("onboardingComplete");
        if (onForceSignOut) onForceSignOut();
        router.replace("/auth/login");
      } finally {
        isSigningOut = false;
      }
    }
    return Promise.reject(error);
  }
);

/** Extract a human-readable error message from an API error response. */
export function getErrorMessage(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  // Pydantic validation errors: array of { msg, loc }
  if (Array.isArray(detail)) {
    return detail
      .map((e: any) => {
        const field = e.loc?.slice(-1)[0];
        const msg: string = e.msg || "Invalid value";
        return field ? `${field}: ${msg}` : msg;
      })
      .join("\n");
  }
  return fallback;
}

export default client;
