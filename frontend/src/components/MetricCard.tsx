import { motion } from 'framer-motion';
import { cn } from '@/lib/utils'; // optional utility for class merging

type Props = {
  title: string;
  value?: string;
  subtitle?: string;
  chart?: boolean;
  timeline?: boolean;
  glow?: 'cyan' | 'pink' | 'violet' | 'blue';
};

export function MetricCard({ title, value, subtitle, chart, timeline, glow }: Props) {
  const glowMap = {
    cyan: 'shadow-[0_0_20px_#00ffff88]',
    pink: 'shadow-[0_0_20px_#ff00ff88]',
    violet: 'shadow-[0_0_20px_#a855f788]',
    blue: 'shadow-[0_0_20px_#3b82f688]',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
      className={cn(
        'bg-[#1a1a1f] rounded-xl p-4 backdrop-blur-md border border-[#2a2a2f]',
        glowMap[glow || 'blue']
      )}
    >
      <h2 className="text-lg font-medium">{title}</h2>
      {value && <div className="text-4xl font-bold mt-2">{value}</div>}
      {subtitle && <p className="text-sm text-gray-400">{subtitle}</p>}
      {chart && <div className="mt-4 h-24 bg-gradient-to-r from-pink-500 to-purple-500 rounded" />}
      {timeline && (
        <div className="mt-4 h-2 bg-gradient-to-r from-blue-500 via-violet-500 to-red-500 rounded-full" />
      )}
    </motion.div>
  );
}
