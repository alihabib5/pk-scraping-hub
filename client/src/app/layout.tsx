import type { Metadata } from "next";
import { Newsreader, Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-serif",
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Scraping Hub — Pakistan Procurement Intelligence",
  description: "Automated public bid discovery across Pakistani government portals",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${newsreader.variable}`}>
      <body
        className="bg-[#faf8f5] text-zinc-900 antialiased min-h-screen font-sans"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
