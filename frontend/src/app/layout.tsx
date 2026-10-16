import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"], display: "swap" });
const mono = JetBrains_Mono({ variable: "--font-mono", subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: {
    default: "StratumAI",
    template: "%s · StratumAI",
  },
  description:
    "StratumAI is an agentic RAG assistant for engineering teams, grounded answers about Kubernetes, infrastructure and systems with cited sources.",
  applicationName: "StratumAI",
  keywords: ["RAG", "Kubernetes", "AI assistant", "LangGraph", "forward deployed engineering"],
  openGraph: {
    title: "StratumAI",
    description: "Grounded engineering answers with cited sources, streamed in real time.",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  interactiveWidget: "resizes-content",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#212121" },
  ],
};

const themeScript = `(function(){try{var t=localStorage.getItem('stratumai.theme')||'system';var d=t==='dark'||(t==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);var r=document.documentElement;r.classList.toggle('dark',d);r.style.colorScheme=d?'dark':'light'}catch(e){}})()`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable} h-full`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="h-full overflow-hidden font-sans">{children}</body>
    </html>
  );
}
