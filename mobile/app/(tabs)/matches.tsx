import { useCallback, useState } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Image,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { getMatches } from "../../src/api/matches";
import { MatchResponse } from "../../src/types/api";
import { photoUrl } from "../../src/config";

export default function MatchesScreen() {
  const router = useRouter();
  const [matches, setMatches] = useState<MatchResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);

  useFocusEffect(
    useCallback(() => {
      loadMatches();
    }, [])
  );

  async function loadMatches(isRefresh = false) {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(false);
    try {
      const res = await getMatches();
      setMatches(res.matches);
    } catch (err) {
      console.error("Failed to load matches:", err);
      setError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  function renderMatch({ item }: { item: MatchResponse }) {
    const user = item.other_user;
    const photo = user.photos.find((p) => p.is_primary) ?? user.photos[0];

    return (
      <TouchableOpacity
        style={styles.matchRow}
        onPress={() => router.push(`/messages/${item.id}`)}
      >
        {photo ? (
          <Image
            source={{ uri: photoUrl(photo.file_path) }}
            style={styles.avatar}
          />
        ) : (
          <View style={[styles.avatar, styles.noAvatar]}>
            <Text style={styles.avatarText}>
              {(user.display_name || "?")[0].toUpperCase()}
            </Text>
          </View>
        )}
        <View style={styles.matchInfo}>
          <Text style={styles.matchName}>
            {user.display_name || "Anonymous"}
          </Text>
          {user.profile?.bio && (
            <Text style={styles.matchBio} numberOfLines={1}>
              {user.profile.bio}
            </Text>
          )}
        </View>
      </TouchableOpacity>
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#e91e63" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <Text style={styles.title}>Matches</Text>
      {error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>Something went wrong</Text>
          <TouchableOpacity style={styles.retryButton} onPress={loadMatches}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : matches.length === 0 ? (
        <View style={styles.center}>
          <Text style={styles.emptyText}>No matches yet. Keep swiping!</Text>
        </View>
      ) : (
        <FlatList
          data={matches}
          keyExtractor={(item) => item.id}
          renderItem={renderMatch}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => loadMatches(true)} tintColor="#e91e63" />
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  list: { paddingHorizontal: 16 },
  matchRow: {
    flexDirection: "row",
    alignItems: "center",
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#f0f0f0",
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#eee",
  },
  noAvatar: { justifyContent: "center", alignItems: "center" },
  avatarText: { fontSize: 20, fontWeight: "bold", color: "#aaa" },
  matchInfo: { flex: 1, marginLeft: 12 },
  matchName: { fontSize: 16, fontWeight: "600" },
  matchBio: { fontSize: 13, color: "#888", marginTop: 2 },
  errorText: { fontSize: 15, color: "#e91e63", marginBottom: 16 },
  retryButton: {
    backgroundColor: "#e91e63",
    borderRadius: 20,
    paddingHorizontal: 24,
    paddingVertical: 10,
  },
  retryText: { color: "#fff", fontWeight: "600" },
  emptyText: { fontSize: 15, color: "#888" },
});
