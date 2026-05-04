import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Navbar } from "@/components/layout/Navbar";
import { ErrorBoundary } from "@/components/layout/ErrorBoundary";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FusionDex — Pokédex Intelligent pour Infinite Fusion",
  description:
    "Explorez les 501 Pokémon de Pokémon Infinite Fusion, calculez les fusions, découvrez les faiblesses et posez vos questions à l'IA DeepSeek.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className={outfit.variable} suppressHydrationWarning>
      {/* Inline script avoids flash of wrong theme on hydration */}
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('theme');document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark');})();`,
          }}
        />
      </head>
      <body className="min-h-screen bg-if-bg text-if-text font-sans antialiased">
        <Providers>
          <ErrorBoundary>
            <Navbar />
            <main className="pt-16">{children}</main>
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
