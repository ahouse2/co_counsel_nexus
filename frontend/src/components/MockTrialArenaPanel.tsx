import { cssVar } from "@/lib/utils";
import { SimulationWorkbench } from '@/components/simulation/SimulationWorkbench';

const participants = [
  { id: 'counsel-1', name: 'Lead Counsel', status: 'Speaking', level: 0.86 },
  { id: 'counsel-2', name: 'Co-Counsel', status: 'Preparing objection', level: 0.34 },
  { id: 'expert-1', name: 'Expert Witness', status: 'Muted', level: 0.1 },
];

export function MockTrialArenaPanel(): JSX.Element {
  return (
    <section className="mock-trial" aria-labelledby="mock-trial-title">
      <header>
        <div>
          <h2 id="mock-trial-title">Mock Trial Arena</h2>
          <p>Live rehearsal with neon spotlight exhibits, synced transcripts, and AI co-counsel monitoring.</p>
        </div>
        <div className="arena-timer" role="timer" aria-live="polite">
          00:42:19
        </div>
      </header>
      <div className="arena-body">
        <aside className="arena-participants" aria-label="Participants">
          <ul>
            {participants.map((participant) => (
              <li key={participant.id}>
                <span className="participant-name">{participant.name}</span>
                <span className="participant-status">{participant.status}</span>
                  <span className="participant-meter">
                    <span style={cssVar('--level', participant.level)} />
                  </span>
              </li>
            ))}
          </ul>
          <div className="arena-controls">
            <button type="button">Toggle Mic</button>
            <button type="button">Share Exhibit</button>
            <button type="button" className="danger">
              End Session
            </button>
          </div>
        </aside>
        <div className="arena-stage">
          <div className="arena-video-frame" role="group" aria-label="Live video stage">
            <div className="video-placeholder" aria-hidden>
              <span>Video Stream</span>
            </div>
          </div>
          <div className="arena-simulation">
            <SimulationWorkbench />
          </div>
        </div>
      </div>
    </section>
  );
}

