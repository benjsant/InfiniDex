"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen, GitMerge, Zap, Shield, Star, Bot, Layers,
  GraduationCap, Palette, Menu, X, Package, Shuffle,
  GitCompare, History, ChevronDown, Database, Sun, Moon, Info,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { GlobalSearch } from "@/components/layout/GlobalSearch";
import { useTheme } from "@/hooks/useTheme";

type SubLink = { href: string; label: string; Icon: LucideIcon };
type NavEntry =
  | { kind: "link"; href: string; label: string; Icon: LucideIcon }
  | { kind: "dropdown"; label: string; Icon: LucideIcon; baseHref: string; sub: SubLink[] };

const NAV: NavEntry[] = [
  { kind: "link", href: "/pokedex", label: "Pokédex", Icon: BookOpen },
  {
    kind: "dropdown",
    label: "Fusion",
    Icon: GitMerge,
    baseHref: "/fusion",
    sub: [
      { href: "/fusion",         label: "Calculateur",    Icon: GitMerge   },
      { href: "/fusion/compare", label: "Comparateur",    Icon: GitCompare },
      { href: "/fusion/history", label: "Historique",     Icon: History    },
      { href: "/fusion/random",  label: "Aléatoire",      Icon: Shuffle    },
      { href: "/triple-fusions", label: "Triple Fusions", Icon: Layers     },
    ],
  },
  {
    kind: "dropdown",
    label: "Contenu",
    Icon: Database,
    baseHref: "",
    sub: [
      { href: "/moves",        label: "Capacités", Icon: Zap           },
      { href: "/moves/tutors", label: "Tuteurs",   Icon: GraduationCap },
      { href: "/abilities",    label: "Talents",   Icon: Star          },
      { href: "/items",        label: "Objets",    Icon: Package       },
      { href: "/types",        label: "Types",     Icon: Shield        },
    ],
  },
  { kind: "link", href: "/creators", label: "Créateurs", Icon: Palette },
  { kind: "link", href: "/ai",       label: "IA",        Icon: Bot     },
  { kind: "link", href: "/about",    label: "À propos",  Icon: Info    },
];

function isActive(pathname: string | null, href: string) {
  return pathname === href || (href !== "/" && !!pathname?.startsWith(href + "/"));
}

