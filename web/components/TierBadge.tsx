"use client";

import { motion } from "motion/react";
import { getTierName, scorePct, tierBadgeClass, tierBadgeLabel } from "@/lib/format";

export default function TierBadge({ probability }: { probability: number }) {
  const tier = getTierName(probability);
  return (
    <motion.span
      key={tier}
      className={`${tierBadgeClass(tier)} badge-pulse`}
      initial={{ scale: 0.6, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 18 }}
    >
      {tierBadgeLabel(tier)} ({scorePct(probability)}%)
    </motion.span>
  );
}
