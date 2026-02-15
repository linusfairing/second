import { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  Switch,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import MultiSlider from "@ptomasroos/react-native-multi-slider";
import { useRouter } from "expo-router";
import { useAuth } from "../../src/context/AuthContext";
import { getMyProfile, updateMyProfile } from "../../src/api/profile";
import { getErrorMessage } from "../../src/api/client";

const GENDER_CHIPS: { label: string; value: string }[] = [
  { label: "Men", value: "Man" },
  { label: "Women", value: "Woman" },
  { label: "Non-binary people", value: "Non-binary" },
];

const RELIGION_OPTIONS = [
  "Agnostic", "Atheist", "Buddhist", "Catholic", "Christian",
  "Hindu", "Jewish", "Muslim", "Spiritual", "Other",
];

function inchesToLabel(inches: number): string {
  const ft = Math.floor(inches / 12);
  const rem = inches % 12;
  return `${ft}'${rem}"`;
}

function calculateAge(dobString: string): number {
  const dob = new Date(dobString + "T00:00:00");
  const today = new Date();
  let age = today.getFullYear() - dob.getFullYear();
  const monthDiff = today.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
    age--;
  }
  return age;
}

export default function DatingPreferencesScreen() {
  const { checkOnboarding } = useAuth();
  const router = useRouter();
  const scrollRef = useRef<ScrollView>(null);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Gender preference
  const [genderPreference, setGenderPreference] = useState<string[]>([]);

  // Age range
  const [ageRange, setAgeRange] = useState<[number, number]>([23, 33]);

  // Distance
  const [maxDistance, setMaxDistance] = useState(50);

  // Height preference
  const [heightEnabled, setHeightEnabled] = useState(false);
  const [heightRange, setHeightRange] = useState<[number, number]>([60, 72]);

  // Religion preference
  const [religionEnabled, setReligionEnabled] = useState(false);
  const [religionPreference, setReligionPreference] = useState<string[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const p = await getMyProfile();

        // Gender preference
        if (p.gender_preference && p.gender_preference.length > 0) {
          setGenderPreference(p.gender_preference);
        }

        // Age range: default from user's age +/- 5
        if (p.date_of_birth) {
          const age = calculateAge(p.date_of_birth);
          const defaultMin = Math.max(18, age - 5);
          const defaultMax = Math.min(100, age + 5);
          setAgeRange([
            p.age_range_min !== 18 || p.age_range_max !== 99
              ? p.age_range_min
              : defaultMin,
            p.age_range_min !== 18 || p.age_range_max !== 99
              ? p.age_range_max
              : defaultMax,
          ]);
        } else {
          setAgeRange([p.age_range_min, p.age_range_max]);
        }

        // Distance
        setMaxDistance(p.max_distance_km || 50);

        // Height preference
        if (p.height_pref_min != null && p.height_pref_max != null) {
          setHeightEnabled(true);
          setHeightRange([p.height_pref_min, p.height_pref_max]);
        }

        // Religion preference
        if (p.religion_preference && p.religion_preference.length > 0) {
          setReligionEnabled(true);
          setReligionPreference(p.religion_preference);
        }
      } catch {
        // Ignore — defaults are fine
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function toggleGender(value: string) {
    setGenderPreference((prev) =>
      prev.includes(value) ? prev.filter((g) => g !== value) : [...prev, value]
    );
  }

  function toggleReligion(value: string) {
    setReligionPreference((prev) =>
      prev.includes(value) ? prev.filter((r) => r !== value) : [...prev, value]
    );
  }

  async function handleSubmit() {
    if (genderPreference.length === 0) {
      Alert.alert("Required", "Please select at least one gender preference.");
      scrollRef.current?.scrollTo({ y: 0, animated: true });
      return;
    }

    setSubmitting(true);
    try {
      await updateMyProfile({
        gender_preference: genderPreference,
        age_range_min: ageRange[0],
        age_range_max: ageRange[1],
        max_distance_km: maxDistance,
        height_pref_min: heightEnabled ? heightRange[0] : null,
        height_pref_max: heightEnabled ? heightRange[1] : null,
        religion_preference: religionEnabled && religionPreference.length > 0 ? religionPreference : null,
        dating_preferences_complete: true,
      });
      await checkOnboarding();
      router.replace("/onboarding");
    } catch (err: any) {
      Alert.alert("Error", getErrorMessage(err, "Failed to save preferences. Please try again."));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
          <ActivityIndicator size="large" color="#e91e63" />
        </View>
      </SafeAreaView>
    );
  }

  const canSubmit = genderPreference.length > 0;

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView
        ref={scrollRef}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.title}>Dating Preferences</Text>
        <Text style={styles.subtitle}>
          Tell us who you're looking for. You can change these anytime.
        </Text>

        {/* ── Gender Preference ── */}
        <Text style={styles.sectionTitle}>I'm interested in *</Text>
        <View style={styles.chipRow}>
          {GENDER_CHIPS.map((chip) => (
            <TouchableOpacity
              key={chip.value}
              style={[
                styles.chip,
                genderPreference.includes(chip.value) && styles.chipSelected,
              ]}
              onPress={() => toggleGender(chip.value)}
            >
              <Text
                style={[
                  styles.chipText,
                  genderPreference.includes(chip.value) && styles.chipTextSelected,
                ]}
              >
                {chip.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        {genderPreference.length === 0 && (
          <Text style={styles.errorText}>Select at least one</Text>
        )}

        {/* ── Age Range ── */}
        <Text style={styles.sectionTitle}>
          Age range: {ageRange[0]} - {ageRange[1]}
        </Text>
        <View style={styles.sliderContainer}>
          <MultiSlider
            values={[ageRange[0], ageRange[1]]}
            min={18}
            max={100}
            step={1}
            sliderLength={280}
            onValuesChange={(values) => setAgeRange([values[0], values[1]])}
            selectedStyle={{ backgroundColor: "#e91e63" }}
            markerStyle={styles.marker}
            unselectedStyle={{ backgroundColor: "#ddd" }}
          />
        </View>

        {/* ── Max Distance ── */}
        <Text style={styles.sectionTitle}>
          Maximum distance: {maxDistance} km
        </Text>
        <View style={styles.sliderContainer}>
          <MultiSlider
            values={[maxDistance]}
            min={1}
            max={500}
            step={1}
            sliderLength={280}
            onValuesChange={(values) => setMaxDistance(values[0])}
            selectedStyle={{ backgroundColor: "#e91e63" }}
            markerStyle={styles.marker}
            unselectedStyle={{ backgroundColor: "#ddd" }}
          />
        </View>

        {/* ── Height Preference ── */}
        <View style={styles.toggleRow}>
          <Text style={styles.sectionTitle}>Height preference</Text>
          <Switch
            value={heightEnabled}
            onValueChange={setHeightEnabled}
            trackColor={{ false: "#ddd", true: "#f48fb1" }}
            thumbColor={heightEnabled ? "#e91e63" : "#ccc"}
          />
        </View>
        {heightEnabled && (
          <>
            <Text style={styles.rangeLabel}>
              {inchesToLabel(heightRange[0])} - {inchesToLabel(heightRange[1])}
            </Text>
            <View style={styles.sliderContainer}>
              <MultiSlider
                values={[heightRange[0], heightRange[1]]}
                min={48}
                max={84}
                step={1}
                sliderLength={280}
                onValuesChange={(values) => setHeightRange([values[0], values[1]])}
                selectedStyle={{ backgroundColor: "#e91e63" }}
                markerStyle={styles.marker}
                unselectedStyle={{ backgroundColor: "#ddd" }}
              />
            </View>
          </>
        )}

        {/* ── Religion Preference ── */}
        <View style={styles.toggleRow}>
          <Text style={styles.sectionTitle}>Religion preference</Text>
          <Switch
            value={religionEnabled}
            onValueChange={(val) => {
              setReligionEnabled(val);
              if (!val) setReligionPreference([]);
            }}
            trackColor={{ false: "#ddd", true: "#f48fb1" }}
            thumbColor={religionEnabled ? "#e91e63" : "#ccc"}
          />
        </View>
        {religionEnabled && (
          <View style={styles.chipRow}>
            {RELIGION_OPTIONS.map((r) => (
              <TouchableOpacity
                key={r}
                style={[
                  styles.chip,
                  religionPreference.includes(r) && styles.chipSelected,
                ]}
                onPress={() => toggleReligion(r)}
              >
                <Text
                  style={[
                    styles.chipText,
                    religionPreference.includes(r) && styles.chipTextSelected,
                  ]}
                >
                  {r}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* ── Submit ── */}
        <TouchableOpacity
          style={[styles.submitButton, (!canSubmit || submitting) && styles.submitDisabled]}
          onPress={handleSubmit}
          disabled={!canSubmit || submitting}
        >
          {submitting ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.submitText}>Continue</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  content: { paddingHorizontal: 20, paddingBottom: 60 },
  title: { fontSize: 26, fontWeight: "bold", color: "#1a1a1a", marginTop: 8 },
  subtitle: { fontSize: 14, color: "#888", marginTop: 4, marginBottom: 16 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "700",
    marginTop: 24,
    marginBottom: 8,
    color: "#e91e63",
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  chip: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: "#f0f0f0",
    borderWidth: 1,
    borderColor: "#ddd",
  },
  chipSelected: {
    backgroundColor: "#fce4ec",
    borderColor: "#e91e63",
  },
  chipText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#555",
  },
  chipTextSelected: {
    color: "#e91e63",
  },
  errorText: { color: "#e91e63", fontSize: 12, marginTop: 4 },
  sliderContainer: {
    alignItems: "center",
    marginTop: 4,
  },
  marker: {
    backgroundColor: "#e91e63",
    height: 24,
    width: 24,
    borderRadius: 12,
  },
  toggleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  rangeLabel: {
    fontSize: 14,
    color: "#555",
    textAlign: "center",
    marginBottom: 4,
  },
  submitButton: {
    backgroundColor: "#e91e63",
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 32,
  },
  submitDisabled: { opacity: 0.5 },
  submitText: { color: "#fff", fontSize: 17, fontWeight: "700" },
});
