"use client";

import { useEffect, useState } from "react";

/**
 * Tracks the `data-theme` attribute on <html>, which ThemeToggle writes to
 * and the inline script in layout.tsx sets before first paint. Returns null
 * until mounted (matches SSR, where the real value doesn't exist) so
 * consumers can render a stable placeholder and avoid a hydration mismatch.
 */
export function useTheme(): "light" | "dark" | null {
  const [theme, setTheme] = useState<"light" | "dark" | null>(null);

  useEffect(() => {
    const read = () => {
      const attr = document.documentElement.getAttribute("data-theme");
      setTheme(attr === "dark" ? "dark" : "light");
    };
    read();
    const observer = new MutationObserver(read);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  return theme;
}
