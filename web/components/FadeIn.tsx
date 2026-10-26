"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

/**
 * Lightweight entrance animation wrapper usable from Server Components
 * (this file is the only "use client" boundary — children can still be
 * server-rendered content passed down as props).
 */
export default function FadeIn({
  children,
  delay = 0,
}: {
  children: ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
