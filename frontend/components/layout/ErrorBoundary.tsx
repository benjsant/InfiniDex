"use client";

import { Component, type ReactNode } from "react";

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
          <div className="max-w-md w-full rounded-2xl p-6 text-center if-panel">
            <div className="text-4xl mb-4">⚠</div>
            <h2 className="text-lg font-bold mb-2 text-if-text">
              Une erreur inattendue s&apos;est produite
            </h2>
            <p className="text-sm mb-4 text-if-muted">
              {this.state.error.message}
            </p>
            <button
              onClick={() => this.setState({ error: null })}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors text-if-accent"
              style={{ background: "rgba(232,184,75,0.12)", border: "1px solid rgba(232,184,75,0.3)" }}
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
