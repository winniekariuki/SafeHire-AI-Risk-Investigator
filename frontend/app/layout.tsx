import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Geist, Geist_Mono } from "next/font/google";
import { AnimatedBackdrop } from "@/components/AnimatedBackdrop";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SafeHire · AI Risk Investigator",
  description: "Worker risk investigations with evidence-backed assessments.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      {/* suppressHydrationWarning: browser extensions (e.g. Grammarly) mutate <body> attributes */}
      <body
        className="relative flex min-h-full flex-col bg-zinc-50 dark:bg-zinc-950"
        suppressHydrationWarning
      >
        <AnimatedBackdrop />
        <ClerkProvider>
          <div className="relative z-0 flex min-h-full flex-1 flex-col">{children}</div>
        </ClerkProvider>
      </body>
    </html>
  );
}
