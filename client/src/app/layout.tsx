import type { Metadata } from "next";
import { Hanken_Grotesk, Red_Hat_Mono } from "next/font/google";
import "./globals.css";

const hanken = Hanken_Grotesk({
  subsets: ["latin"],
  variable: "--font-hanken",
});

const redHatMono = Red_Hat_Mono({
  subsets: ["latin"],
  weight: ["500", "700"],
  variable: "--font-redhat-mono",
});

export const metadata: Metadata = {
  title: "PK-Hub — Pakistan Procurement Intelligence",
  description: "Automated public bid discovery across Pakistani government portals",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${hanken.variable} ${redHatMono.variable}`}>
      <body className="min-h-screen bg-stamp font-sans text-ink-900 antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
