import Constants from "expo-constants";

const lanIp = Constants.expoConfig?.extra?.lanIp || "localhost";

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL || `http://${lanIp}:8000`;

export function photoUrl(filePath: string): string {
  return `${API_BASE_URL}/uploads/${filePath}`;
}
