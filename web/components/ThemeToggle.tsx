"use client";

import { motion } from "motion/react";
import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/lib/useTheme";

const STORAGE_KEY = "citelytics-theme";

export default function ThemeToggle() {
  const theme = useTheme();

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Private browsing / blocked storage -- the toggle still works for
      // this page view, it just won't be remembered next visit.
    }
  }

  if (theme === null) {
    return <span className="theme-toggle-button" style={{ visibility: "hidden" }} aria-hidden="true" />;
  }

  return (
    <motion.button
      type="button"
      className="theme-toggle-button"
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      whileTap={{ scale: 0.88 }}
    >
      {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
    </motion.button>
  );
}
