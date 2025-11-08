import * as React from "react";

import { motion } from "framer-motion"
import { FileText, Image, Link, FileSearch, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface Exhibit {
  id: string
  title: string
  type: "document" | "image" | "link"
  description: string
  spotlighted: boolean
}

interface DraggableExhibitsProps {
  exhibits: Exhibit[]
  onSpotlight?: (id: string) => void
  onRemove?: (id: string) => void
  className?: string
}

const DraggableExhibits: React.FC<DraggableExhibitsProps> = ({ 
  exhibits, 
  onSpotlight,
  onRemove,
  className 
}) => {
  const [draggedItem, setDraggedItem] = React.useState<string | null>(null)
  
  const handleDragStart = (e: React.DragEvent, id: string) => {
    e.dataTransfer.setData("exhibitId", id)
    setDraggedItem(id)
  }
  
  const handleDragEnd = () => {
    setDraggedItem(null)
  }
  
  const getIcon = (type: string) => {
    switch (type) {
      case "document": return <FileText className="w-5 h-5 text-accent-cyan-500" />
      case "image": return <Image className="w-5 h-5 text-accent-violet-500" />
      case "link": return <Link className="w-5 h-5 text-accent-gold" />
      default: return <FileText className="w-5 h-5 text-accent-cyan-500" />
    }
  }
  
  return (
    <div className={cn("space-y-3", className)}>
      <h3 className="text-text-primary font-display text-lg">Exhibits</h3>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {exhibits.map((exhibit, index) => (
          <motion.div
            key={exhibit.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
            draggable
            onDragStart={((e: any) => handleDragStart(e, exhibit.id)) as any}
            onDragEnd={handleDragEnd}
            whileHover={{ 
              scale: 1.02,
              boxShadow: "0 0 20px rgba(24, 202, 254, 0.3)"
            }}
            whileTap={{ scale: 0.98 }}
            className={cn(
              "relative p-4 bg-background-surface border rounded-xl cursor-move transition-all",
              exhibit.spotlighted 
                ? "border-accent-cyan-500 shadow-cyan-md" 
                : "border-border-subtle hover:border-accent-cyan-500/50"
            )}
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5">
                {getIcon(exhibit.type)}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-text-primary font-medium truncate">{exhibit.title}</h4>
                <p className="text-text-secondary text-sm mt-1 truncate">{exhibit.description}</p>
                
                <div className="flex items-center gap-2 mt-3">
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => onSpotlight && onSpotlight(exhibit.id)}
                    className={cn(
                      "text-xs px-2 py-1 rounded-full",
                      exhibit.spotlighted
                        ? "bg-accent-cyan-500/20 text-accent-cyan-300"
                        : "bg-background-panel text-text-secondary hover:bg-accent-cyan-500/10 hover:text-accent-cyan-300"
                    )}
                  >
                    {exhibit.spotlighted ? "Spotlighted" : "Spotlight"}
                  </motion.button>
                  
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => onRemove && onRemove(exhibit.id)}
                    className="text-text-secondary hover:text-accent-red"
                  >
                    <X className="w-4 h-4" />
                  </motion.button>
                </div>
              </div>
            </div>
            
            {/* Drag handle indicator */}
            <div className="absolute top-2 right-2 text-text-secondary/50">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M6 3H8V5H6V3Z" fill="currentColor"/>
                <path d="M6 7H8V9H6V7Z" fill="currentColor"/>
                <path d="M6 11H8V13H6V11Z" fill="currentColor"/>
                <path d="M10 3H12V5H10V3Z" fill="currentColor"/>
                <path d="M10 7H12V9H10V7Z" fill="currentColor"/>
                <path d="M10 11H12V13H10V11Z" fill="currentColor"/>
              </svg>
            </div>
          </motion.div>
        ))}
      </div>
      
      {/* Drop zone for spotlighting */}
      <motion.div
        className="border-2 border-dashed border-accent-cyan-500/50 rounded-xl p-6 text-center bg-background-panel/50"
        whileHover={{ 
          backgroundColor: "rgba(24, 202, 254, 0.1)",
          borderColor: "rgba(24, 202, 254, 0.8)"
        }}
      >
        <FileSearch className="w-8 h-8 text-accent-cyan-500 mx-auto mb-2" />
        <p className="text-text-primary">Drag exhibits here to spotlight them</p>
        <p className="text-text-secondary text-sm mt-1">Spotlighted exhibits will be highlighted during the trial</p>
      </motion.div>
    </div>
  )
}

export { DraggableExhibits }


