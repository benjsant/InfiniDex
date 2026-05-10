"use client";

import { Component, type ReactNode } from "react";

// ── Section-level boundary — inline fallback, no full-page takeover ───────────

interface SectionProps {
  children: ReactNode;
  label?: string;
}

interface SectionState {
  error: Error | null;
}

export class SectionErrorBoundary extends Component<SectionProps, SectionState> {
  state: SectionState = { error: null };

  static getDerivedStateFromError(error: Error): SectionState {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div
          className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "rgba(239,68,68,0.08)", border: "1px solid #ef444433", color: "#f87171" }}
        >
          {this.props.label ? `${this.props.label} — ` : ""}
          Erreur de chargement.{" "}
          <button
            onClick={() => this.setState({ error: null })}
            className="underline hover:no-underline transition-all"
          >
            Réessayer
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Full-page boundary ────────────────────────────────────────────────────────

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center px-4">
          <div
            className="max-w-md w-full rounded-2xl p-6 text-center"
            style={{ background: "#111428", border: "1px solid #1e2240" }}
          >
            <div className="text-4xl mb-4">⚠</div>
            <h2 className="text-lg font-bold mb-2" style={{ color: "#e1e4ff" }}>
              Une erreur inattendue s&apos;est produite
            </h2>
            <p className="text-sm mb-4" style={{ color: "#6b7199" }}>
              {this.state.error.message}
            </p>
            <button
              onClick={() => this.setState({ error: null })}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{ background: "rgba(232,184,75,0.12)", color: "#e8b84b", border: "1px solid rgba(232,184,75,0.3)" }}
            >
              Réessayer
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
