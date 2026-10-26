"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function AnalyzeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" strokeLinecap="round" />
    </svg>
  );
}

function ExplainabilityIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18h6M10 22h4" strokeLinecap="round" />
      <path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.3h6c0-1 .4-1.8 1-2.3A7 7 0 0 0 12 2z" strokeLinejoin="round" />
    </svg>
  );
}

function ModelCardIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <circle cx="8.5" cy="10.5" r="1.5" />
      <path d="M5 16c.6-1.6 2-2.5 3.5-2.5S11.4 14.4 12 16" strokeLinecap="round" />
      <path d="M14 9h5M14 12.5h5" strokeLinecap="round" />
    </svg>
  );
}

const NAV_ITEMS = [
  { href: "/analyze", label: "Analyze", icon: AnalyzeIcon },
  { href: "/explainability", label: "Explainability", icon: ExplainabilityIcon },
  { href: "/model-card", label: "Model Card", icon: ModelCardIcon },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-logo" aria-hidden="true" />
        Citelytics
      </div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-nav-link${active ? " active" : ""}`}
            >
              <Icon />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export function currentPageLabel(pathname: string): string {
  const item = NAV_ITEMS.find((i) => i.href === pathname);
  return item ? item.label : "Analyze";
}
