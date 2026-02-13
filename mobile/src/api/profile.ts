import client from "./client";
import { UserResponse, UserUpdate, ProfileUpdate, ProfileDataResponse, PhotoResponse, ProfileSetupRequest } from "../types/api";

export async function getMyProfile() {
  const res = await client.get<UserResponse>("/api/v1/profile/me");
  return res.data;
}

export async function updateMyProfile(data: UserUpdate) {
  const res = await client.put<UserResponse>("/api/v1/profile/me", data);
  return res.data;
}

export async function updateMyProfileDetails(data: ProfileUpdate) {
  const res = await client.put<ProfileDataResponse>("/api/v1/profile/me/profile", data);
  return res.data;
}

export async function uploadPhoto(uri: string) {
  const formData = new FormData();
  const filename = uri.split("/").pop() || "photo.jpg";
  const match = /\.(\w+)$/.exec(filename);
  const ext = match ? match[1].toLowerCase() : "jpeg";
  const type = `image/${ext === "jpg" ? "jpeg" : ext}`;
  formData.append("file", { uri, name: filename, type } as any);

  const res = await client.post<PhotoResponse>("/api/v1/profile/me/photos", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function deletePhoto(photoId: string) {
  await client.delete(`/api/v1/profile/me/photos/${photoId}`);
}

export async function submitProfileSetup(data: ProfileSetupRequest) {
  const res = await client.post<UserResponse>("/api/v1/profile/me/setup", data);
  return res.data;
}
