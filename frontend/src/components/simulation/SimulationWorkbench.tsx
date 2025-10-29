import { useEffect, useRef, useState } from 'react';
import { ScenarioConfigurator } from './ScenarioConfigurator';
import { SimulationCanvas } from './SimulationCanvas';
import { useScenario } from '@/context/ScenarioContext';
import type { ScenarioRunTurn } from '@/types';

function computeDuration(turn: ScenarioRunTurn | undefined): number {
  if (!turn) {
    return 0;
  }
  if (typeof turn.duration_ms === 'number' && turn.duration_ms > 0) {
    return turn.duration_ms;
  }
  const words = turn.text.split(/\s+/).length;
  return Math.max(words * 320, 2500);
}

export function SimulationWorkbench(): JSX.Element {
  const { state } = useScenario();
  const transcript = state.runResult?.transcript ?? [];
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const activeTurn = transcript[currentIndex];

  useEffect(() => {
    setCurrentIndex(0);
    setIsPlaying(false);
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, [state.runResult?.run_id]);

  useEffect(() => {
    if (!isPlaying || !activeTurn) {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      return;
    }
    const duration = computeDuration(activeTurn);
    timerRef.current = window.setTimeout(() => {
      setCurrentIndex((index) => {
        if (index + 1 >= transcript.length) {
          setIsPlaying(false);
          return index;
        }
        return index + 1;
      });
    }, duration);
    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isPlaying, activeTurn, transcript]);

  useEffect(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    if (isPlaying) {
      void element.play().catch(() => undefined);
    } else {
      element.pause();
    }
  }, [isPlaying]);

  useEffect(() => {
    if (!activeTurn?.audio) {
      audioRef.current?.pause();
      audioRef.current = null;
      return;
    }
    const { mime_type: mime, base64 } = activeTurn.audio;
    const audio = new Audio(`data:${mime};base64,${base64}`);
    audioRef.current?.pause();
    audioRef.current = audio;
    if (isPlaying) {
      void audio.play().catch(() => undefined);
    }
    return () => {
      audio.pause();
    };
  }, [activeTurn?.audio?.sha256, isPlaying]);

  const enabledParticipants = state.configuration.participants;
  const progress = transcript.length > 0 ? ((currentIndex + 1) / transcript.length) * 100 : 0;

  const handlePlayToggle = (): void => {
    if (!transcript.length) {
      return;
    }
    setIsPlaying((value) => !value);
  };

  const stepForward = (): void => {
    setIsPlaying(false);
    setCurrentIndex((index) => Math.min(index + 1, Math.max(transcript.length - 1, 0)));
  };

  const stepBackward = (): void => {
    setIsPlaying(false);
    setCurrentIndex((index) => Math.max(index - 1, 0));
  };

  const restart = (): void => {
    setIsPlaying(false);
    setCurrentIndex(0);
  };

  return (
    <div className="simulation-workbench">
      <div className="simulation-workbench__layout">
        <ScenarioConfigurator />
        <section className="simulation-workbench__stage" aria-labelledby="simulation-stage-title">
          <header className="simulation-workbench__stage-header">
            <div>
              <h2 id="simulation-stage-title">Simulation Playback</h2>
              <p>{state.runResult ? 'Review the generated courtroom exchange.' : 'Run a simulation to populate the canvas.'}</p>
            </div>
            <div className="simulation-workbench__playback-controls">
              <button type="button" onClick={restart} disabled={!transcript.length}>
                Restart
              </button>
              <button type="button" onClick={stepBackward} disabled={!transcript.length || currentIndex === 0}>
                Step back
              </button>
              <button type="button" onClick={handlePlayToggle} disabled={!transcript.length}>
                {isPlaying ? 'Pause' : 'Play'}
              </button>
              <button type="button" onClick={stepForward} disabled={!transcript.length || currentIndex >= transcript.length - 1}>
                Step forward
              </button>
            </div>
          </header>
          <SimulationCanvas
            scenario={state.scenario}
            transcript={transcript}
            enabledParticipants={enabledParticipants}
            activeIndex={currentIndex}
            isPlaying={isPlaying}
          />
          <div className="simulation-workbench__progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
            <div className="simulation-workbench__progress-bar" style={{ width: `${progress}%` }} />
          </div>
          <section className="simulation-workbench__transcript" aria-live="polite">
            {transcript.length ? (
              <ol>
                {transcript.map((turn, index) => (
                  <li key={turn.beat_id} data-active={index === currentIndex}>
                    <header>
                      <strong>{turn.speaker.name}</strong>
                      <span>{turn.kind}</span>
                    </header>
                    <p>{turn.text}</p>
                    {turn.stage_direction ? <p className="stage-direction">{turn.stage_direction}</p> : null}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="simulation-workbench__transcript-empty">No transcript yet. Run the simulation to populate dialogue.</p>
            )}
          </section>
          {state.runResult ? (
            <details className="simulation-workbench__telemetry">
              <summary>Show telemetry payload</summary>
              <pre>{JSON.stringify(state.runResult.telemetry, null, 2)}</pre>
            </details>
          ) : null}
        </section>
      </div>
    </div>
  );
}
