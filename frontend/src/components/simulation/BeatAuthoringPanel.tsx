import { ChangeEvent, useMemo } from 'react';

import { useScenario } from '@/context/ScenarioContext';
import type {
  ScenarioBeatSpec,
  ScenarioDirectorBeat,
  ScenarioDirectorBeatOverride,
} from '@/types';

function mergeDirectorBeat(
  base: ScenarioDirectorBeat,
  override: ScenarioDirectorBeatOverride | undefined
): ScenarioDirectorBeat {
  if (!override) {
    return base;
  }
  return {
    beat_id: base.beat_id,
    emotional_tone: override.emotional_tone ?? base.emotional_tone,
    counter_argument:
      override.counter_argument !== undefined ? override.counter_argument ?? null : base.counter_argument,
    lighting: { ...base.lighting, ...(override.lighting ?? {}) },
    motion: { ...base.motion, ...(override.motion ?? {}) },
    persona: { ...base.persona, ...(override.persona ?? {}) },
  };
}

const TONE_OPTIONS = [
  'neutral',
  'assertive',
  'confident',
  'empathetic',
  'confrontational',
  'urgent',
  'contemplative',
  'hesitant',
];

const DIRECTION_OPTIONS = ['none', 'left', 'right', 'forward', 'back'] as const;

interface AuthoringRowProps {
  beat: ScenarioBeatSpec;
  base: ScenarioDirectorBeat;
  override?: ScenarioDirectorBeatOverride;
  onUpdate: (override: ScenarioDirectorBeatOverride) => void;
  onReset: () => void;
}

function AuthoringRow({ beat, base, override, onUpdate, onReset }: AuthoringRowProps): JSX.Element {
  const merged = useMemo(() => mergeDirectorBeat(base, override), [base, override]);

  const handleToneChange = (event: ChangeEvent<HTMLSelectElement>): void => {
    onUpdate({ emotional_tone: event.currentTarget.value });
  };

  const handleCounterArgumentChange = (event: ChangeEvent<HTMLTextAreaElement>): void => {
    onUpdate({ counter_argument: event.currentTarget.value });
  };

  const handleLightingChange = (key: 'intensity' | 'focus' | 'ambient') =>
    (event: ChangeEvent<HTMLInputElement>): void => {
      const value = Number.parseFloat(event.currentTarget.value);
      onUpdate({ lighting: { ...override?.lighting, [key]: Number.isFinite(value) ? value : merged.lighting[key] } });
    };

  const handleMotionChange = (key: 'direction' | 'intensity' | 'tempo') =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
      const value = key === 'direction' ? event.currentTarget.value : Number.parseFloat(event.currentTarget.value);
      onUpdate({
        motion: {
          ...override?.motion,
          [key]: key === 'direction' ? value : (Number.isFinite(value as number) ? value : merged.motion[key]),
        },
      });
    };

  const handlePersonaConfidence = (event: ChangeEvent<HTMLInputElement>): void => {
    const value = Number.parseFloat(event.currentTarget.value);
    onUpdate({ persona: { ...override?.persona, confidence: Number.isFinite(value) ? value : merged.persona.confidence } });
  };

  const handlePersonaExpression = (event: ChangeEvent<HTMLInputElement>): void => {
    onUpdate({ persona: { ...override?.persona, expression: event.currentTarget.value } });
  };

  return (
    <div className="beat-authoring__row">
      <header>
        <strong>{beat.id}</strong>
        <span>{beat.speaker}</span>
        <span className="beat-authoring__kind">{beat.kind}</span>
      </header>
      <div className="beat-authoring__grid">
        <label>
          <span>Emotional tone</span>
          <select value={merged.emotional_tone} onChange={handleToneChange}>
            {TONE_OPTIONS.map((tone) => (
              <option key={tone} value={tone}>
                {tone}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Lighting intensity</span>
          <input
            type="range"
            min={0}
            max={2}
            step={0.05}
            value={merged.lighting.intensity}
            onChange={handleLightingChange('intensity')}
          />
          <small>{merged.lighting.intensity.toFixed(2)}</small>
        </label>
        <label>
          <span>Motion direction</span>
          <select value={merged.motion.direction} onChange={handleMotionChange('direction')}>
            {DIRECTION_OPTIONS.map((direction) => (
              <option key={direction} value={direction}>
                {direction}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Motion intensity</span>
          <input
            type="range"
            min={0}
            max={2}
            step={0.05}
            value={merged.motion.intensity}
            onChange={handleMotionChange('intensity')}
          />
          <small>{merged.motion.intensity.toFixed(2)}</small>
        </label>
        <label>
          <span>Motion tempo</span>
          <input
            type="range"
            min={0.1}
            max={2}
            step={0.05}
            value={merged.motion.tempo}
            onChange={handleMotionChange('tempo')}
          />
          <small>{merged.motion.tempo.toFixed(2)}</small>
        </label>
        <label>
          <span>Persona expression</span>
          <input type="text" value={merged.persona.expression} onChange={handlePersonaExpression} />
        </label>
        <label>
          <span>Persona confidence</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={merged.persona.confidence}
            onChange={handlePersonaConfidence}
          />
          <small>{merged.persona.confidence.toFixed(2)}</small>
        </label>
      </div>
      <label className="beat-authoring__counter">
        <span>Counter-argument</span>
        <textarea rows={3} value={merged.counter_argument ?? ''} onChange={handleCounterArgumentChange} />
      </label>
      <footer>
        <button type="button" onClick={onReset} disabled={!override}>
          Reset beat
        </button>
      </footer>
    </div>
  );
}

export function BeatAuthoringPanel(): JSX.Element {
  const { state, updateDirectorOverride, resetDirectorOverride } = useScenario();
  const manifest = state.directorManifest;
  const scenarioBeats = state.scenario?.beats ?? [];

  if (!state.scenario || !manifest) {
    return (
      <aside className="beat-authoring" aria-labelledby="beat-authoring-title">
        <h3 id="beat-authoring-title">Beat authoring</h3>
        <p>Select a scenario to customise emotional beats and counter-arguments.</p>
      </aside>
    );
  }

  return (
    <aside className="beat-authoring" aria-labelledby="beat-authoring-title">
      <div className="beat-authoring__header">
        <h3 id="beat-authoring-title">Beat authoring</h3>
        <button type="button" onClick={() => resetDirectorOverride()} disabled={!Object.keys(state.directorOverrides).length}>
          Reset all
        </button>
      </div>
      <p className="beat-authoring__description">
        Adjust cinematic cues, motion, and counter-arguments to tailor the simulation before running playback.
      </p>
      <div className="beat-authoring__list">
        {scenarioBeats.map((beat) => {
          const base = manifest.beats[beat.id];
          if (!base) {
            return null;
          }
          return (
            <AuthoringRow
              key={beat.id}
              beat={beat}
              base={base}
              override={state.directorOverrides[beat.id]}
              onUpdate={(override) => updateDirectorOverride(beat.id, override)}
              onReset={() => resetDirectorOverride(beat.id)}
            />
          );
        })}
      </div>
    </aside>
  );
}
