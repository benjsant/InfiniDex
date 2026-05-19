"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { normalize } from "@/lib/utils";

interface SearchBarProps {
  placeholder?: string;
  onSearch?: (q: string) => void;
  navigateTo?: boolean; // if true, navigate to /pokedex?q=
  className?: string;
}

export function SearchBar({
  placeholder = "Rechercher un Pokémon (EN, FR, accents ok)…",
  onSearch,
  navigateTo = false,
  className,
}: SearchBarProps) {
  const [value, setValue] = useState("");
  const router = useRouter();

  const handleSearch = useCallback(
    (q: string) => {
      if (onSearch) {
        onSearch(normalize(q));
      }
      if (navigateTo && q.trim().length > 0) {
        router.push(`/pokedex?q=${encodeURIComponent(q.trim())}`);
      }
    },
    [onSearch, navigateTo, router],
  );

  // Debounce 300ms
  useEffect(() => {
    const timer = setTimeout(() => handleSearch(value), 300);
    return () => clearTimeout(timer);
  }, [value, handleSearch]);

  return (
    <input
      type="search"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      placeholder={placeholder}
      className={`w-full px-4 py-2 rounded-lg bg-if-input border border-if-border-mid text-if-text-hi placeholder:text-if-muted focus:outline-none focus:border-indigo-500 transition-colors ${className ?? ""}`}
    />
  );
}
