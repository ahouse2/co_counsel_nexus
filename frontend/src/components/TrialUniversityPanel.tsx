import { cssVar } from "@/lib/utils";
const lessons = [
  {
    id: 'module-1',
    title: 'Precision Cross: Financial Forensics',
    duration: '12:48',
    progress: 0.72,
    status: 'In Progress',
    summary: 'Holoscreen walkthrough of cross strategy anchored on privilege-safe financial exhibits.',
  },
  {
    id: 'module-2',
    title: 'Voir Dire Dynamics',
    duration: '09:25',
    progress: 0.45,
    status: 'Queued',
    summary: 'AI identifies risk signals for juror elimination and attitude matching.',
  },
  {
    id: 'module-3',
    title: 'Motion Practice in Motion',
    duration: '16:04',
    progress: 1,
    status: 'Complete',
    summary: 'Dynamic timeline of granted/denied motions with strategy overlays.',
  },
];

export function TrialUniversityPanel(): JSX.Element {
  return (
    <section className="trial-university" aria-labelledby="trial-university-title">
      <header>
        <h2 id="trial-university-title">Trial University</h2>
        <p>Modular holoscreen lessons curated from trial arena telemetry and AI co-counsel insights.</p>
      </header>
      <div className="lesson-grid">
        {lessons.map((lesson) => (
          <article key={lesson.id} className="lesson-card">
            <div className="lesson-progress" style={cssVar('--progress', lesson.progress)}>
              <span className="progress-glow" aria-hidden />
              <span className="progress-fill" aria-hidden />
            </div>
            <div className="lesson-body">
              <h3>{lesson.title}</h3>
              <p className="lesson-summary">{lesson.summary}</p>
              <div className="lesson-meta">
                <span>{lesson.duration}</span>
                <span>{lesson.status}</span>
              </div>
            </div>
            <button type="button" className="lesson-action">
              Continue Lesson
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

