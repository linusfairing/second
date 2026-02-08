import React, { createContext, useContext, useEffect, useState } from "react";
import * as SecureStore from "expo-secure-store";
import * as SplashScreen from "expo-splash-screen";
import { getChatStatus } from "../api/chat";
import { setForceSignOut } from "../api/client";

interface AuthState {
  token: string | null;
  userId: string | null;
  isLoading: boolean;
  onboardingComplete: boolean;
  signIn: (token: string, userId: string) => Promise<void>;
  signOut: () => Promise<void>;
  checkOnboarding: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  token: null,
  userId: null,
  isLoading: true,
  onboardingComplete: false,
  signIn: async () => {},
  signOut: async () => {},
  checkOnboarding: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [onboardingComplete, setOnboardingComplete] = useState(false);

  useEffect(() => {
    setForceSignOut(() => {
      setToken(null);
      setUserId(null);
      setOnboardingComplete(false);
    });
    restoreSession();
  }, []);

  async function restoreSession() {
    try {
      const storedToken = await SecureStore.getItemAsync("token");
      const storedUserId = await SecureStore.getItemAsync("userId");
      if (storedToken && storedUserId) {
        setToken(storedToken);
        setUserId(storedUserId);
        await fetchOnboardingStatus();
      }
    } catch {
      // Token invalid or expired — stay logged out
    } finally {
      setIsLoading(false);
      await SplashScreen.hideAsync();
    }
  }

  async function fetchOnboardingStatus() {
    try {
      const status = await getChatStatus();
      const completed = status.onboarding_status === "completed";
      setOnboardingComplete(completed);
      await SecureStore.setItemAsync("onboardingComplete", completed ? "1" : "0");
    } catch {
      // Network failed — fall back to cached value
      const cached = await SecureStore.getItemAsync("onboardingComplete");
      setOnboardingComplete(cached === "1");
    }
  }

  async function signIn(newToken: string, newUserId: string) {
    await SecureStore.setItemAsync("token", newToken);
    await SecureStore.setItemAsync("userId", newUserId);
    setToken(newToken);
    setUserId(newUserId);
    await fetchOnboardingStatus();
  }

  async function signOut() {
    await SecureStore.deleteItemAsync("token");
    await SecureStore.deleteItemAsync("userId");
    await SecureStore.deleteItemAsync("onboardingComplete");
    setToken(null);
    setUserId(null);
    setOnboardingComplete(false);
  }

  async function checkOnboarding() {
    await fetchOnboardingStatus();
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        userId,
        isLoading,
        onboardingComplete,
        signIn,
        signOut,
        checkOnboarding,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
