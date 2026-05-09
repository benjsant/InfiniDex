"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { Bot, Cog, Globe, Database, BookOpen, Eye, ThumbsUp, ThumbsDown } from "lucide-react";
import { useAiChat } from "@/hooks/useAiChat";
import { getAiProvider, sendAiFeedback } from "@/lib/api";
import type { ChatMessage } from "@/hooks/useAiChat";
import { AI_TOOL_LABELS, AI_SOURCE_LABELS, AI_SOURCE_COLORS } from "@/lib/constants";
import { PromptModal } from "@/components/ai/PromptModal";

const SUGGESTIONS = [
  "Meilleure fusion Dracaufeu ?",
  "Quelle équipe pour un run Nuzlocke ?",
  "Comment obtenir les Pokémon légendaires dans IF ?",
  "Quels sont les types les plus forts dans Infinite Fusion ?",
];

export function AiChat({
  initialMessage,
  initialContext,
}: {
  initialMessage?: string;
  initialContext?: string;
}) {
  const { messages, isStreaming, error, sendMessage, reset } = useAiChat();
  const [input, setInput] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);
  const [ratings, setRatings] = useState<Record<number, "up" | "down">>({});

  const handleRate = useCallback((msgIndex: number, rating: "up" | "down") => {
    if (ratings[msgIndex]) return;
    setRatings((r) => ({ ...r, [msgIndex]: rating }));
    const question = messages[msgIndex - 1]?.content ?? "";
    const answer   = messages[msgIndex]?.content ?? "";
    sendAiFeedback(question, answer, rating).catch(() => {});
  }, [ratings, messages]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLInputElement>(null);

  const { data: provider } = useQuery({
    queryKey: ["ai-provider"],
    queryFn: getAiProvider,
    staleTime: Infinity,
    retry: false,
  });

  // Intentionally runs on mount only — initial message is a one-shot trigger.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (initialMessage) sendMessage(initialMessage, initialContext); }, []);

  // Scroll to bottom when a new message bubble is added (smooth) or when a
  // token is appended to the current streaming bubble (instant — avoids the
  // animation being cancelled and restarted tens of times per second).
  const prevMessageCountRef = useRef(0);
  useEffect(() => {
    const isNewMessage = messages.length > prevMessageCountRef.current;
    prevMessageCountRef.current = messages.length;
    bottomRef.current?.scrollIntoView({
      behavior: isNewMessage ? "smooth" : "instant",
    });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    sendMessage(input.trim());
    setInput("");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 min-h-0">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 gap-6">
            <div className="text-indigo-400"><Bot size={40} /></div>
            <p className="text-if-text-lo text-sm text-center max-w-xs">
              Pose-moi une question sur Pokémon Infinite Fusion, les stratégies de fusion, les équipes…
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-xs px-3 py-1.5 rounded-full bg-if-elevated border border-if-border-mid text-[rgb(160,160,200)] hover:border-indigo-500 hover:text-indigo-300 transition-all"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            message={msg}
            rating={ratings[i]}
            onRate={msg.role === "assistant" && !isStreaming ? (r) => handleRate(i, r) : undefined}
          />
        ))}

        {isStreaming && messages[messages.length - 1]?.content === "" &&
          (messages[messages.length - 1]?.toolCalls ?? []).length === 0 && (
          <div className="flex gap-1 items-center pl-10">
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        )}

        {error && (
          <p className="text-red-400 text-sm text-center py-2">{error}</p>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-if-border-lo pt-4 mt-4">
        <div className="flex items-center justify-between mb-2 min-h-[20px]">
          {messages.length > 0 ? (
            <button
              onClick={reset}
              className="text-xs text-if-muted hover:text-if-text-lo transition-colors"
            >
              Effacer la conversation
            </button>
          ) : <span />}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowPrompt(true)}
              title="Voir le prompt envoyé au LLM"
              className="p-1 rounded text-[rgb(80,80,110)] hover:text-indigo-400 transition-colors"
            >
              <Eye size={14} />
            </button>
            {provider && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-if-deep border border-if-border text-if-muted">
                {provider.name} · {provider.model}
              </span>
            )}
          </div>
        </div>
        {showPrompt && <PromptModal onClose={() => setShowPrompt(false)} />}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
            placeholder="Pose ta question…"
            className="flex-1 px-4 py-2 rounded-lg bg-if-elevated border border-if-border-mid text-if-text-hi placeholder:text-if-muted focus:outline-none focus:border-indigo-500 disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            {isStreaming ? "…" : "Envoyer"}
          </button>
        </form>
      </div>
    </div>
  );
}

