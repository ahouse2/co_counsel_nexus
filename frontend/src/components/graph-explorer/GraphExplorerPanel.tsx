import React from 'react';
import { motion } from 'framer-motion';
import { GraphExplorer } from '@/components/GraphExplorer';

export function GraphExplorerPanel() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
      className="panel-shell"
    >
      <header>
        <h2>Graph Explorer</h2>
        <p className="panel-subtitle">Visualize and interact with your legal data.</p>
      </header>
      <GraphExplorer />
    </motion.div>
  );
}
