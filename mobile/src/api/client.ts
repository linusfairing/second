import axios from "axios";
import * as SecureStore from "expo-secure-store";
import { router } from "expo-router";
import { API_BASE_URL } from "../config";

let onForceSignOut: (() => void) | null = null;

export function setForceSignOut(fn: () => void) {
  onForceSignOut = fn;
}

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const url = error.config?.url || "";
    const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/signup");
    if (error.response?.status === 401 && !isAuthEndpoint) {
      await SecureStore.deleteItemAsync("token");
      await SecureStore.deleteItemAsync("userId");
      if (onForceSignOut) onForceSignOut();
      router.replace("/auth/login");
    }
    return Promise.reject(error);
  }
);

export default client;
