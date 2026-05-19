"use client";

import { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import { Check, AlertCircle, X } from "lucide-react";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

let nextId = 1;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, type: ToastType = "success") => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        aria-live="polite"
        className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
      >
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast: t, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.opacity = "0";
    el.style.transform = "translateY(8px)";
    requestAnimationFrame(() => {
      el.style.transition = "opacity 0.2s, transform 0.2s";
      el.style.opacity = "1";
      el.style.transform = "translateY(0)";
    });
  }, []);

  const colors = {
    success: { bg: "rgba(74,222,128,0.12)", border: "#4ade8044", icon: "#4ade80" },
    error:   { bg: "rgba(239,68,68,0.12)",  border: "#ef444444", icon: "#f87171" },
    info:    { bg: "rgba(99,102,241,0.12)", border: "#6366f144", icon: "#818cf8" },
  }[t.type];

  const Icon = t.type === "success" ? Check : t.type === "error" ? AlertCircle : AlertCircle;

  return (
    <div
      ref={ref}
      className="pointer-events-auto flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-sm font-medium shadow-xl"
      style={{
        background: colors.bg,
        border: `1px solid ${colors.border}`,
        color: "var(--color-if-text)",
        backdropFilter: "blur(8px)",
        minWidth: 200,
        maxWidth: 320,
      }}
    >
      <Icon size={14} style={{ color: colors.icon, flexShrink: 0 }} />
      <span className="flex-1">{t.message}</span>
      <button
        onClick={() => onDismiss(t.id)}
        className="shrink-0 opacity-50 hover:opacity-100 transition-opacity"
        aria-label="Fermer"
      >
        <X size={12} />
      </button>
    </div>
  );
}

export function useToast(): ToastContextValue {
  return useContext(ToastContext);
}
