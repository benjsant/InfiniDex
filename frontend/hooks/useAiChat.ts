"use client";

import { useState, useCallback, useRef } from "react";
import { askAi } from "@/lib/api";
import type { HistoryMessage } from "@/types/api";

export interface WebSource {
  title: string;
  url: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolCalls?: string[];
  sources?: string[];
  webUrls?: WebSource[];
  totalTokens?: number;
}

// 3 minutes — covers the full agent loop (5 iterations × ~30s worst-case LLM)
const AI_TIMEOUT_MS = 180_000;

export function useAiChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ref tracks latest messages so sendMessage doesn't need them as a dep.
  const messagesRef = useRef<ChatMessage[]>([]);
  messagesRef.current = messages;

  // Abort controller for the current in-flight request.
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (message: string, context?: string) => {
      setError(null);

      // Cancel any in-flight request before starting a new one.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const timeoutId = setTimeout(() => {
        controller.abort("timeout");
      }, AI_TIMEOUT_MS);

      const history: HistoryMessage[] = messagesRef.current
        .filter((m) => m.content.trim() !== "")
        .map((m) => ({ role: m.role, content: m.content.slice(0, 7900) }))
        .slice(-30);

      const safeContext = context ? context.slice(0, 1900) : undefined;

      setMessages((prev) => [
        ...prev.filter((m) => m.content.trim() !== ""),
        { role: "user", content: message },
        { role: "assistant", content: "", toolCalls: [] },
      ]);
      setIsStreaming(true);

      try {
        const res = await askAi({ message, context: safeContext, history }, controller.signal);
        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";
        let done = false;

        while (!done) {
          const { value, done: doneReading } = await reader.read();
          done = doneReading;
          if (value) {
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";

            for (const line of lines) {
              if (!line.startsWith("data: ")) continue;
              try {
                const event = JSON.parse(line.slice(6)) as {
                  type: "tool_call" | "token" | "source" | "usage" | "error";
                  name?: string;
                  chunk?: string;
                  sources?: string[];
                  web_urls?: WebSource[];
                  total_tokens?: number;
                  message?: string;
                };

                if (event.type === "tool_call" && event.name) {
                  setMessages((cur) => {
                    const updated = [...cur];
                    const last = updated[updated.length - 1];
                    updated[updated.length - 1] = {
                      ...last,
                      toolCalls: [...(last.toolCalls ?? []), event.name!],
                    };
                    return updated;
                  });
                } else if (event.type === "token" && event.chunk != null) {
                  setMessages((cur) => {
                    const updated = [...cur];
                    const last = updated[updated.length - 1];
                    updated[updated.length - 1] = {
                      ...last,
                      content: last.content + event.chunk,
                    };
                    return updated;
                  });
                } else if (event.type === "source" && event.sources) {
                  setMessages((cur) => {
                    const updated = [...cur];
                    const last = updated[updated.length - 1];
                    updated[updated.length - 1] = {
                      ...last,
                      sources: event.sources,
                      webUrls: event.web_urls ?? [],
                    };
                    return updated;
                  });
                } else if (event.type === "usage" && event.total_tokens != null) {
                  setMessages((cur) => {
                    const updated = [...cur];
                    const last = updated[updated.length - 1];
                    updated[updated.length - 1] = { ...last, totalTokens: event.total_tokens };
                    return updated;
                  });
                } else if (event.type === "error") {
                  setError(event.message ?? "Une erreur est survenue.");
                  setMessages((cur) => cur.slice(0, -1));
                  done = true;
                }
              } catch {
                // Malformed SSE line — skip.
              }
            }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          const isTimeout = (err.message === "timeout" || controller.signal.reason === "timeout");
          setError(isTimeout
            ? "La réponse a pris trop de temps. Réessaie."
            : null  // user-initiated cancel — no error shown
          );
        } else {
          setError(err instanceof Error ? err.message : "Erreur inconnue");
        }
        setMessages((cur) => cur.slice(0, -1));
      } finally {
        clearTimeout(timeoutId);
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort("user-cancel");
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isStreaming, error, sendMessage, cancel, reset };
}
