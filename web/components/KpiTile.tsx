"use client";

import { useEffect, useState } from "react";

function useCountUp(countTo: number | undefined, duration = 1100) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (countTo === undefined) return;
    const target = countTo;
    const start = performance.now();
    let raf: number;
    function tick(now: number) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 4);
      setDisplay(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [countTo, duration]);

  return display;
}

export default function KpiTile({
  label,
  value,
  sub,
  countTo,
  formatCount,
}: {
  label: string;
  value: string;
  sub?: string;
  /** If set, animates the tile's value from 0 up to this number on mount. */
  countTo?: number;
  /** Formats each in-between frame of the count-up; required when countTo is set. */
  formatCount?: (n: number) => string;
}) {
  const animated = useCountUp(countTo);
  const display = countTo !== undefined && formatCount ? formatCount(animated) : value;

  return (
    <div className="card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{display}</div>
      {sub ? <div className="kpi-sub">{sub}</div> : null}
    </div>
  );
}
