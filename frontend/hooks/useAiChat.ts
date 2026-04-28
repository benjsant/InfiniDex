"use client";

import { useState, useCallback, useRef } from "react";
import { askAi } from "@/lib/api";
import type { HistoryMessage } from "@/types/api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export function useAiChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ref tracks latest messages so sendMessage doesn't need them as a dep.
  const messagesRef = useRef<ChatMessage[]>([]);
  messagesRef.current = messages;

  const sendMessage = useCallback(
    async (message: string, context?: string) => {
      setError(null);

      // Completed exchanges = history for this request (exclude empty placeholders).
      const history: HistoryMessage[] = messagesRef.current
        .filter((m) => m.content.trim() !== "")
        .map((m) => ({ role: m.role, content: m.content }));

      setMessages((prev) => [
        ...prev.filter((m) => m.content.trim() !== ""),
        { role: "user", content: message },
        { role: "assistant", content: "" },
      ]);
      setIsStreaming(true);

      try {
        const res = await askAi({ message, context, history });
        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let done = false;
        while (!done) {
          const { value, done: doneReading } = await reader.read();
          done = doneReading;
          if (value) {
            const chunk = decoder.decode(value, { stream: true });
            setMessages((cur) => {
              const updated = [...cur];
              const last = updated[updated.length - 1];
              updated[updated.length - 1] = {
                ...last,
                content: last.content + chunk,
              };
              return updated;
            });
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur inconnue");
        setMessages((cur) => cur.slice(0, -1));
      } finally {
        setIsStreaming(false);
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isStreaming, error, sendMessage, reset };
}
