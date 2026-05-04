"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, GitMerge, Zap, Shield, Star, Bot, Layers, GraduationCap, Users, Menu, X, Sun, Moon } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/lib/theme";

const NAV_LINKS: { href: string; label: string; Icon: LucideIcon }[] = [
  { href: "/pokedex",        label: "Pokédex",        Icon: BookOpen      },
  { href: "/fusion",         label: "Fusion",         Icon: GitMerge      },
  { href: "/moves/tutors",   label: "Tuteurs",        Icon: GraduationCap },
  { href: "/moves",          label: "Capacités",      Icon: Zap           },
  { href: "/types",          label: "Types",          Icon: Shield        },
  { href: "/abilities",      label: "Talents",        Icon: Star          },
  { href: "/triple-fusions", label: "Triple Fusions", Icon: Layers        },
  { href: "/creators",       label: "Créateurs",      Icon: Users         },
  { href: "/ai",             label: "IA",             Icon: Bot           },
];

function isActive(pathname: string | null, href: string) {
  return pathname === href || (href !== "/" && !!pathname?.startsWith(href + "/"));
}

export function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { theme, toggle } = useTheme();

  return (
    <>
      <nav
        className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center px-4 gap-4 if-navbar-bg border-b border-if-border"
        style={{ boxShadow: "0 2px 16px rgba(0,0,0,0.3)" }}
      >
        {/* Logo */}
        <Link
          href="/"
          className="text-lg font-bold whitespace-nowrap mr-2 text-if-accent hover:text-if-accent-hi transition-colors"
        >
          FusionDex
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-0.5 overflow-x-auto flex-1">
          {NAV_LINKS.map(({ href, label, Icon }) => {
            const active = isActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
                  active
                    ? "text-if-accent bg-[rgba(232,184,75,0.12)]"
                    : "text-if-muted hover:text-if-text hover:bg-if-elevated",
                )}
              >
                <Icon size={14} />
                {label}
              </Link>
            );
          })}
        </div>

        {/* Theme toggle */}
        <button
          onClick={toggle}
          aria-label={theme === "dark" ? "Passer en mode clair" : "Passer en mode sombre"}
          className="p-2 rounded-lg text-if-muted hover:text-if-text hover:bg-if-elevated transition-colors shrink-0"
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-lg text-if-muted hover:text-if-text transition-colors"
          onClick={() => setOpen((v) => !v)}
          aria-label="Menu"
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </nav>

      {/* Mobile drawer */}
      {open && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          onClick={() => setOpen(false)}
        >
          <div
            className="absolute top-16 left-0 right-0 py-2 px-3 if-drawer-bg border-b border-if-border"
            style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}
            onClick={(e) => e.stopPropagation()}
          >
            {NAV_LINKS.map(({ href, label, Icon }) => {
              const active = isActive(pathname, href);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-all",
                    active
                      ? "text-if-accent bg-[rgba(232,184,75,0.10)]"
                      : "text-if-muted hover:text-if-text hover:bg-if-elevated",
                  )}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
