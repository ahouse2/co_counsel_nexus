import React from 'react';
import { motion } from 'framer-motion';
import { UploadZone } from '@/components/UploadZone';

export function EvidenceUploadZone() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
      className="panel-shell"
    >
      <header>
        <h2>Evidence Upload & File Intelligence</h2>
        <p className="panel-subtitle">Drag and drop files for AI analysis and auto-tagging.</p>
      </header>
      <UploadZone />
    </motion.div>
  );
}
