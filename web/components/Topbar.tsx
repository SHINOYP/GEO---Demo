"use client";

import { usePathname } from "next/navigation";
import { currentPageLabel } from "./Sidebar";

export default function Topbar() {
  const pathname = usePathname();
  return (
    <div className="topbar">
      <span className="brand-text">Citelytics</span>
      <span className="crumb">&nbsp;/ {currentPageLabel(pathname)}</span>
    </div>
  );
}
