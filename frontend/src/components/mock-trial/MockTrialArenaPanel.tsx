import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { motion } from "framer-motion"
import { VideoGrid } from "./VideoGrid"
import { DraggableExhibits } from "./DraggableExhibits"
import { Play, Pause, Mic, MicOff, Video, VideoOff, PhoneOff, Timer, Users } from "lucide-react"
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

interface Exhibit {
  id: string
  title: string
  type: "document" | "image" | "link"
  description: string
  spotlighted: boolean
}

const MockTrialArenaPanel: React.FC = () => {
  const [isRecording, setIsRecording] = React.useState(false)
  const [elapsedTime, setElapsedTime] = React.useState(0)
  const [participants, setParticipants] = React.useState<Participant[]>([
    {
      id: "1",
      name: "Alex Johnson",
      role: "Attorney",
      isMuted: false,
      isVideoOff: false,
      isSpeaking: true,
      isHost: true
    },
    {
      id: "2",
      name: "Sarah Williams",
      role: "Witness",
      isMuted: false,
      isVideoOff: false,
      isSpeaking: false,
      isHost: false
    },
    {
      id: "3",
      name: "Michael Chen",
      role: "Judge",
      isMuted: true,
      isVideoOff: false,
      isSpeaking: false,
      isHost: false
    },
    {
      id: "4",
      name: "Robert Davis",
      role: "Defense",
      isMuted: false,
      isVideoOff: true,
      isSpeaking: false,
      isHost: false
    }
  ])
  
  const [exhibits, setExhibits] = React.useState<Exhibit[]>([
    {
      id: "1",
      title: "Contract Agreement",
      type: "document",
      description: "Signed contract between parties",
      spotlighted: true
    },
    {
      id: "2",
      title: "Crime Scene Photo",
      type: "image",
      description: "Photograph of the incident location",
      spotlighted: false
    },
    {
      id: "3",
      title: "Witness Statement",
      type: "document",
      description: "Statement from key witness",
      spotlighted: false
    },
    {
      id: "4",
      title: "Evidence Database",
      type: "link",
      description: "Link to external evidence repository",
      spotlighted: false
    }
  ])
  
  // Timer effect
  React.useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    
    if (isRecording) {
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 1)
      }, 1000)
    }
    
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isRecording])
  
  const formatTime = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  
  const toggleParticipantMute = (id: string) => {
    setParticipants(prev => prev.map(p => 
      p.id === id ? { ...p, isMuted: !p.isMuted } : p
    ))
  }
  
  const toggleParticipantVideo = (id: string) => {
    setParticipants(prev => prev.map(p => 
      p.id === id ? { ...p, isVideoOff: !p.isVideoOff } : p
    ))
  }
  
  const spotlightExhibit = (id: string) => {
    setExhibits(prev => prev.map(e => 
      e.id === id ? { ...e, spotlighted: !e.spotlighted } : { ...e, spotlighted: false }
    ))
  }
  
  const removeExhibit = (id: string) => {
    setExhibits(prev => prev.filter(e => e.id !== id))
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <Card className="bg-background-panel border-border-subtle shadow-cyan-sm rounded-2xl overflow-hidden">
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <CardTitle className="text-text-primary font-display text-xl">
              Mock Trial Arena
            </CardTitle>
            <div className="flex flex-wrap gap-2">
              <Button 
                variant="cinematic" 
                size="sm"
                onClick={() => setIsRecording(!isRecording)}
                className={cn(
                  "flex items-center gap-2",
                  isRecording && "bg-accent-red hover:bg-accent-red/90"
                )}
              >
                {isRecording ? (
                  <>
                    <Pause className="w-4 h-4" />
                    Stop Session
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Start Session
                  </>
                )}
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                className="flex items-center gap-2 border-border-subtle text-text-secondary"
              >
                <Users className="w-4 h-4" />
                Invite
              </Button>
            </div>
          </div>
          <p className="text-text-secondary text-sm mt-2">
            Live video conferencing with draggable exhibits and real-time transcription
          </p>
        </CardHeader>
        <CardContent>
          {/* Session controls and timer with cinematic styling */}
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6 p-4 bg-background-surface/50 backdrop-blur-sm rounded-xl border border-border-subtle relative overflow-hidden">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-accent-cyan-500/5 to-accent-violet-500/5 rounded-xl" />
            <div className="relative z-10 flex items-center gap-4">
              <div className="flex items-center gap-2 relative overflow-hidden rounded-lg px-3 py-2 bg-background-panel/80 border border-border-subtle">
                <Timer className="w-5 h-5 text-accent-cyan-500 relative z-10" />
                <span className="text-text-primary font-mono relative z-10">{formatTime(elapsedTime)}</span>
                {/* Glow effect for timer */}
                <div className="absolute inset-0 bg-accent-cyan-500/10 rounded-lg" />
              </div>
              <div className="flex items-center gap-2 relative overflow-hidden rounded-lg px-3 py-2 bg-background-panel/80 border border-border-subtle">
                <Users className="w-5 h-5 text-accent-violet-500 relative z-10" />
                <span className="text-text-primary relative z-10">{participants.length} Participants</span>
                {/* Glow effect for participants */}
                <div className="absolute inset-0 bg-accent-violet-500/10 rounded-lg" />
              </div>
            </div>
            
            <div className="relative z-10 flex gap-2">
              <Button 
                variant="outline" 
                size="sm"
                className="flex items-center gap-2 border-border-subtle text-text-secondary relative overflow-hidden group/mute-all"
              >
                <Mic className="w-4 h-4 relative z-10" />
                Mute All
                {/* Button glow effect */}
                <div className="absolute inset-0 bg-text-secondary/10 rounded-md blur-sm opacity-0 group-hover/mute-all:opacity-100 transition-opacity duration-300" />
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                className="flex items-center gap-2 border-border-subtle text-text-secondary relative overflow-hidden group/video-off"
              >
                <Video className="w-4 h-4 relative z-10" />
                Video Off
                {/* Button glow effect */}
                <div className="absolute inset-0 bg-text-secondary/10 rounded-md blur-sm opacity-0 group-hover/video-off:opacity-100 transition-opacity duration-300" />
              </Button>
              <Button 
                variant="destructive" 
                size="sm"
                className="flex items-center gap-2 relative overflow-hidden group/end"
              >
                <PhoneOff className="w-4 h-4 relative z-10" />
                End Session
                {/* Button glow effect */}
                <div className="absolute inset-0 bg-accent-red/20 rounded-md blur-sm opacity-0 group-hover/end:opacity-100 transition-opacity duration-300" />
              </Button>
            </div>
          </div>
          
          {/* Main content area */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Video grid - spans 2 columns on large screens */}
            <div className="lg:col-span-2">
              <VideoGrid 
                participants={participants}
                onToggleMute={toggleParticipantMute}
                onToggleVideo={toggleParticipantVideo}
              />
            </div>
            
            {/* Exhibits panel - spans 1 column on large screens */}
            <div>
              <DraggableExhibits 
                exhibits={exhibits}
                onSpotlight={spotlightExhibit}
                onRemove={removeExhibit}
              />
            </div>
          </div>
          
          {/* Transcript panel with cinematic styling */}
          <div className="mt-6 p-4 bg-background-surface/50 backdrop-blur-sm rounded-xl border border-border-subtle relative overflow-hidden">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-accent-cyan-500/5 to-accent-violet-500/5 rounded-xl" />
            <div className="relative z-10">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-text-primary font-display text-lg">Live Transcript</h3>
                <Button 
                  variant="outline" 
                  size="sm"
                  className="flex items-center gap-2 border-border-subtle text-text-secondary"
                >
                  Export
                </Button>
              </div>
              <div className="h-32 overflow-y-auto rounded-lg bg-background-panel/80 border border-border-subtle p-3">
                <div className="space-y-3 text-sm">
                  <motion.div 
                    className="flex gap-2"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <span className="font-medium text-accent-cyan-500 flex-shrink-0">Alex Johnson:</span>
                    <span className="text-text-primary">Your Honor, I'd like to present Exhibit A, the contract agreement.</span>
                  </motion.div>
                  <motion.div 
                    className="flex gap-2"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: 0.1 }}
                  >
                    <span className="font-medium text-accent-violet-500 flex-shrink-0">Sarah Williams:</span>
                    <span className="text-text-primary">Yes, I signed that document on March 15th, 2023.</span>
                  </motion.div>
                  <motion.div 
                    className="flex gap-2"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: 0.2 }}
                  >
                    <span className="font-medium text-accent-gold flex-shrink-0">Michael Chen:</span>
                    <span className="text-text-primary">Please approach the witness with the document.</span>
                  </motion.div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export { MockTrialArenaPanel }