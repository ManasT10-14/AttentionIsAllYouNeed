'use client';

import { motion } from 'motion/react';

export default function DashboardTemplate({ children }: { children: React.ReactNode }) {
  return <motion.div initial={{ opacity: 0, y: 12, filter: 'blur(3px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} transition={{ duration: .38, ease: [.22, 1, .36, 1] }}>{children}</motion.div>;
}
