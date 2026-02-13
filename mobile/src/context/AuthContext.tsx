import React, { createContext, useContext, useEffect, useState } from "react";
import * as SecureStore from "expo-secure-store";
import { getChatStatus } from "../api/chat";
import { setForceSignOut, setCachedToken } from "../api/client";

interface AuthState {
  token: string | null;
  userId: string | null;
  isLoading: boolean;
  profileSetupComplete: boolean;
  onboardingComplete: boolean;
  signIn: (token: string, userId: string) => Promise<void>;
  signOut: () => Promise<void>;
  checkOnboarding: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  token: null,
  userId: null,
  isLoading: true,
  profileSetupComplete: false,
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
  const [profileSetupComplete, setProfileSetupComplete] = useState(false);
  const [onboardingComplete, setOnboardingComplete] = useState(false);

  useEffect(() => {
    setForceSignOut(() => {
      setToken(null);
      setUserId(null);
      setProfileSetupComplete(false);
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
    }
  }

  async function fetchOnboardingStatus() {
    try {
      const status = await getChatStatus();
      const setupDone = !!status.profile_setup_complete;
      const completed = status.onboarding_status === "completed";
      setProfileSetupComplete(setupDone);
      setOnboardingComplete(completed);
      await SecureStore.setItemAsync("profileSetupComplete", setupDone ? "1" : "0");
      await SecureStore.setItemAsync("onboardingComplete", completed ? "1" : "0");
    } catch {
      // Network failed — fall back to cached values
      const cachedSetup = await SecureStore.getItemAsync("profileSetupComplete");
      const cachedOnboarding = await SecureStore.getItemAsync("onboardingComplete");
      setProfileSetupComplete(cachedSetup === "1");
      setOnboardingComplete(cachedOnboarding === "1");
    }
  }

  async function signIn(newToken: string, newUserId: string) {
    await SecureStore.setItemAsync("token", newToken);
    await SecureStore.setItemAsync("userId", newUserId);
    setCachedToken(newToken);
    setToken(newToken);
    setUserId(newUserId);
    await fetchOnboardingStatus();
  }

  async function signOut() {
    setCachedToken(null);
    await SecureStore.deleteItemAsync("token");
    await SecureStore.deleteItemAsync("userId");
    await SecureStore.deleteItemAsync("profileSetupComplete");
    await SecureStore.deleteItemAsync("onboardingComplete");
    setToken(null);
    setUserId(null);
    setProfileSetupComplete(false);
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
        profileSetupComplete,
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
