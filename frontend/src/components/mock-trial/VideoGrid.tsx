import * as React from "react"
import { motion } from "framer-motion"
import { Mic, MicOff, Video, VideoOff, Crown, User } from "lucide-react"
import { cn } from "@/lib/utils"

interface Participant {
  id: string
  name: string
  role: string
  isMuted: boolean
  isVideoOff: boolean
  isSpeaking: boolean
  isHost: boolean
}

interface VideoGridProps {
  participants: Participant[]
  onToggleMute?: (id: string) => void
  onToggleVideo?: (id: string) => void
  className?: string
}

const VideoGrid: React.FC<VideoGridProps> = ({ 
  participants, 
  onToggleMute,
  onToggleVideo,
  className 
}) => {
  return (
    <div className={cn("grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4", className)}>
      {participants.map((participant, index) => (
        <motion.div
          key={participant.id}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: index * 0.1 }}
          whileHover={{ y: -5 }}
          className={cn(
            "relative rounded-xl overflow-hidden border-2 bg-background-panel transition-all duration-300",
            participant.isSpeaking 
              ? "border-accent-cyan-500 shadow-cyan-md" 
              : "border-border-subtle",
            participants.length === 1 && "sm:col-span-2 sm:row-span-2"
          )}
        >
          {/* Enhanced video placeholder with holo effect */}
          <div className="aspect-video bg-gradient-to-br from-background-surface to-background-panel flex items-center justify-center relative overflow-hidden rounded-t-xl">
            {/* Atmospheric background effects */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(24,202,254,0.05)_0%,transparent_70%)]" />
            
            <div className="text-center relative z-10">
              <div className="w-16 h-16 rounded-full bg-accent-violet-500/20 flex items-center justify-center mx-auto mb-3 relative overflow-hidden">
                <User className="w-8 h-8 text-accent-violet-300 relative z-10" />
                {/* Glow effect */}
                <div className="absolute inset-0 bg-accent-violet-500/10 rounded-full" />
              </div>
              <p className="text-text-primary font-medium">{participant.name}</p>
              <p className="text-text-secondary text-sm mt-1">{participant.role}</p>
            </div>
            
            {/* Neon edge lighting */}
            <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-accent-cyan-500 to-transparent opacity-50" />
          </div>
          
          {/* Participant overlay with enhanced gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-background-panel/90 via-background-panel/50 to-transparent pointer-events-none" />
          
          {/* Status indicators with glow effects */}
          <div className="absolute top-3 left-3 flex gap-2">
            {participant.isHost && (
              <div className="flex items-center gap-1 bg-accent-gold/20 text-accent-gold px-2 py-1 rounded-full text-xs relative overflow-hidden">
                <Crown className="w-3 h-3 relative z-10" />
                <span className="relative z-10">Host</span>
                {/* Glow effect */}
                <div className="absolute inset-0 bg-accent-gold/10 rounded-full" />
              </div>
            )}
            {participant.isMuted && (
              <div className="flex items-center gap-1 bg-accent-red/20 text-accent-red px-2 py-1 rounded-full text-xs relative overflow-hidden">
                <MicOff className="w-3 h-3 relative z-10" />
                <span className="relative z-10">Muted</span>
                {/* Glow effect */}
                <div className="absolute inset-0 bg-accent-red/10 rounded-full" />
              </div>
            )}
          </div>
          
          {/* Enhanced controls with glow effects */}
          <div className="absolute bottom-3 right-3 flex gap-2">
            <motion.button
              className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center backdrop-blur-sm relative overflow-hidden group/mic",
                participant.isMuted 
                  ? "bg-accent-red/80 text-white" 
                  : "bg-background-overlay/80 text-text-primary"
              )}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => onToggleMute && onToggleMute(participant.id)}
            >
              {participant.isMuted ? (
                <MicOff className="w-4 h-4 relative z-10" />
              ) : (
                <Mic className="w-4 h-4 relative z-10" />
              )}
              {/* Button glow effect */}
              <div className="absolute inset-0 bg-current/20 rounded-full blur-sm opacity-0 group-hover/mic:opacity-100 transition-opacity duration-300" />
            </motion.button>
            
            <motion.button
              className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center backdrop-blur-sm relative overflow-hidden group/video",
                participant.isVideoOff 
                  ? "bg-accent-red/80 text-white" 
                  : "bg-background-overlay/80 text-text-primary"
              )}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => onToggleVideo && onToggleVideo(participant.id)}
            >
              {participant.isVideoOff ? (
                <VideoOff className="w-4 h-4 relative z-10" />
              ) : (
                <Video className="w-4 h-4 relative z-10" />
              )}
              {/* Button glow effect */}
              <div className="absolute inset-0 bg-current/20 rounded-full blur-sm opacity-0 group-hover/video:opacity-100 transition-opacity duration-300" />
            </motion.button>
          </div>
          
          {/* Enhanced speaking indicator with cinematic effects */}
          {participant.isSpeaking && (
            <motion.div
              className="absolute inset-0 border-2 border-accent-cyan-500 rounded-xl pointer-events-none"
              animate={{ 
                boxShadow: [
                  "0 0 0 0 rgba(24, 202, 254, 0.4)",
                  "0 0 0 8px rgba(24, 202, 254, 0)",
                  "0 0 0 0 rgba(24, 202, 254, 0.4)"
                ]
              }}
              transition={{ 
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          )}
          
          {/* Additional glow effect when speaking */}
          {participant.isSpeaking && (
            <div className="absolute inset-0 rounded-xl pointer-events-none border border-accent-cyan-500/50">
              <div className="absolute inset-0 bg-accent-cyan-500/5 rounded-xl blur-sm" />
            </div>
          )}
        </motion.div>
      ))}
    </div>
  )
}

export { VideoGrid }