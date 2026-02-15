import React, { createContext, useContext, useEffect, useState } from "react";
import * as SecureStore from "expo-secure-store";
import { getChatStatus } from "../api/chat";
import { setForceSignOut, setCachedToken } from "../api/client";

interface AuthState {
  token: string | null;
  userId: string | null;
  isLoading: boolean;
  profileSetupComplete: boolean;
  datingPreferencesComplete: boolean;
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
  datingPreferencesComplete: false,
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
  const [datingPreferencesComplete, setDatingPreferencesComplete] = useState(false);
  const [onboardingComplete, setOnboardingComplete] = useState(false);

  useEffect(() => {
    setForceSignOut(() => {
      setToken(null);
      setUserId(null);
      setProfileSetupComplete(false);
      setDatingPreferencesComplete(false);
      setOnboardingComplete(false);
    });
    restoreSession();
  }, []);

  async function restoreSession() {
    try {
      const storedToken = await SecureStore.getItemAsync("token");
      const storedUserId = await SecureStore.getItemAsync("userId");
      if (storedToken && storedUserId) {
        setCachedToken(storedToken);
        setToken(storedToken);
        setUserId(storedUserId);
        await fetchOnboardingStatus();
      }
    } catch {
      // Token invalid or expired — clear stale session
      setCachedToken(null);
      setToken(null);
      setUserId(null);
      await SecureStore.deleteItemAsync("token");
      await SecureStore.deleteItemAsync("userId");
      await SecureStore.deleteItemAsync("profileSetupComplete");
      await SecureStore.deleteItemAsync("datingPreferencesComplete");
      await SecureStore.deleteItemAsync("onboardingComplete");
    } finally {
      setIsLoading(false);
    }
  }

  async function fetchOnboardingStatus() {
    try {
      const status = await getChatStatus();
      const setupDone = !!status.profile_setup_complete;
      const datingDone = !!status.dating_preferences_complete;
      const completed = status.onboarding_status === "completed";
      setProfileSetupComplete(setupDone);
      setDatingPreferencesComplete(datingDone);
      setOnboardingComplete(completed);
      await SecureStore.setItemAsync("profileSetupComplete", setupDone ? "1" : "0");
      await SecureStore.setItemAsync("datingPreferencesComplete", datingDone ? "1" : "0");
      await SecureStore.setItemAsync("onboardingComplete", completed ? "1" : "0");
    } catch (err: any) {
      // Auth error — re-throw so restoreSession can clear stale tokens
      if (err?.response?.status === 401) throw err;
      // Network failed — fall back to cached values
      const cachedSetup = await SecureStore.getItemAsync("profileSetupComplete");
      const cachedDating = await SecureStore.getItemAsync("datingPreferencesComplete");
      const cachedOnboarding = await SecureStore.getItemAsync("onboardingComplete");
      setProfileSetupComplete(cachedSetup === "1");
      setDatingPreferencesComplete(cachedDating === "1");
      setOnboardingComplete(cachedOnboarding === "1");
    }
  }

  async function signIn(newToken: string, newUserId: string) {
    await SecureStore.setItemAsync("token", newToken);
    await SecureStore.setItemAsync("userId", newUserId);
    setCachedToken(newToken);
    // Fetch onboarding status BEFORE setting token in React state,
    // so the auth guard has correct values when it first fires
    await fetchOnboardingStatus();
    setToken(newToken);
    setUserId(newUserId);
  }

  async function signOut() {
    setCachedToken(null);
    await SecureStore.deleteItemAsync("token");
    await SecureStore.deleteItemAsync("userId");
    await SecureStore.deleteItemAsync("profileSetupComplete");
    await SecureStore.deleteItemAsync("datingPreferencesComplete");
    await SecureStore.deleteItemAsync("onboardingComplete");
    setToken(null);
    setUserId(null);
    setProfileSetupComplete(false);
    setDatingPreferencesComplete(false);
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
        datingPreferencesComplete,
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
