import { useState, useRef, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  Image,
  Modal,
  FlatList,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as ImagePicker from "expo-image-picker";
import { useAuth } from "../../src/context/AuthContext";
import { getMyProfile, submitProfileSetup, uploadPhoto, deletePhoto } from "../../src/api/profile";
import { PhotoResponse, ProfileSetupRequest } from "../../src/types/api";
import { photoUrl } from "../../src/config";

// ── Option Data ──────────────────────────────────────────────────────────

const GENDER_OPTIONS = ["Man", "Woman", "Non-binary", "Other"];
const ORIENTATION_OPTIONS = [
  "Straight", "Gay", "Lesbian", "Bisexual", "Pansexual", "Asexual", "Queer", "Other",
];
const EDUCATION_OPTIONS = [
  "High school", "Some college", "Associate's", "Bachelor's", "Master's", "PhD", "Trade school", "Other",
];
const RELIGION_OPTIONS = [
  "Agnostic", "Atheist", "Buddhist", "Catholic", "Christian", "Hindu",
  "Jewish", "Muslim", "Spiritual", "Other", "Prefer not to say",
];
const CHILDREN_OPTIONS = ["No", "Yes, they live with me", "Yes, they don't live with me"];
const FAMILY_PLANS_OPTIONS = ["Want someday", "Don't want", "Have and want more", "Have and don't want more", "Not sure"];
const DRINKING_OPTIONS = ["Never", "Rarely", "Socially", "Regularly"];
const SMOKING_OPTIONS = ["Never", "Socially", "Regularly", "Trying to quit"];
const MARIJUANA_OPTIONS = ["Never", "Socially", "Regularly"];
const DRUGS_OPTIONS = ["Never", "Socially", "Prefer not to say"];

const HEIGHT_OPTIONS: { label: string; value: number }[] = [];
for (let inches = 48; inches <= 84; inches++) {
  const ft = Math.floor(inches / 12);
  const rem = inches % 12;
  HEIGHT_OPTIONS.push({ label: `${ft}'${rem}" (${inches}")`, value: inches });
}

const LANGUAGES = [
  "English", "Spanish", "French", "German", "Italian", "Portuguese", "Chinese (Mandarin)",
  "Chinese (Cantonese)", "Japanese", "Korean", "Arabic", "Hindi", "Bengali", "Urdu",
  "Russian", "Turkish", "Vietnamese", "Thai", "Indonesian", "Malay", "Filipino (Tagalog)",
  "Dutch", "Polish", "Czech", "Slovak", "Hungarian", "Romanian", "Greek",
  "Swedish", "Norwegian", "Danish", "Finnish", "Hebrew", "Persian (Farsi)", "Swahili",
  "Amharic", "Yoruba", "Igbo", "Hausa", "Zulu", "Afrikaans", "Ukrainian",
  "Serbian", "Croatian", "Bosnian", "Bulgarian", "Slovenian", "Catalan", "Basque",
  "Galician", "Welsh", "Irish", "Scottish Gaelic", "Latvian", "Lithuanian", "Estonian",
  "Georgian", "Armenian", "Kazakh", "Uzbek", "Azerbaijani", "Pashto", "Kurdish",
  "Tamil", "Telugu", "Kannada", "Malayalam", "Marathi", "Gujarati", "Punjabi",
  "Sinhala", "Nepali", "Burmese", "Khmer", "Lao", "Mongolian", "Tibetan",
  "Hawaiian", "Samoan", "Tongan", "Maori", "Haitian Creole", "Esperanto",
  "Latin", "American Sign Language (ASL)", "British Sign Language (BSL)",
  "Somali", "Tigrinya", "Twi", "Xhosa", "Cebuano", "Hmong",
  "Navajo", "Cherokee", "Quechua", "Guarani", "Aymara", "Tok Pisin",
  "Fijian", "Maltese", "Luxembourgish", "Icelandic", "Albanian",
];

// ── Reusable Select Modal ────────────────────────────────────────────────

function SelectModal({
  visible,
  title,
  options,
  selected,
  onSelect,
  onClose,
  allowOther,
}: {
  visible: boolean;
  title: string;
  options: string[];
  selected: string;
  onSelect: (val: string) => void;
  onClose: () => void;
  allowOther?: boolean;
}) {
  const [otherText, setOtherText] = useState("");
  const [showOtherInput, setShowOtherInput] = useState(false);

  // Reset "Other" input state when modal opens/closes
  useEffect(() => {
    if (visible) {
      setShowOtherInput(false);
      setOtherText("");
    }
  }, [visible]);

  // Check if the current selected value is a custom "Other" value (not in the options list)
  const isCustomValue = allowOther && selected && !options.includes(selected);

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={modalStyles.overlay}>
        <View style={modalStyles.sheet}>
          <Text style={modalStyles.title}>{title}</Text>
          <FlatList
            data={options}
            keyExtractor={(item) => item}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={[
                  modalStyles.option,
                  selected === item && modalStyles.optionSelected,
                ]}
                onPress={() => {
                  if (item === "Other" && allowOther) {
                    setShowOtherInput(true);
                  } else {
                    onSelect(item);
                    onClose();
                  }
                }}
              >
                <Text
                  style={[
                    modalStyles.optionText,
                    selected === item && modalStyles.optionTextSelected,
                  ]}
                >
                  {item}
                </Text>
              </TouchableOpacity>
            )}
          />
          {isCustomValue && !showOtherInput && (
            <Text style={modalStyles.selectedLabel}>Current: {selected}</Text>
          )}
          {showOtherInput && (
            <View style={modalStyles.otherRow}>
              <TextInput
                style={modalStyles.otherInput}
                placeholder="Type your answer..."
                value={otherText}
                onChangeText={setOtherText}
                autoFocus
              />
              <TouchableOpacity
                style={modalStyles.otherDone}
                onPress={() => {
                  if (otherText.trim()) {
                    onSelect(otherText.trim());
                    setOtherText("");
                    setShowOtherInput(false);
                    onClose();
                  }
                }}
              >
                <Text style={modalStyles.otherDoneText}>Done</Text>
              </TouchableOpacity>
            </View>
          )}
          <TouchableOpacity style={modalStyles.cancel} onPress={onClose}>
            <Text style={modalStyles.cancelText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

// ── Height Picker Modal ──────────────────────────────────────────────────

function HeightModal({
  visible,
  selected,
  onSelect,
  onClose,
}: {
  visible: boolean;
  selected: number | null;
  onSelect: (val: number) => void;
  onClose: () => void;
}) {
  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={modalStyles.overlay}>
        <View style={modalStyles.sheet}>
          <Text style={modalStyles.title}>Height</Text>
          <FlatList
            data={HEIGHT_OPTIONS}
            keyExtractor={(item) => String(item.value)}
            initialScrollIndex={
              selected ? Math.max(0, HEIGHT_OPTIONS.findIndex((h) => h.value === selected)) : 20
            }
            getItemLayout={(_, index) => ({
              length: 48,
              offset: 48 * index,
              index,
            })}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={[
                  modalStyles.option,
                  selected === item.value && modalStyles.optionSelected,
                ]}
                onPress={() => {
                  onSelect(item.value);
                  onClose();
                }}
              >
                <Text
                  style={[
                    modalStyles.optionText,
                    selected === item.value && modalStyles.optionTextSelected,
                  ]}
                >
                  {item.label}
                </Text>
              </TouchableOpacity>
            )}
          />
          <TouchableOpacity style={modalStyles.cancel} onPress={onClose}>
            <Text style={modalStyles.cancelText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

// ── Language Multi-Select Modal ──────────────────────────────────────────

function LanguageModal({
  visible,
  selected,
  onDone,
  onClose,
}: {
  visible: boolean;
  selected: string[];
  onDone: (langs: string[]) => void;
  onClose: () => void;
}) {
  const [search, setSearch] = useState("");
  const [localSelected, setLocalSelected] = useState<string[]>(selected);
  const [customLang, setCustomLang] = useState("");

  // Sync local state with parent when modal opens
  useEffect(() => {
    if (visible) {
      setLocalSelected(selected);
      setSearch("");
      setCustomLang("");
    }
  }, [visible]);

  // Include custom languages (not in LANGUAGES) so they can be toggled off
  const customInSelected = localSelected.filter((l) => !LANGUAGES.includes(l));
  const filtered = [
    ...customInSelected.filter((l) => l.toLowerCase().includes(search.toLowerCase())),
    ...LANGUAGES.filter((l) => l.toLowerCase().includes(search.toLowerCase())),
  ];

  function toggle(lang: string) {
    setLocalSelected((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
  }

  function addCustom() {
    const trimmed = customLang.trim();
    if (trimmed && !localSelected.includes(trimmed)) {
      setLocalSelected((prev) => [...prev, trimmed]);
      setCustomLang("");
    }
  }

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={modalStyles.overlay}>
        <View style={[modalStyles.sheet, { maxHeight: "80%" }]}>
          <Text style={modalStyles.title}>Languages</Text>
          <TextInput
            style={modalStyles.searchInput}
            placeholder="Search languages..."
            value={search}
            onChangeText={setSearch}
          />
          <FlatList
            data={filtered}
            keyExtractor={(item) => item}
            style={{ maxHeight: 300 }}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={[
                  modalStyles.option,
                  localSelected.includes(item) && modalStyles.optionSelected,
                ]}
                onPress={() => toggle(item)}
              >
                <Text
                  style={[
                    modalStyles.optionText,
                    localSelected.includes(item) && modalStyles.optionTextSelected,
                  ]}
                >
                  {localSelected.includes(item) ? "\u2713 " : ""}
                  {item}
                </Text>
              </TouchableOpacity>
            )}
          />
          <View style={modalStyles.otherRow}>
            <TextInput
              style={modalStyles.otherInput}
              placeholder="Add custom language..."
              value={customLang}
              onChangeText={setCustomLang}
              onSubmitEditing={addCustom}
            />
            <TouchableOpacity style={modalStyles.otherDone} onPress={addCustom}>
              <Text style={modalStyles.otherDoneText}>Add</Text>
            </TouchableOpacity>
          </View>
          {localSelected.length > 0 && (
            <Text style={modalStyles.selectedLabel}>
              Selected: {localSelected.join(", ")}
            </Text>
          )}
          <TouchableOpacity
            style={[modalStyles.doneButton, localSelected.length === 0 && { opacity: 0.5 }]}
            disabled={localSelected.length === 0}
            onPress={() => {
              onDone(localSelected);
              onClose();
            }}
          >
            <Text style={modalStyles.doneButtonText}>Done ({localSelected.length})</Text>
          </TouchableOpacity>
          <TouchableOpacity style={modalStyles.cancel} onPress={onClose}>
            <Text style={modalStyles.cancelText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

// ── Date Picker Modal ────────────────────────────────────────────────────

function DatePickerModal({
  visible,
  value,
  onSelect,
  onClose,
}: {
  visible: boolean;
  value: Date | null;
  onSelect: (d: Date) => void;
  onClose: () => void;
}) {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(value?.getFullYear() ?? 1995);
  const [month, setMonth] = useState(value ? value.getMonth() + 1 : 6);
  const [day, setDay] = useState(value?.getDate() ?? 15);

  // Sync local state with parent when modal opens
  useEffect(() => {
    if (visible) {
      setYear(value?.getFullYear() ?? 1995);
      setMonth(value ? value.getMonth() + 1 : 6);
      setDay(value?.getDate() ?? 15);
    }
  }, [visible]);

  const years = Array.from({ length: currentYear - 18 - 1920 + 1 }, (_, i) => currentYear - 18 - i);
  const months = Array.from({ length: 12 }, (_, i) => i + 1);
  const daysInMonth = new Date(year, month, 0).getDate();
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  // Auto-clamp day when month/year change reduces available days
  useEffect(() => {
    if (day > daysInMonth) setDay(daysInMonth);
  }, [daysInMonth]);

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={modalStyles.overlay}>
        <View style={modalStyles.sheet}>
          <Text style={modalStyles.title}>Date of Birth</Text>
          <View style={{ flexDirection: "row", justifyContent: "space-around", marginBottom: 16 }}>
            <View style={{ alignItems: "center" }}>
              <Text style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>Year</Text>
              <ScrollView style={{ height: 150, width: 80 }}>
                {years.map((y) => (
                  <TouchableOpacity
                    key={y}
                    onPress={() => setYear(y)}
                    style={[modalStyles.option, year === y && modalStyles.optionSelected]}
                  >
                    <Text style={[modalStyles.optionText, year === y && modalStyles.optionTextSelected]}>
                      {y}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
            <View style={{ alignItems: "center" }}>
              <Text style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>Month</Text>
              <ScrollView style={{ height: 150, width: 60 }}>
                {months.map((m) => (
                  <TouchableOpacity
                    key={m}
                    onPress={() => setMonth(m)}
                    style={[modalStyles.option, month === m && modalStyles.optionSelected]}
                  >
                    <Text style={[modalStyles.optionText, month === m && modalStyles.optionTextSelected]}>
                      {m}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
            <View style={{ alignItems: "center" }}>
              <Text style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>Day</Text>
              <ScrollView style={{ height: 150, width: 60 }}>
                {days.map((d) => (
                  <TouchableOpacity
                    key={d}
                    onPress={() => setDay(d)}
                    style={[modalStyles.option, day === d && modalStyles.optionSelected]}
                  >
                    <Text style={[modalStyles.optionText, day === d && modalStyles.optionTextSelected]}>
                      {d}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          </View>
          <TouchableOpacity
            style={modalStyles.doneButton}
            onPress={() => {
              const clampedDay = Math.min(day, daysInMonth);
              onSelect(new Date(year, month - 1, clampedDay));
              onClose();
            }}
          >
            <Text style={modalStyles.doneButtonText}>Done</Text>
          </TouchableOpacity>
          <TouchableOpacity style={modalStyles.cancel} onPress={onClose}>
            <Text style={modalStyles.cancelText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

// ── Eye Toggle ───────────────────────────────────────────────────────────

function EyeToggle({
  field,
  hidden,
  onToggle,
}: {
  field: string;
  hidden: boolean;
  onToggle: (field: string) => void;
}) {
  return (
    <TouchableOpacity onPress={() => onToggle(field)} style={styles.eyeButton}>
      <Text style={{ fontSize: 18 }}>{hidden ? "\u{1F648}" : "\u{1F441}"}</Text>
    </TouchableOpacity>
  );
}

// ── Main Screen ──────────────────────────────────────────────────────────

export default function ProfileSetupScreen() {
  const { checkOnboarding } = useAuth();
  const scrollRef = useRef<ScrollView>(null);

  // Form state
  const [displayName, setDisplayName] = useState("");
  const [dob, setDob] = useState<Date | null>(null);
  const [heightInches, setHeightInches] = useState<number | null>(null);
  const [location, setLocation] = useState("");
  const [homeTown, setHomeTown] = useState("");
  const [gender, setGender] = useState("");
  const [sexualOrientation, setSexualOrientation] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [collegeUniversity, setCollegeUniversity] = useState("");
  const [educationLevel, setEducationLevel] = useState("");
  const [languages, setLanguages] = useState<string[]>([]);
  const [religion, setReligion] = useState("");
  const [children, setChildren] = useState("");
  const [familyPlans, setFamilyPlans] = useState("");
  const [drinking, setDrinking] = useState("");
  const [smoking, setSmoking] = useState("");
  const [marijuana, setMarijuana] = useState("");
  const [drugs, setDrugs] = useState("");
  const [hiddenFields, setHiddenFields] = useState<string[]>([]);

  // Photos
  const [photos, setPhotos] = useState<PhotoResponse[]>([]);
  const [uploading, setUploading] = useState(false);

  // Modal visibility
  const [showDob, setShowDob] = useState(false);
  const [showHeight, setShowHeight] = useState(false);
  const [showGender, setShowGender] = useState(false);
  const [showOrientation, setShowOrientation] = useState(false);
  const [showEducation, setShowEducation] = useState(false);
  const [showLanguages, setShowLanguages] = useState(false);
  const [showReligion, setShowReligion] = useState(false);
  const [showChildren, setShowChildren] = useState(false);
  const [showFamilyPlans, setShowFamilyPlans] = useState(false);
  const [showDrinking, setShowDrinking] = useState(false);
  const [showSmoking, setShowSmoking] = useState(false);
  const [showMarijuana, setShowMarijuana] = useState(false);
  const [showDrugs, setShowDrugs] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Load existing photos on mount (supports re-entry)
  useEffect(() => {
    (async () => {
      try {
        const profile = await getMyProfile();
        if (profile.photos && profile.photos.length > 0) {
          setPhotos(profile.photos);
        }
      } catch {
        // Ignore — user may not have photos yet
      }
    })();
  }, []);

  function toggleHidden(field: string) {
    setHiddenFields((prev) =>
      prev.includes(field) ? prev.filter((f) => f !== field) : [...prev, field]
    );
  }

  function formatDate(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  function heightLabel(inches: number): string {
    const ft = Math.floor(inches / 12);
    const rem = inches % 12;
    return `${ft}'${rem}"`;
  }

  async function handleAddPhoto() {
    if (photos.length >= 6) {
      Alert.alert("Maximum photos", "You can upload up to 6 photos.");
      return;
    }

    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      Alert.alert("Permission needed", "Please allow access to your photo library.");
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      setUploading(true);
      try {
        const photo = await uploadPhoto(result.assets[0].uri);
        setPhotos((prev) => [...prev, photo]);
      } catch (err) {
        console.error("Failed to upload photo:", err);
        Alert.alert("Error", "Failed to upload photo.");
      } finally {
        setUploading(false);
      }
    }
  }

  async function handleDeletePhoto(photoId: string) {
    try {
      await deletePhoto(photoId);
      setPhotos((prev) => prev.filter((p) => p.id !== photoId));
    } catch (err) {
      console.error("Failed to delete photo:", err);
      Alert.alert("Error", "Failed to delete photo.");
    }
  }

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!displayName.trim()) errs.displayName = "Required";
    if (!dob) errs.dob = "Required";
    if (!heightInches) errs.heightInches = "Required";
    if (!location.trim()) errs.location = "Required";
    if (!homeTown.trim()) errs.homeTown = "Required";
    if (!gender) errs.gender = "Required";
    if (!sexualOrientation) errs.sexualOrientation = "Required";
    if (!jobTitle.trim()) errs.jobTitle = "Required";
    if (!collegeUniversity.trim()) errs.collegeUniversity = "Required";
    if (!educationLevel) errs.educationLevel = "Required";
    if (languages.length === 0) errs.languages = "Select at least one";
    if (!religion) errs.religion = "Required";
    if (!children) errs.children = "Required";
    if (!familyPlans) errs.familyPlans = "Required";
    if (!drinking) errs.drinking = "Required";
    if (!smoking) errs.smoking = "Required";
    if (!marijuana) errs.marijuana = "Required";
    if (!drugs) errs.drugs = "Required";
    if (photos.length < 3) errs.photos = `Upload at least 3 photos (${photos.length}/3)`;
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit() {
    if (!validate()) {
      scrollRef.current?.scrollTo({ y: 0, animated: true });
      return;
    }

    setSubmitting(true);
    try {
      const payload: ProfileSetupRequest = {
        display_name: displayName.trim(),
        date_of_birth: formatDate(dob!),
        height_inches: heightInches!,
        location: location.trim(),
        home_town: homeTown.trim(),
        gender,
        sexual_orientation: sexualOrientation,
        job_title: jobTitle.trim(),
        college_university: collegeUniversity.trim(),
        education_level: educationLevel,
        languages,
        religion,
        children,
        family_plans: familyPlans,
        drinking,
        smoking,
        marijuana,
        drugs,
        hidden_fields: hiddenFields,
      };

      await submitProfileSetup(payload);
      await checkOnboarding();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      Alert.alert("Error", detail || "Failed to save profile. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit =
    displayName.trim() &&
    dob &&
    heightInches &&
    location.trim() &&
    homeTown.trim() &&
    gender &&
    sexualOrientation &&
    jobTitle.trim() &&
    collegeUniversity.trim() &&
    educationLevel &&
    languages.length > 0 &&
    religion &&
    children &&
    familyPlans &&
    drinking &&
    smoking &&
    marijuana &&
    drugs &&
    photos.length >= 3;

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView
        ref={scrollRef}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.title}>Create Your Profile</Text>
        <Text style={styles.subtitle}>
          Fill in your details. Tap the eye icon to hide a field from others.
        </Text>

        {/* ── Section 1: Basic Info ── */}
        <Text style={styles.sectionTitle}>Basic Info</Text>

        <Text style={styles.label}>Name *</Text>
        <TextInput
          style={[styles.input, errors.displayName && styles.inputError]}
          placeholder="Your name"
          value={displayName}
          onChangeText={setDisplayName}
          maxLength={100}
        />
        {errors.displayName && <Text style={styles.errorText}>{errors.displayName}</Text>}

        <Text style={styles.label}>Date of Birth *</Text>
        <TouchableOpacity
          style={[styles.pickerButton, errors.dob && styles.inputError]}
          onPress={() => setShowDob(true)}
        >
          <Text style={dob ? styles.pickerText : styles.pickerPlaceholder}>
            {dob ? formatDate(dob) : "Select date"}
          </Text>
        </TouchableOpacity>
        {errors.dob && <Text style={styles.errorText}>{errors.dob}</Text>}

        <Text style={styles.label}>Height *</Text>
        <TouchableOpacity
          style={[styles.pickerButton, errors.heightInches && styles.inputError]}
          onPress={() => setShowHeight(true)}
        >
          <Text style={heightInches ? styles.pickerText : styles.pickerPlaceholder}>
            {heightInches ? heightLabel(heightInches) : "Select height"}
          </Text>
        </TouchableOpacity>
        {errors.heightInches && <Text style={styles.errorText}>{errors.heightInches}</Text>}

        <Text style={styles.label}>Location *</Text>
        <TextInput
          style={[styles.input, errors.location && styles.inputError]}
          placeholder="City, State"
          value={location}
          onChangeText={setLocation}
          maxLength={100}
        />
        {errors.location && <Text style={styles.errorText}>{errors.location}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Home Town *</Text>
          </View>
          <EyeToggle field="home_town" hidden={hiddenFields.includes("home_town")} onToggle={toggleHidden} />
        </View>
        <TextInput
          style={[styles.input, errors.homeTown && styles.inputError]}
          placeholder="Where you grew up"
          value={homeTown}
          onChangeText={setHomeTown}
          maxLength={200}
        />
        {errors.homeTown && <Text style={styles.errorText}>{errors.homeTown}</Text>}

        {/* ── Section 2: About You ── */}
        <Text style={styles.sectionTitle}>About You</Text>

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Gender *</Text>
          </View>
          <EyeToggle field="gender" hidden={hiddenFields.includes("gender")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.gender && styles.inputError]}
          onPress={() => setShowGender(true)}
        >
          <Text style={gender ? styles.pickerText : styles.pickerPlaceholder}>
            {gender || "Select gender"}
          </Text>
        </TouchableOpacity>
        {errors.gender && <Text style={styles.errorText}>{errors.gender}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Sexual Orientation *</Text>
          </View>
          <EyeToggle field="sexual_orientation" hidden={hiddenFields.includes("sexual_orientation")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.sexualOrientation && styles.inputError]}
          onPress={() => setShowOrientation(true)}
        >
          <Text style={sexualOrientation ? styles.pickerText : styles.pickerPlaceholder}>
            {sexualOrientation || "Select orientation"}
          </Text>
        </TouchableOpacity>
        {errors.sexualOrientation && <Text style={styles.errorText}>{errors.sexualOrientation}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Job Title *</Text>
          </View>
          <EyeToggle field="job_title" hidden={hiddenFields.includes("job_title")} onToggle={toggleHidden} />
        </View>
        <TextInput
          style={[styles.input, errors.jobTitle && styles.inputError]}
          placeholder="e.g. Software Engineer"
          value={jobTitle}
          onChangeText={setJobTitle}
          maxLength={200}
        />
        {errors.jobTitle && <Text style={styles.errorText}>{errors.jobTitle}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>College / University *</Text>
          </View>
          <EyeToggle field="college_university" hidden={hiddenFields.includes("college_university")} onToggle={toggleHidden} />
        </View>
        <TextInput
          style={[styles.input, errors.collegeUniversity && styles.inputError]}
          placeholder="e.g. MIT"
          value={collegeUniversity}
          onChangeText={setCollegeUniversity}
          maxLength={200}
        />
        {errors.collegeUniversity && <Text style={styles.errorText}>{errors.collegeUniversity}</Text>}

        <Text style={styles.label}>Education Level * <Text style={styles.hint}>(for better matches, not shown on profile)</Text></Text>
        <TouchableOpacity
          style={[styles.pickerButton, errors.educationLevel && styles.inputError]}
          onPress={() => setShowEducation(true)}
        >
          <Text style={educationLevel ? styles.pickerText : styles.pickerPlaceholder}>
            {educationLevel || "Select education level"}
          </Text>
        </TouchableOpacity>
        {errors.educationLevel && <Text style={styles.errorText}>{errors.educationLevel}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Languages *</Text>
          </View>
          <EyeToggle field="languages" hidden={hiddenFields.includes("languages")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.languages && styles.inputError]}
          onPress={() => setShowLanguages(true)}
        >
          <Text style={languages.length > 0 ? styles.pickerText : styles.pickerPlaceholder}>
            {languages.length > 0 ? languages.join(", ") : "Select languages"}
          </Text>
        </TouchableOpacity>
        {errors.languages && <Text style={styles.errorText}>{errors.languages}</Text>}

        {/* ── Section 3: Beliefs & Family ── */}
        <Text style={styles.sectionTitle}>Beliefs & Family</Text>

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Religion *</Text>
          </View>
          <EyeToggle field="religion" hidden={hiddenFields.includes("religion")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.religion && styles.inputError]}
          onPress={() => setShowReligion(true)}
        >
          <Text style={religion ? styles.pickerText : styles.pickerPlaceholder}>
            {religion || "Select religion"}
          </Text>
        </TouchableOpacity>
        {errors.religion && <Text style={styles.errorText}>{errors.religion}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Children *</Text>
          </View>
          <EyeToggle field="children" hidden={hiddenFields.includes("children")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.children && styles.inputError]}
          onPress={() => setShowChildren(true)}
        >
          <Text style={children ? styles.pickerText : styles.pickerPlaceholder}>
            {children || "Select"}
          </Text>
        </TouchableOpacity>
        {errors.children && <Text style={styles.errorText}>{errors.children}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Family Plans *</Text>
          </View>
          <EyeToggle field="family_plans" hidden={hiddenFields.includes("family_plans")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.familyPlans && styles.inputError]}
          onPress={() => setShowFamilyPlans(true)}
        >
          <Text style={familyPlans ? styles.pickerText : styles.pickerPlaceholder}>
            {familyPlans || "Select"}
          </Text>
        </TouchableOpacity>
        {errors.familyPlans && <Text style={styles.errorText}>{errors.familyPlans}</Text>}

        {/* ── Section 4: Lifestyle ── */}
        <Text style={styles.sectionTitle}>Lifestyle</Text>

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Drinking *</Text>
          </View>
          <EyeToggle field="drinking" hidden={hiddenFields.includes("drinking")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.drinking && styles.inputError]}
          onPress={() => setShowDrinking(true)}
        >
          <Text style={drinking ? styles.pickerText : styles.pickerPlaceholder}>
            {drinking || "Select"}
          </Text>
        </TouchableOpacity>
        {errors.drinking && <Text style={styles.errorText}>{errors.drinking}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Smoking *</Text>
          </View>
          <EyeToggle field="smoking" hidden={hiddenFields.includes("smoking")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.smoking && styles.inputError]}
          onPress={() => setShowSmoking(true)}
        >
          <Text style={smoking ? styles.pickerText : styles.pickerPlaceholder}>
            {smoking || "Select"}
          </Text>
        </TouchableOpacity>
        {errors.smoking && <Text style={styles.errorText}>{errors.smoking}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Marijuana *</Text>
          </View>
          <EyeToggle field="marijuana" hidden={hiddenFields.includes("marijuana")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.marijuana && styles.inputError]}
          onPress={() => setShowMarijuana(true)}
        >
          <Text style={marijuana ? styles.pickerText : styles.pickerPlaceholder}>
            {marijuana || "Select"}
          </Text>
        </TouchableOpacity>
        {errors.marijuana && <Text style={styles.errorText}>{errors.marijuana}</Text>}

        <View style={styles.fieldRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Drugs *</Text>
          </View>
          <EyeToggle field="drugs" hidden={hiddenFields.includes("drugs")} onToggle={toggleHidden} />
        </View>
        <TouchableOpacity
          style={[styles.pickerButton, errors.drugs && styles.inputError]}
          onPress={() => setShowDrugs(true)}
        >
          <Text style={drugs ? styles.pickerText : styles.pickerPlaceholder}>
            {drugs || "Select"}
          </Text>
        </TouchableOpacity>
        {errors.drugs && <Text style={styles.errorText}>{errors.drugs}</Text>}

        {/* ── Section 5: Photos ── */}
        <Text style={styles.sectionTitle}>Photos</Text>
        <Text style={styles.photoCounter}>
          {photos.length} of 6 photos (minimum 3 required)
        </Text>
        {errors.photos && <Text style={styles.errorText}>{errors.photos}</Text>}

        <View style={styles.photoGrid}>
          {Array.from({ length: 6 }).map((_, i) => {
            const photo = photos[i];
            if (photo) {
              return (
                <View key={photo.id} style={styles.photoSlot}>
                  <Image source={{ uri: photoUrl(photo.file_path) }} style={styles.photoImage} />
                  <TouchableOpacity
                    style={styles.photoDelete}
                    onPress={() => handleDeletePhoto(photo.id)}
                  >
                    <Text style={styles.photoDeleteText}>X</Text>
                  </TouchableOpacity>
                </View>
              );
            }
            return (
              <TouchableOpacity
                key={`empty-${i}`}
                style={styles.photoSlotEmpty}
                onPress={handleAddPhoto}
                disabled={uploading}
              >
                {uploading && i === photos.length ? (
                  <ActivityIndicator size="small" color="#e91e63" />
                ) : (
                  <Text style={styles.photoAddText}>+</Text>
                )}
              </TouchableOpacity>
            );
          })}
        </View>

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

      {/* ── Modals ── */}
      <DatePickerModal visible={showDob} value={dob} onSelect={setDob} onClose={() => setShowDob(false)} />
      <HeightModal visible={showHeight} selected={heightInches} onSelect={setHeightInches} onClose={() => setShowHeight(false)} />
      <SelectModal visible={showGender} title="Gender" options={GENDER_OPTIONS} selected={gender} onSelect={setGender} onClose={() => setShowGender(false)} allowOther />
      <SelectModal visible={showOrientation} title="Sexual Orientation" options={ORIENTATION_OPTIONS} selected={sexualOrientation} onSelect={setSexualOrientation} onClose={() => setShowOrientation(false)} allowOther />
      <SelectModal visible={showEducation} title="Education Level" options={EDUCATION_OPTIONS} selected={educationLevel} onSelect={setEducationLevel} onClose={() => setShowEducation(false)} allowOther />
      <LanguageModal visible={showLanguages} selected={languages} onDone={setLanguages} onClose={() => setShowLanguages(false)} />
      <SelectModal visible={showReligion} title="Religion" options={RELIGION_OPTIONS} selected={religion} onSelect={setReligion} onClose={() => setShowReligion(false)} allowOther />
      <SelectModal visible={showChildren} title="Children" options={CHILDREN_OPTIONS} selected={children} onSelect={setChildren} onClose={() => setShowChildren(false)} />
      <SelectModal visible={showFamilyPlans} title="Family Plans" options={FAMILY_PLANS_OPTIONS} selected={familyPlans} onSelect={setFamilyPlans} onClose={() => setShowFamilyPlans(false)} />
      <SelectModal visible={showDrinking} title="Drinking" options={DRINKING_OPTIONS} selected={drinking} onSelect={setDrinking} onClose={() => setShowDrinking(false)} />
      <SelectModal visible={showSmoking} title="Smoking" options={SMOKING_OPTIONS} selected={smoking} onSelect={setSmoking} onClose={() => setShowSmoking(false)} />
      <SelectModal visible={showMarijuana} title="Marijuana" options={MARIJUANA_OPTIONS} selected={marijuana} onSelect={setMarijuana} onClose={() => setShowMarijuana(false)} />
      <SelectModal visible={showDrugs} title="Drugs" options={DRUGS_OPTIONS} selected={drugs} onSelect={setDrugs} onClose={() => setShowDrugs(false)} />
    </SafeAreaView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  content: { paddingHorizontal: 20, paddingBottom: 60 },
  title: { fontSize: 26, fontWeight: "bold", marginTop: 8, color: "#1a1a1a" },
  subtitle: { fontSize: 14, color: "#888", marginTop: 4, marginBottom: 16 },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginTop: 28,
    marginBottom: 12,
    color: "#e91e63",
  },
  label: { fontSize: 14, fontWeight: "600", color: "#333", marginTop: 12, marginBottom: 4 },
  hint: { fontSize: 12, fontWeight: "400", color: "#999" },
  input: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: "#333",
    backgroundColor: "#fafafa",
  },
  inputError: { borderColor: "#e91e63" },
  errorText: { color: "#e91e63", fontSize: 12, marginTop: 2 },
  pickerButton: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 13,
    backgroundColor: "#fafafa",
  },
  pickerText: { fontSize: 15, color: "#333" },
  pickerPlaceholder: { fontSize: 15, color: "#aaa" },
  fieldRow: { flexDirection: "row", alignItems: "center", marginTop: 12 },
  eyeButton: { padding: 4, marginLeft: 8 },
  photoCounter: { fontSize: 13, color: "#888", marginBottom: 8 },
  photoGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginBottom: 16,
  },
  photoSlot: {
    width: "30%",
    aspectRatio: 1,
    borderRadius: 10,
    overflow: "hidden",
    position: "relative",
  },
  photoImage: { width: "100%", height: "100%" },
  photoDelete: {
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
  photoDeleteText: { color: "#fff", fontSize: 12, fontWeight: "bold" },
  photoSlotEmpty: {
    width: "30%",
    aspectRatio: 1,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: "#ddd",
    borderStyle: "dashed",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#fafafa",
  },
  photoAddText: { fontSize: 28, color: "#ccc" },
  submitButton: {
    backgroundColor: "#e91e63",
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 24,
  },
  submitDisabled: { opacity: 0.5 },
  submitText: { color: "#fff", fontSize: 17, fontWeight: "700" },
});

const modalStyles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: "#fff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: "70%",
  },
  title: { fontSize: 18, fontWeight: "700", marginBottom: 12, textAlign: "center" },
  option: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  optionSelected: { backgroundColor: "#fce4ec" },
  optionText: { fontSize: 15, color: "#333" },
  optionTextSelected: { color: "#e91e63", fontWeight: "600" },
  cancel: { paddingVertical: 14, alignItems: "center" },
  cancelText: { fontSize: 15, color: "#888" },
  otherRow: { flexDirection: "row", alignItems: "center", marginTop: 8 },
  otherInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 15,
    marginRight: 8,
  },
  otherDone: {
    backgroundColor: "#e91e63",
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  otherDoneText: { color: "#fff", fontWeight: "600" },
  searchInput: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 15,
    marginBottom: 8,
  },
  selectedLabel: { fontSize: 13, color: "#666", marginTop: 8 },
  doneButton: {
    backgroundColor: "#e91e63",
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 12,
  },
  doneButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },
});
