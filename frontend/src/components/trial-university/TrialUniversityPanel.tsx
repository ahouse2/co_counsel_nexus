import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { motion } from "framer-motion"
import { HoloVideoPlayer } from "./HoloVideoPlayer"
import { BookOpen, Play, Award, Bookmark, Search } from "lucide-react"
import { cn } from "@/lib/utils"

interface Lesson {
  id: string
  title: string
  description: string
  duration: string
  progress: number
  category: string
  bookmarked: boolean
}

const TrialUniversityPanel: React.FC = () => {
  const [lessons, setLessons] = React.useState<Lesson[]>([
    {
      id: "1",
      title: "Cross-Examination Techniques",
      description: "Master the art of questioning witnesses to uncover inconsistencies",
      duration: "12:45",
      progress: 75,
      category: "Evidence",
      bookmarked: true
    },
    {
      id: "2",
      title: "Opening Statements",
      description: "Craft compelling narratives that engage judges and juries",
      duration: "18:30",
      progress: 40,
      category: "Narrative",
      bookmarked: false
    },
    {
      id: "3",
      title: "Objection Handling",
      description: "Strategies for responding to and anticipating legal objections",
      duration: "15:20",
      progress: 0,
      category: "Procedure",
      bookmarked: true
    },
    {
      id: "4",
      title: "Closing Arguments",
      description: "Summarize cases effectively to maximize persuasive impact",
      duration: "22:15",
      progress: 100,
      category: "Narrative",
      bookmarked: false
    }
  ])

  const [searchQuery, setSearchQuery] = React.useState("")

  const toggleBookmark = (id: string) => {
    setLessons(prev => prev.map(lesson => 
      lesson.id === id 
        ? { ...lesson, bookmarked: !lesson.bookmarked } 
        : lesson
    ))
  }

  const filteredLessons = lessons.filter(lesson => 
    lesson.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    lesson.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <Card className="bg-background-panel border-border-subtle shadow-cyan-sm rounded-2xl overflow-hidden mb-6">
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <CardTitle className="text-text-primary font-display text-xl">
              Trial University
            </CardTitle>
            <div className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-secondary" />
                <input
                  type="text"
                  placeholder="Search lessons..."
                  className="pl-10 pr-4 py-2 bg-background-surface border border-border-subtle rounded-lg text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan-500/50"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <Button variant="cinematic" size="sm">
                <BookOpen className="w-4 h-4 mr-2" />
                New Course
              </Button>
            </div>
          </div>
          <p className="text-text-secondary text-sm mt-2">
            Holo-screen video lessons with interactive subtitles and progress tracking
          </p>
        </CardHeader>
        <CardContent>
          {/* Featured lesson player */}
          <div className="mb-8">
            <HoloVideoPlayer
              src="/placeholder-video.mp4"
              title="Cross-Examination Mastery"
              description="Advanced techniques for uncovering witness inconsistencies"
              duration="12:45"
              className="mb-6"
            />
          </div>
          
          {/* Lessons grid with cinematic styling */}
          <div>
            <h3 className="text-text-primary font-display text-lg mb-4">Course Modules</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredLessons.map((lesson, index) => (
                <motion.div
                  key={lesson.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.1 }}
                  whileHover={{ y: -5 }}
                  className="bg-background-surface border border-border-subtle rounded-xl p-4 hover:border-accent-cyan-500/50 transition-all duration-300 relative overflow-hidden group"
                >
                  {/* Neon accent border on left */}
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-accent-cyan-500 to-accent-violet-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="text-text-primary font-medium">{lesson.title}</h4>
                      <p className="text-text-secondary text-sm mt-1">{lesson.description}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleBookmark(lesson.id)}
                      className={lesson.bookmarked ? "text-accent-gold relative" : "text-text-secondary"}
                    >
                      <Bookmark className={`w-4 h-4 ${lesson.bookmarked ? "fill-current" : ""}`} />
                      {/* Glow effect when bookmarked */}
                      {lesson.bookmarked && (
                        <div className="absolute inset-0 bg-accent-gold rounded-full blur-sm opacity-30" />
                      )}
                    </Button>
                  </div>
                  
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs px-2 py-1 bg-accent-violet-500/20 text-accent-violet-300 rounded-full relative overflow-hidden">
                      {/* Glow effect */}
                      <div className="absolute inset-0 bg-accent-violet-500/10" />
                      <span className="relative z-10">{lesson.category}</span>
                    </span>
                    <span className="text-text-secondary text-sm">{lesson.duration}</span>
                  </div>
                  
                  {/* Progress bar with glow effect */}
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-text-secondary mb-1">
                      <span>Progress</span>
                      <span>{lesson.progress}%</span>
                    </div>
                    <div className="w-full h-2 bg-background-panel rounded-full relative overflow-hidden">
                      <motion.div 
                        className="h-full bg-gradient-to-r from-accent-cyan-500 to-accent-violet-500 rounded-full relative"
                        initial={{ width: 0 }}
                        animate={{ width: `${lesson.progress}%` }}
                        transition={{ duration: 0.5, delay: 0.2 }}
                      />
                      {/* Glow effect on progress */}
                      <motion.div 
                        className="absolute inset-0 bg-gradient-to-r from-accent-cyan-500/30 to-accent-violet-500/30 rounded-full blur-sm"
                        initial={{ width: 0 }}
                        animate={{ width: `${lesson.progress}%` }}
                        transition={{ duration: 0.5, delay: 0.2 }}
                      />
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button 
                      variant="cinematic" 
                      size="sm" 
                      className="flex-1 relative overflow-hidden"
                    >
                      <Play className="w-4 h-4 mr-2 relative z-10" />
                      Play
                      {/* Button glow effect */}
                      <div className="absolute inset-0 bg-gradient-to-r from-accent-violet-600/30 to-accent-cyan-500/30 blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="border-border-subtle text-text-secondary relative overflow-hidden group/quiz"
                    >
                      <Award className="w-4 h-4 mr-2 relative z-10" />
                      Quiz
                      {/* Button glow effect on hover */}
                      <div className="absolute inset-0 bg-text-secondary/10 blur-sm opacity-0 group-hover/quiz:opacity-100 transition-opacity duration-300" />
                    </Button>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export { TrialUniversityPanel }