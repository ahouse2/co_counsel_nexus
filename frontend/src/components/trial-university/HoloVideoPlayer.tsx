import * as React from "react"
import { motion } from "framer-motion"
import { Play, Pause, Volume2, VolumeX, Maximize, SkipBack, SkipForward } from "lucide-react"
import { cn } from "@/lib/utils"

interface HoloVideoPlayerProps {
  src: string
  title: string
  description: string
  duration: string
  onPlay?: () => void
  onPause?: () => void
  className?: string
}

interface Subtitle {
  time: number
  text: string
  active: boolean
}

const HoloVideoPlayer: React.FC<HoloVideoPlayerProps> = ({ 
  src, 
  title, 
  description, 
  duration,
  onPlay,
  onPause,
  className 
}) => {
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [isMuted, setIsMuted] = React.useState(false)
  const [progress, setProgress] = React.useState(0)
  const [currentTime, setCurrentTime] = React.useState("0:00")
  const [showSubtitles, setShowSubtitles] = React.useState(true)
  const [subtitles, setSubtitles] = React.useState<Subtitle[]>([
    { time: 5, text: "Welcome to Cross-Examination Mastery", active: false },
    { time: 15, text: "Today we'll explore key techniques", active: false },
    { time: 30, text: "First, let's discuss leading questions", active: false },
    { time: 45, text: "These can be powerful tools in your arsenal", active: false },
  ])
  
  const videoRef = React.useRef<HTMLVideoElement>(null)

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
        onPause && onPause()
      } else {
        videoRef.current.play()
        onPlay && onPlay()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  const handleProgress = () => {
    if (videoRef.current) {
      const percentage = (videoRef.current.currentTime / videoRef.current.duration) * 100
      setProgress(percentage)
      
      // Format current time
      const minutes = Math.floor(videoRef.current.currentTime / 60)
      const seconds = Math.floor(videoRef.current.currentTime % 60)
      setCurrentTime(`${minutes}:${seconds < 10 ? '0' : ''}${seconds}`)
      
      // Update subtitles
      if (showSubtitles) {
        const currentTime = videoRef.current.currentTime;
        setSubtitles(prev => prev.map(sub => ({
          ...sub,
          active: currentTime >= sub.time && currentTime < sub.time + 5
        })));
      }
    }
  }

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (videoRef.current) {
      const rect = e.currentTarget.getBoundingClientRect()
      const pos = (e.clientX - rect.left) / rect.width
      videoRef.current.currentTime = pos * videoRef.current.duration
      setProgress(pos * 100)
    }
  }

  return (
    <motion.div 
      className={cn(
        "relative rounded-2xl overflow-hidden border border-accent-cyan-500/30 bg-background-panel shadow-cyan-md",
        className
      )}
      whileHover={{ 
        boxShadow: "0 0 30px rgba(24, 202, 254, 0.4)",
        borderColor: "rgba(24, 202, 254, 0.6)"
      }}
      transition={{ duration: 0.3 }}
    >
      {/* Video container with enhanced holo effect */}
      <div className="relative aspect-video bg-black rounded-t-2xl overflow-hidden">
        <video
          ref={videoRef}
          src={src}
          className="w-full h-full object-cover"
          onTimeUpdate={handleProgress}
          onEnded={() => setIsPlaying(false)}
        />
        
        {/* Enhanced holo overlay effect */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-t from-background-panel/70 via-transparent to-background-panel/30" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(24,202,254,0.15)_0%,transparent_70%)]" />
          
          {/* Atmospheric edge lighting */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-accent-cyan-500 to-transparent opacity-70" />
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-accent-violet-500 to-transparent opacity-70" />
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-transparent via-accent-cyan-500 to-transparent opacity-70" />
          <div className="absolute right-0 top-0 bottom-0 w-1 bg-gradient-to-b from-transparent via-accent-violet-500 to-transparent opacity-70" />
        </div>
        
        {/* Interactive subtitles */}
        {showSubtitles && subtitles.map((subtitle, index) => (
          subtitle.active && (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="absolute bottom-20 left-1/2 transform -translate-x-1/2 bg-background-panel/80 backdrop-blur-sm border border-accent-cyan-500/30 rounded-lg px-4 py-2 max-w-md"
            >
              <p className="text-text-primary text-center font-medium">{subtitle.text}</p>
            </motion.div>
          )
        ))}
        
        {/* Play/Pause overlay with enhanced animation */}
        <motion.button
          className="absolute inset-0 flex items-center justify-center bg-black/30 backdrop-blur-sm"
          onClick={togglePlay}
          whileHover={{ backgroundColor: "rgba(0, 0, 0, 0.2)" }}
          whileTap={{ scale: 0.95 }}
        >
          {!isPlaying && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="w-20 h-20 rounded-full bg-accent-cyan-500/90 flex items-center justify-center backdrop-blur-sm relative"
            >
              <Play className="w-8 h-8 text-white ml-1 relative z-10" />
              {/* Glow effect */}
              <div className="absolute inset-0 bg-accent-cyan-500 rounded-full blur-md opacity-50" />
            </motion.div>
          )}
        </motion.button>
      </div>
      
      {/* Video controls with cinematic styling */}
      <div className="p-4 bg-background-surface/50 backdrop-blur-sm rounded-b-2xl border-t border-border-subtle">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="text-text-primary font-display text-lg">{title}</h3>
            <p className="text-text-secondary text-sm mt-1">{description}</p>
          </div>
          <div className="flex items-center gap-2 text-text-secondary text-sm">
            <span>{currentTime}</span>
            <span>/</span>
            <span>{duration}</span>
          </div>
        </div>
        
        {/* Progress bar with glow effect */}
        <div 
          className="w-full h-1.5 bg-background-panel rounded-full cursor-pointer mb-4 relative overflow-hidden"
          onClick={handleSeek}
        >
          <motion.div 
            className="h-full bg-gradient-to-r from-accent-cyan-500 to-accent-violet-500 rounded-full relative"
            style={{ width: `${progress}%` }}
            whileHover={{ height: "6px" }}
          />
          {/* Glow effect on progress */}
          <motion.div 
            className="absolute inset-0 bg-gradient-to-r from-accent-cyan-500/30 to-accent-violet-500/30 rounded-full blur-sm"
            style={{ width: `${progress}%` }}
            whileHover={{ height: "6px" }}
          />
        </div>
        
        {/* Control buttons with enhanced styling */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.button
              className="p-2 rounded-full hover:bg-background-panel transition-colors relative overflow-hidden group/play"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={togglePlay}
            >
              {isPlaying ? (
                <Pause className="w-5 h-5 text-text-primary relative z-10" />
              ) : (
                <Play className="w-5 h-5 text-text-primary relative z-10" />
              )}
              {/* Button glow effect */}
              <div className="absolute inset-0 bg-accent-cyan-500/20 rounded-full blur-sm opacity-0 group-hover/play:opacity-100 transition-opacity duration-300" />
            </motion.button>
            
            <motion.button
              className="p-2 rounded-full hover:bg-background-panel transition-colors relative overflow-hidden group/back"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <SkipBack className="w-5 h-5 text-text-primary relative z-10" />
              {/* Button glow effect */}
              <div className="absolute inset-0 bg-text-secondary/20 rounded-full blur-sm opacity-0 group-hover/back:opacity-100 transition-opacity duration-300" />
            </motion.button>
            
            <motion.button
              className="p-2 rounded-full hover:bg-background-panel transition-colors relative overflow-hidden group/forward"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <SkipForward className="w-5 h-5 text-text-primary relative z-10" />
              {/* Button glow effect */}
              <div className="absolute inset-0 bg-text-secondary/20 rounded-full blur-sm opacity-0 group-hover/forward:opacity-100 transition-opacity duration-300" />
            </motion.button>
          </div>
          
          <div className="flex items-center gap-3">
            <motion.button
              className="p-2 rounded-full hover:bg-background-panel transition-colors relative overflow-hidden group/mute"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={toggleMute}
            >
              {isMuted ? (
                <VolumeX className="w-5 h-5 text-text-primary relative z-10" />
              ) : (
                <Volume2 className="w-5 h-5 text-text-primary relative z-10" />
              )}
              {/* Button glow effect */}
              <div className="absolute inset-0 bg-text-secondary/20 rounded-full blur-sm opacity-0 group-hover/mute:opacity-100 transition-opacity duration-300" />
            </motion.button>
            
            <motion.button
              className="p-2 rounded-full hover:bg-background-panel transition-colors relative overflow-hidden group/subtitles"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setShowSubtitles(!showSubtitles)}
            >
              <span className="text-text-primary text-xs font-bold relative z-10">CC</span>
              {/* Button glow effect */}
              <div className="absolute inset-0 bg-accent-cyan-500/20 rounded-full blur-sm opacity-0 group-hover/subtitles:opacity-100 transition-opacity duration-300" />
              {/* Active indicator */}
              {showSubtitles && (
                <div className="absolute bottom-1 right-1 w-1.5 h-1.5 bg-accent-cyan-500 rounded-full" />
              )}
            </motion.button>
            
            <motion.button
              className="p-2 rounded-full hover:bg-background-panel transition-colors relative overflow-hidden group/fullscreen"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <Maximize className="w-5 h-5 text-text-primary relative z-10" />
              {/* Button glow effect */}
              <div className="absolute inset-0 bg-text-secondary/20 rounded-full blur-sm opacity-0 group-hover/fullscreen:opacity-100 transition-opacity duration-300" />
            </motion.button>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export { HoloVideoPlayer }