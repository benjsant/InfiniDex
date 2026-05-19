import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { ErrorBoundary } from "@/components/layout/ErrorBoundary";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://fusiondex.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "InfiniDex — Pokédex Intelligent pour Infinite Fusion",
  description:
    "Explorez les 501 Pokémon de Pokémon Infinite Fusion, calculez les fusions, découvrez les faiblesses et posez vos questions à l'IA DeepSeek.",
  openGraph: {
    siteName: "InfiniDex",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className={`dark ${outfit.variable}`}>
      <body className="min-h-screen bg-if-bg text-if-text font-sans antialiased">
        <Providers>
          <ErrorBoundary>
            <Navbar />
            <main className="pt-16">{children}</main>
            <Footer />
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
