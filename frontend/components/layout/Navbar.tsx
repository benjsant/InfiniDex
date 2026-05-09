"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, GitMerge, Zap, Shield, Star, Bot, Layers, GraduationCap, Palette, Menu, X, Package } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { GlobalSearch } from "@/components/layout/GlobalSearch";

const NAV_LINKS: { href: string; label: string; Icon: LucideIcon }[] = [
  { href: "/pokedex",        label: "Pokédex",        Icon: BookOpen      },
  { href: "/fusion",         label: "Fusion",         Icon: GitMerge      },
  { href: "/moves/tutors",   label: "Tuteurs",        Icon: GraduationCap },
  { href: "/moves",          label: "Capacités",      Icon: Zap           },
  { href: "/types",          label: "Types",          Icon: Shield        },
  { href: "/abilities",      label: "Talents",        Icon: Star          },
  { href: "/items",          label: "Objets",         Icon: Package       },
  { href: "/triple-fusions", label: "Triple Fusions", Icon: Layers        },
  { href: "/creators",       label: "Créateurs",      Icon: Palette       },
  { href: "/ai",             label: "IA",             Icon: Bot           },
];

function isActive(pathname: string | null, href: string) {
  return pathname === href || (href !== "/" && !!pathname?.startsWith(href + "/"));
}

export function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <>
      <nav
        className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center px-4 gap-4"
        style={{
          background: "rgba(9,12,26,0.96)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid #1e2240",
          boxShadow: "0 2px 16px rgba(0,0,0,0.5)",
        }}
      >
        {/* Logo */}
        <Link
          href="/"
          className="text-lg font-bold whitespace-nowrap mr-2 transition-colors"
          style={{ color: "#e8b84b" }}
          onMouseEnter={(e) => ((e.target as HTMLElement).style.color = "#f5d07a")}
          onMouseLeave={(e) => ((e.target as HTMLElement).style.color = "#e8b84b")}
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
                    ? "text-[#e8b84b]"
                    : "text-[#6b7199] hover:text-[#e1e4ff] hover:bg-[#1e2240]",
                )}
                style={active ? { background: "rgba(232,184,75,0.12)" } : undefined}
              >
                <Icon size={14} />
                {label}
              </Link>
            );
          })}
        </div>

        {/* Global search */}
        <div className="ml-auto">
          <GlobalSearch />
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-lg transition-colors"
          style={{ color: "#6b7199" }}
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
            className="absolute top-16 left-0 right-0 py-2 px-3"
            style={{
              background: "rgba(9,12,26,0.98)",
              borderBottom: "1px solid #1e2240",
              boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {NAV_LINKS.map(({ href, label, Icon }) => {
              const active = isActive(pathname, href);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-all"
                  style={{
                    color: active ? "#e8b84b" : "#6b7199",
                    background: active ? "rgba(232,184,75,0.10)" : undefined,
                  }}
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
