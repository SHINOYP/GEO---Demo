"use client";

import { usePathname } from "next/navigation";
import { motion } from "motion/react";
import { currentPageLabel } from "./Sidebar";

export default function Topbar({ onMenuClick }: { onMenuClick?: () => void }) {
  const pathname = usePathname();
  return (
    <div className="topbar">
      <button
        type="button"
        className="mobile-menu-button"
        aria-label="Toggle navigation menu"
        onClick={onMenuClick}
      >
        <motion.span whileTap={{ scale: 0.85 }} style={{ display: "flex" }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
          </svg>
        </motion.span>
      </button>
      <span className="brand-text">Citelytics</span>
      <span className="crumb">&nbsp;/ {currentPageLabel(pathname)}</span>
    </div>
  );
}
