import { useCallback, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Image,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { ScrollView } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useFocusEffect } from "expo-router";
import { getMyProfile, uploadPhoto, deletePhoto } from "../../src/api/profile";
import { useAuth } from "../../src/context/AuthContext";
import { UserResponse } from "../../src/types/api";
import { photoUrl } from "../../src/config";

export default function ProfileScreen() {
  const { signOut } = useAuth();
  const [profile, setProfile] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  useFocusEffect(
    useCallback(() => {
      loadProfile();
    }, [])
  );

  async function loadProfile() {
    setLoading(true);
    try {
      const data = await getMyProfile();
      setProfile(data);
    } catch (err) {
      console.error("Failed to load profile:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleAddPhoto() {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      Alert.alert(
        "Permission needed",
        "Please allow access to your photo library to upload photos."
      );
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      setUploading(true);
      try {
        await uploadPhoto(result.assets[0].uri);
        await loadProfile();
      } catch (err) {
        console.error("Failed to upload photo:", err);
        Alert.alert("Error", "Failed to upload photo.");
      } finally {
        setUploading(false);
      }
    }
  }

  async function handleDeletePhoto(photoId: string) {
    Alert.alert("Delete Photo", "Are you sure you want to delete this photo?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await deletePhoto(photoId);
            await loadProfile();
          } catch (err) {
            console.error("Failed to delete photo:", err);
            Alert.alert("Error", "Failed to delete photo.");
          }
        },
      },
    ]);
  }

  async function handleSignOut() {
    await signOut();
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#e91e63" />
      </View>
    );
  }

  if (!profile) {
    return (
      <View style={styles.center}>
        <Text>Failed to load profile.</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Profile</Text>

        <View style={styles.section}>
          <Text style={styles.label}>Email</Text>
          <Text style={styles.value}>{profile.email}</Text>
        </View>

        {profile.display_name && (
          <View style={styles.section}>
            <Text style={styles.label}>Name</Text>
            <Text style={styles.value}>{profile.display_name}</Text>
          </View>
        )}

        {profile.gender && (
          <View style={styles.section}>
            <Text style={styles.label}>Gender</Text>
            <Text style={styles.value}>{profile.gender}</Text>
          </View>
        )}

        {profile.location && (
          <View style={styles.section}>
            <Text style={styles.label}>Location</Text>
            <Text style={styles.value}>{profile.location}</Text>
          </View>
        )}

        {profile.profile?.bio && (
          <View style={styles.section}>
            <Text style={styles.label}>Bio</Text>
            <Text style={styles.value}>{profile.profile.bio}</Text>
          </View>
        )}

        {profile.profile?.interests && profile.profile.interests.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.label}>Interests</Text>
            <Text style={styles.value}>
              {profile.profile.interests.join(", ")}
            </Text>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.label}>Photos</Text>
          <View style={styles.photoGrid}>
            {profile.photos.map((photo) => (
              <View key={photo.id} style={styles.photoItem}>
                <Image
                  source={{ uri: photoUrl(photo.file_path) }}
                  style={styles.photo}
                />
                <TouchableOpacity
                  style={styles.deletePhoto}
                  onPress={() => handleDeletePhoto(photo.id)}
                >
                  <Text style={styles.deletePhotoText}>X</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
          <TouchableOpacity
            style={[styles.addPhotoButton, uploading && styles.addPhotoDisabled]}
            onPress={handleAddPhoto}
            disabled={uploading}
          >
            {uploading ? (
              <ActivityIndicator size="small" color="#e91e63" />
            ) : (
              <Text style={styles.addPhotoText}>Add Photo</Text>
            )}
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut}>
          <Text style={styles.signOutText}>Sign Out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  content: { paddingHorizontal: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  title: { fontSize: 24, fontWeight: "bold", marginBottom: 24 },
  section: { marginBottom: 20 },
  label: { fontSize: 13, color: "#888", marginBottom: 4, textTransform: "uppercase" },
  value: { fontSize: 16, color: "#333" },
  photoGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8 },
  photoItem: { position: "relative" },
  photo: { width: 100, height: 100, borderRadius: 8 },
  deletePhoto: {
    position: "absolute",
    top: 4,
    right: 4,
    backgroundColor: "rgba(0,0,0,0.6)",
    borderRadius: 12,
    width: 24,
    height: 24,
    justifyContent: "center",
    alignItems: "center",
  },
  deletePhotoText: { color: "#fff", fontSize: 12, fontWeight: "bold" },
  addPhotoButton: {
    borderWidth: 1,
    borderColor: "#e91e63",
    borderRadius: 8,
    padding: 10,
    alignItems: "center",
  },
  addPhotoText: { color: "#e91e63", fontWeight: "600" },
  addPhotoDisabled: { opacity: 0.5 },
  signOutButton: {
    backgroundColor: "#f0f0f0",
    borderRadius: 8,
    padding: 16,
    alignItems: "center",
    marginTop: 20,
  },
  signOutText: { color: "#e91e63", fontSize: 16, fontWeight: "600" },
});