function ToolPill({ name }: { name: string }) {
  const label = AI_TOOL_LABELS[name] ?? name;
  return (
    <span className="if-tool-pill">
      <Cog size={10} className="opacity-70" />
      {label}
    </span>
  );
}

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  db:   <Database size={9} className="opacity-70" />,
  wiki: <BookOpen size={9} className="opacity-70" />,
  web:  <Globe    size={9} className="opacity-70" />,
};

function SourceBadge({ source }: { source: string }) {
  const label  = AI_SOURCE_LABELS[source] ?? source;
  const colors = AI_SOURCE_COLORS[source] ?? "bg-zinc-900/60 border-zinc-700/50 text-zinc-300";
  return (
    <span className={`inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full border ${colors}`}>
      {SOURCE_ICONS[source]}
      {label}
    </span>
  );
}

function MessageBubble({
  message,
  rating,
  onRate,
}: {
  message: ChatMessage;
  rating?: "up" | "down";
  onRate?: (r: "up" | "down") => void;
}) {
  const isUser = message.role === "user";
  const toolCalls = message.toolCalls ?? [];

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-indigo-700 flex items-center justify-center shrink-0 mr-2 mt-0.5">
          <Bot size={14} />
        </div>
      )}
      <div className="flex flex-col gap-1 max-w-[80%]">
        {toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {toolCalls.map((tc, i) => (
              <ToolPill key={i} name={tc} />
            ))}
          </div>
        )}
        {((message.sources ?? []).length > 0 || message.totalTokens != null) && (
          <div className="flex flex-wrap gap-1">
            {(message.sources ?? []).map((src) => (
              <SourceBadge key={src} source={src} />
            ))}
            {message.totalTokens != null && (
              <span className="inline-flex items-center text-[9px] px-1.5 py-0.5 rounded-full bg-zinc-900/40 border border-zinc-700/30 text-zinc-500">
                {message.totalTokens.toLocaleString()} tokens
              </span>
            )}
          </div>
        )}
        <div
          className={`px-4 py-2.5 rounded-xl text-sm leading-relaxed ${
            isUser
              ? "bg-indigo-600/30 text-if-text-hi rounded-br-sm whitespace-pre-wrap"
              : "bg-if-elevated text-if-text-dim rounded-bl-sm prose prose-sm prose-invert max-w-none"
          }`}
        >
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown
              components={{
                p:      ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul:     ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                ol:     ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                li:     ({ children }) => <li>{children}</li>,
                strong: ({ children }) => <strong className="font-semibold text-if-text-hi">{children}</strong>,
                code:   ({ children }) => <code className="bg-if-deep px-1 py-0.5 rounded text-indigo-400 text-xs font-mono">{children}</code>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Feedback buttons — assistant only */}
        {onRate && message.content && (
          <div className="flex gap-1 mt-1">
            <button
              onClick={() => onRate("up")}
              disabled={!!rating}
              title="Bonne réponse"
              className="p-1 rounded transition-colors"
              style={{
                color: rating === "up" ? "#4ade80" : "#3d4170",
                background: rating === "up" ? "rgba(74,222,128,0.1)" : "transparent",
              }}
            >
              <ThumbsUp size={12} />
            </button>
            <button
              onClick={() => onRate("down")}
              disabled={!!rating}
              title="Mauvaise réponse"
              className="p-1 rounded transition-colors"
              style={{
                color: rating === "down" ? "#f87171" : "#3d4170",
                background: rating === "down" ? "rgba(248,113,113,0.1)" : "transparent",
              }}
            >
              <ThumbsDown size={12} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
