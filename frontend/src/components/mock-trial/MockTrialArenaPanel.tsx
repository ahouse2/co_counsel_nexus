import React from 'react';
import { motion } from 'framer-motion';
import { MockTrialArena } from '@/components/MockTrialArena';

export function MockTrialArenaPanel() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
      className="panel-shell"
    >
      <header>
        <h2>Mock Trial Arena</h2>
        <p className="panel-subtitle">Simulate and practice trial scenarios with AI.</p>
      </header>
      <MockTrialArena />
    </motion.div>
  );
}
