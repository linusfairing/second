import { useEffect } from "react";
import { ActivityIndicator, View } from "react-native";
import { Slot, useRouter, useSegments } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AuthProvider, useAuth } from "../src/context/AuthContext";

// Hide splash screen immediately — we use our own loading spinner instead
SplashScreen.hideAsync().catch(() => {});

function AuthGuard() {
  const { token, isLoading, profileSetupComplete, onboardingComplete } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    const inAuth = segments[0] === "auth";
    const inOnboarding = segments[0] === "onboarding";

    const secondSegment = (segments as string[])[1];

    if (!token) {
      if (!inAuth) router.replace("/auth/login");
    } else if (!profileSetupComplete) {
      if (!inOnboarding || secondSegment !== "profile-setup")
        router.replace("/onboarding/profile-setup");
    } else if (!onboardingComplete) {
      if (!inOnboarding || secondSegment === "profile-setup")
        router.replace("/onboarding");
    } else {
      if (inAuth || inOnboarding) router.replace("/(tabs)/discover");
    }
  }, [token, isLoading, profileSetupComplete, onboardingComplete, segments]);

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return <Slot />;
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <AuthGuard />
      </AuthProvider>
    </SafeAreaProvider>
  );
}
