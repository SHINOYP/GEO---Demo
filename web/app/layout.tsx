import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Citelytics — AI Citation Predictor",
  description:
    "Citation Likelihood Prediction in Generative Answer Engines — Explainable ML for Local Business Content",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <div className="app-shell">
          <Sidebar />
          <main className="main-content">
            <Topbar />
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
