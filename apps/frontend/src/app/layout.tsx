import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import PasswordLock from "@/components/PasswordLock";
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
  title: "CreatorArc - Creator Workspace Hub",
  description: "An AI-powered local workstation hub for content creators, featuring Text, YouTube, and Media suites.",
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
    >
      <body className="min-h-full flex flex-col bg-[#05060b]">
        <PasswordLock>{children}</PasswordLock>
      </body>
    </html>
  );
}
