import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface Lesson {
  id: string;
  title: string;
  summary: string;
  progress: number;
  icon: string;
}

const lessons: Lesson[] = [
  {
    id: '1',
    title: 'Introduction to Legal Discovery',
    summary: 'Understand the basics of evidence collection and its importance.',
    progress: 75,
    icon: 'fa-solid fa-magnifying-glass',
  },
  {
    id: '2',
    title: 'Crafting Compelling Arguments',
    summary: 'Develop persuasive legal arguments and presentation skills.',
    progress: 50,
    icon: 'fa-solid fa-gavel',
  },
  {
    id: '3',
    title: 'Navigating Courtroom Procedures',
    summary: 'Learn the intricacies of courtroom etiquette and procedures.',
    progress: 25,
    icon: 'fa-solid fa-scale-balanced',
  },
  {
    id: '4',
    title: 'AI in Legal Research',
    summary: 'Leverage AI tools for efficient and comprehensive legal research.',
    progress: 90,
    icon: 'fa-solid fa-robot',
  },
  {
    id: '5',
    title: 'Ethical Considerations in AI Law',
    summary: 'Explore the ethical implications of AI in the legal profession.',
    progress: 10,
    icon: 'fa-solid fa-book',
  },
];

export function TrialUniversityPanel() {
  const [selectedLesson, setSelectedLesson] = useState<string | null>(null);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.5, ease: "easeOut" }}
      className="panel-shell"
    >
      <header>
        <h2>Trial University</h2>
        <p className="panel-subtitle">Learn and master trial strategies with interactive modules.</p>
      </header>
      <div className="holoscreen-container">
        <div className="holoscreen-content">
          {/* Main content area for selected lesson video/details */}
          {selectedLesson ? (
            <div className="selected-lesson-detail">
              <h3>{lessons.find(l => l.id === selectedLesson)?.title}</h3>
              <p>{lessons.find(l => l.id === selectedLesson)?.summary}</p>
              {/* Placeholder for video player */}
              <div className="video-player-placeholder"></div>
            </div>
          ) : (
            <div className="holoscreen-placeholder">
              Select a module to begin your learning journey.
            </div>
          )}
        </div>
      </div>

      <div className="module-carousel">
        {lessons.map((lesson) => (
          <motion.div
            key={lesson.id}
            className={`module-card ${selectedLesson === lesson.id ? 'selected' : ''}`}
            whileHover={{ scale: 1.05, boxShadow: "0 0 25px rgba(0, 255, 255, 0.7)" }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setSelectedLesson(lesson.id)}
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            <div className="neon-accent"></div>
            <div className="module-content">
              <i className={`${lesson.icon} module-icon`}></i>
              <h3>{lesson.title}</h3>
              <p>{lesson.summary}</p>
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${lesson.progress}%` }}>
                  <div className="progress-glow"></div>
                </div>
                <span className="progress-text">{lesson.progress}% Complete</span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
