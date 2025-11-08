
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils'; // optional utility for class merging
import { MetricCard } from './MetricCard';
import { UploadZone } from './UploadZone';
import { GraphExplorer } from './GraphExplorer';
import { MockTrialArena } from './MockTrialArena';

export default function DashboardHub() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="min-h-screen bg-gradient-to-br from-[#0a0a0f] to-[#111] text-white p-6 space-y-8"
    >
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-semibold tracking-tight">Welcome, David</h1>
        <div className="flex space-x-4">
          <button className="icon-btn">🔔</button>
          <button className="icon-btn">👤</button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-4 gap-6">
        <MetricCard title="Relevant Matter Score" value="84" subtitle="8 Uncovered Facts" glow="cyan" />
        <MetricCard title="Task Burndown" chart glow="pink" />
        <MetricCard title="Case Status Timeline" timeline glow="violet" />
        <MetricCard title="Reports Reviewed" value="175" subtitle="Last 7 Days" glow="blue" />
      </div>

      {/* Upload + Graph + Trial */}
      <div className="grid grid-cols-3 gap-6">
        <UploadZone />
        <GraphExplorer />
        <MockTrialArena />
      </div>
    </motion.div>
  );
}
