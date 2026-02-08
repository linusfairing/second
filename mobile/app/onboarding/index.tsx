import { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { sendChatMessage, getChatHistory } from "../../src/api/chat";
import { useAuth } from "../../src/context/AuthContext";
import { ChatMessageResponse } from "../../src/types/api";

interface Message {
  id: string;
  role: string;
  content: string;
}

export default function OnboardingScreen() {
  const { checkOnboarding } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    try {
      const history = await getChatHistory();
      if (history.length > 0) {
        setMessages(
          history.map((m: ChatMessageResponse) => ({
            id: m.id,
            role: m.role,
            content: m.content,
          }))
        );
      } else {
        await handleSend("Hello");
      }
    } catch (err) {
      console.error("Failed to load chat history:", err);
      await handleSend("Hello");
    }
  }

  async function handleSend(text?: string) {
    const msg = text ?? input.trim();
    if (!msg || sending) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: msg,
    };
    setMessages((prev) => [...prev, userMsg]);
    if (!text) setInput("");
    setSending(true);

    try {
      const res = await sendChatMessage(msg);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.reply,
      };
      setMessages((prev) => [...prev, aiMsg]);

      if (res.onboarding_status === "completed") {
        await checkOnboarding();
      }
    } catch (err) {
      console.error("Failed to send chat message:", err);
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Something went wrong. Please try again.",
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setSending(false);
    }
  }

  function renderMessage({ item }: { item: Message }) {
    const isUser = item.role === "user";
    return (
      <View
        style={[
          styles.messageBubble,
          isUser ? styles.userBubble : styles.aiBubble,
        ]}
      >
        <Text style={[styles.messageText, isUser && styles.userText]}>
          {item.content}
        </Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Let's get to know you</Text>
          <Text style={styles.headerSubtitle}>
            Answer a few questions to set up your profile
          </Text>
        </View>
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={renderMessage}
          contentContainerStyle={styles.messageList}
          onContentSizeChange={() =>
            flatListRef.current?.scrollToEnd({ animated: true })
          }
        />
        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            placeholder="Type your answer..."
            value={input}
            onChangeText={setInput}
            editable={!sending}
            onSubmitEditing={() => handleSend()}
            returnKeyType="send"
            maxLength={2000}
          />
          <TouchableOpacity
            style={[styles.sendButton, sending && styles.sendDisabled]}
            onPress={() => handleSend()}
            disabled={sending || !input.trim()}
          >
            <Text style={styles.sendText}>Send</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  header: { paddingHorizontal: 24, paddingBottom: 16 },
  headerTitle: { fontSize: 22, fontWeight: "bold" },
  headerSubtitle: { fontSize: 14, color: "#888", marginTop: 4 },
  messageList: { paddingHorizontal: 16, paddingBottom: 8 },
  messageBubble: {
    maxWidth: "80%",
    padding: 12,
    borderRadius: 16,
    marginVertical: 4,
  },
  userBubble: {
    backgroundColor: "#e91e63",
    alignSelf: "flex-end",
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    backgroundColor: "#f0f0f0",
    alignSelf: "flex-start",
    borderBottomLeftRadius: 4,
  },
  messageText: { fontSize: 15, color: "#333" },
  userText: { color: "#fff" },
  inputRow: {
    flexDirection: "row",
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: "#eee",
    alignItems: "center",
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    marginRight: 8,
  },
  sendButton: {
    backgroundColor: "#e91e63",
    borderRadius: 20,
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  sendDisabled: { opacity: 0.5 },
  sendText: { color: "#fff", fontWeight: "600" },
});