function DesktopDropdown({
  entry,
  pathname,
}: {
  entry: Extract<NavEntry, { kind: "dropdown" }>;
  pathname: string | null;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const active = entry.baseHref
    ? isActive(pathname, entry.baseHref)
    : entry.sub.some((s) => isActive(pathname, s.href));

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap select-none",
          active
            ? "text-if-accent"
            : "text-if-muted hover:text-if-text hover:bg-if-elevated",
        )}
        style={active ? { background: "rgba(232,184,75,0.12)" } : undefined}
      >
        <entry.Icon size={14} />
        {entry.label}
        <ChevronDown
          size={11}
          className={cn("transition-transform duration-150", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 py-1.5 rounded-xl shadow-2xl min-w-[180px] z-50 bg-if-deep border border-if-border-hi">
          {entry.sub.map(({ href, label, Icon }) => {
            const subActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-2.5 px-4 py-2 text-sm transition-colors",
                  subActive
                    ? "text-if-accent bg-[rgba(232,184,75,0.08)]"
                    : "text-if-muted hover:text-if-text hover:bg-if-elevated",
                )}
              >
                <Icon size={13} />
                {label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      aria-label={theme === "dark" ? "Passer en mode clair" : "Passer en mode sombre"}
      title={theme === "dark" ? "Mode clair" : "Mode sombre"}
      className="flex items-center justify-center w-8 h-8 rounded-lg transition-all text-if-muted hover:text-if-accent border border-if-border hover:border-if-border-hi bg-if-card"
    >
      {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
    </button>
  );
}

export function Navbar() {
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center px-4 gap-4 if-navbar-bg border-b border-if-border shadow-[0_2px_16px_rgba(0,0,0,0.4)]">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 text-lg font-bold whitespace-nowrap mr-2 text-if-accent hover:text-if-accent-hi transition-colors"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/icon.svg" alt="" width={28} height={28} className="shrink-0" />
          InfiniDex
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-0.5 flex-1">
          {NAV.map((entry) => {
            if (entry.kind === "dropdown") {
              return <DesktopDropdown key={entry.label} entry={entry} pathname={pathname} />;
            }
            const active = isActive(pathname, entry.href);
            return (
              <Link
                key={entry.href}
                href={entry.href}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
                  active
                    ? "text-if-accent"
                    : "text-if-muted hover:text-if-text hover:bg-if-elevated",
                )}
                style={active ? { background: "rgba(232,184,75,0.12)" } : undefined}
              >
                <entry.Icon size={14} />
                {entry.label}
              </Link>
            );
          })}
        </div>

        {/* Random fusion shortcut */}
        <Link
          href="/fusion/random"
          className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all shrink-0 text-if-muted border border-if-border hover:text-if-accent hover:border-if-border-hi"
          style={{ background: "rgba(30,34,64,0.4)" }}
          aria-label="Fusion aléatoire"
          title="Fusion aléatoire"
        >
          <Shuffle size={13} />
        </Link>

        {/* Theme toggle */}
        <ThemeToggle />

        {/* Global search */}
        <GlobalSearch />

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-lg transition-colors text-if-muted hover:text-if-text"
          onClick={() => setDrawerOpen((v) => !v)}
          aria-label="Menu"
        >
          {drawerOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </nav>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          onClick={() => setDrawerOpen(false)}
        >
          <div
            className="absolute top-16 left-0 right-0 py-2 px-3 if-drawer-bg border-b border-if-border shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
            onClick={(e) => e.stopPropagation()}
          >
            {NAV.map((entry) => {
              if (entry.kind === "dropdown") {
                const active = entry.baseHref
                  ? isActive(pathname, entry.baseHref)
                  : entry.sub.some((s) => isActive(pathname, s.href));
                const isExpanded = expanded === entry.label;
                return (
                  <div key={entry.label}>
                    <button
                      onClick={() => setExpanded(isExpanded ? null : entry.label)}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors",
                        active ? "text-if-accent" : "text-if-muted",
                      )}
                      style={active ? { background: "rgba(232,184,75,0.10)" } : undefined}
                    >
                      <entry.Icon size={16} />
                      {entry.label}
                      <ChevronDown
                        size={13}
                        className={cn("ml-auto transition-transform duration-150", isExpanded && "rotate-180")}
                      />
                    </button>
                    {isExpanded && (
                      <div className="ml-7 border-l border-if-border pl-3 space-y-0.5 mb-1">
                        {entry.sub.map(({ href, label, Icon }) => {
                          const subActive = pathname === href;
                          return (
                            <Link
                              key={href}
                              href={href}
                              onClick={() => setDrawerOpen(false)}
                              className={cn(
                                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
                                subActive ? "text-if-accent" : "text-if-muted hover:text-if-text",
                              )}
                            >
                              <Icon size={14} />
                              {label}
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              }
              const active = isActive(pathname, entry.href);
              return (
                <Link
                  key={entry.href}
                  href={entry.href}
                  onClick={() => setDrawerOpen(false)}
                  className={cn(
                    "flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors",
                    active ? "text-if-accent" : "text-if-muted hover:text-if-text",
                  )}
                  style={active ? { background: "rgba(232,184,75,0.10)" } : undefined}
                >
                  <entry.Icon size={16} />
                  {entry.label}
                </Link>
              );
            })}

            {/* Theme toggle in drawer */}
            <div className="border-t border-if-border mt-2 pt-2">
              <ThemeToggleRow />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ThemeToggleRow() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-if-muted hover:text-if-text transition-colors"
    >
      {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      {theme === "dark" ? "Mode clair" : "Mode sombre"}
    </button>
  );
}
