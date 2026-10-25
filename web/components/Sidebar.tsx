"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/analyze", label: "Analyze" },
  { href: "/explainability", label: "Explainability" },
  { href: "/model-card", label: "Model Card" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">Citelytics</div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar-nav-link${pathname === item.href ? " active" : ""}`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="sidebar-footer">Stephin Arnold · CSD 415</div>
    </aside>
  );
}

export function currentPageLabel(pathname: string): string {
  const item = NAV_ITEMS.find((i) => i.href === pathname);
  return item ? item.label : "Analyze";
}
