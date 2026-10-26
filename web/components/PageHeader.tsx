"use client";

import { motion } from "motion/react";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" as const } },
};

export default function PageHeader({
  badge,
  title,
  subtitle,
}: {
  badge: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.span className="page-badge" variants={item}>
        {badge}
      </motion.span>
      <motion.h1 className="page-title" variants={item}>
        {title}
      </motion.h1>
      {subtitle ? (
        <motion.p className="page-sub" variants={item}>
          {subtitle}
        </motion.p>
      ) : null}
    </motion.div>
  );
}
