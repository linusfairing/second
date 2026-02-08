import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Image,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { getDiscoverUsers } from "../../src/api/discover";
import { likeUser, passUser } from "../../src/api/matches";
import { DiscoverUserResponse } from "../../src/types/api";
import { photoUrl } from "../../src/config";

export default function DiscoverScreen() {
  const [users, setUsers] = useState<DiscoverUserResponse[]>([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [matchAlert, setMatchAlert] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getDiscoverUsers();
      setUsers(res.users);
      setIndex(0);
    } catch (err) {
      console.error("Failed to load discover users:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const currentUser = users[index] ?? null;

  async function handleLike() {
    if (!currentUser || acting) return;
    setActing(true);
    try {
      const res = await likeUser(currentUser.id);
      if (res.is_match) {
        setMatchAlert(currentUser.display_name || "Someone");
        setTimeout(() => setMatchAlert(null), 2500);
      }
      advance();
    } catch (err) {
      console.error("Failed to like user:", err);
    } finally {
      setActing(false);
    }
  }

  async function handlePass() {
    if (!currentUser || acting) return;
    setActing(true);
    try {
      await passUser(currentUser.id);
      advance();
    } catch (err) {
      console.error("Failed to pass user:", err);
    } finally {
      setActing(false);
    }
  }

  function advance() {
    if (index + 1 < users.length) {
      setIndex((i) => i + 1);
    } else {
      loadUsers();
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#e91e63" />
      </View>
    );
  }

  if (!currentUser) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyText}>No more people to discover</Text>
        <TouchableOpacity style={styles.refreshButton} onPress={loadUsers}>
          <Text style={styles.refreshText}>Refresh</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const primaryPhoto = currentUser.photos.find((p) => p.is_primary) ?? currentUser.photos[0];
  const score = Math.round(currentUser.compatibility_score * 100);

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      {matchAlert && (
        <View style={styles.matchBanner}>
          <Text style={styles.matchText}>It's a match with {matchAlert}!</Text>
        </View>
      )}

      <View style={styles.card}>
        {primaryPhoto ? (
          <Image
            source={{ uri: photoUrl(primaryPhoto.file_path) }}
            style={styles.photo}
          />
        ) : (
          <View style={[styles.photo, styles.noPhoto]}>
            <Text style={styles.noPhotoText}>No Photo</Text>
          </View>
        )}
        <View style={styles.cardInfo}>
          <Text style={styles.name}>
            {currentUser.display_name || "Anonymous"}
          </Text>
          {currentUser.location && (
            <Text style={styles.detail}>{currentUser.location}</Text>
          )}
          {currentUser.profile?.bio && (
            <Text style={styles.bio} numberOfLines={3}>
              {currentUser.profile.bio}
            </Text>
          )}
          {score > 0 && (
            <Text style={styles.score}>{score}% compatible</Text>
          )}
        </View>
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionButton, styles.passButton]}
          onPress={handlePass}
          disabled={acting}
        >
          <Text style={styles.passButtonText}>Pass</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, styles.likeButton]}
          onPress={handleLike}
          disabled={acting}
        >
          <Text style={styles.likeButtonText}>Like</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  card: {
    flex: 1,
    marginHorizontal: 16,
    borderRadius: 16,
    overflow: "hidden",
    backgroundColor: "#f9f9f9",
    elevation: 3,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  photo: { width: "100%", height: "60%", backgroundColor: "#eee" },
  noPhoto: { justifyContent: "center", alignItems: "center" },
  noPhotoText: { color: "#aaa", fontSize: 18 },
  cardInfo: { padding: 20 },
  name: { fontSize: 24, fontWeight: "bold" },
  detail: { fontSize: 14, color: "#888", marginTop: 4 },
  bio: { fontSize: 15, color: "#555", marginTop: 8 },
  score: { fontSize: 14, color: "#e91e63", fontWeight: "600", marginTop: 8 },
  actions: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 24,
    paddingVertical: 20,
    paddingBottom: 32,
  },
  actionButton: {
    width: 100,
    paddingVertical: 14,
    borderRadius: 30,
    alignItems: "center",
  },
  passButton: { backgroundColor: "#f0f0f0" },
  likeButton: { backgroundColor: "#e91e63" },
  passButtonText: { fontSize: 16, fontWeight: "600", color: "#888" },
  likeButtonText: { fontSize: 16, fontWeight: "600", color: "#fff" },
  emptyText: { fontSize: 16, color: "#888", marginBottom: 16 },
  refreshButton: {
    backgroundColor: "#e91e63",
    borderRadius: 20,
    paddingHorizontal: 24,
    paddingVertical: 10,
  },
  refreshText: { color: "#fff", fontWeight: "600" },
  matchBanner: {
    position: "absolute",
    top: 16,
    left: 16,
    right: 16,
    backgroundColor: "#e91e63",
    borderRadius: 12,
    padding: 16,
    zIndex: 10,
    alignItems: "center",
  },
  matchText: { color: "#fff", fontSize: 18, fontWeight: "bold" },
});
