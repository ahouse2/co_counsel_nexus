import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SimulationCanvas } from '@/components/simulation/SimulationCanvas';
import type { ScenarioDefinition, ScenarioRunTurn } from '@/types';
import type { SimulationManifest } from '@/hooks/useSimulationAssets';

const manifest: SimulationManifest = {
  version: 1,
  stage: {
    width: 1280,
    height: 720,
    background: '/simulations/backgrounds/courtroom.svg',
    characterPositions: {
      judge: { x: 980, y: 160 },
      counsel: { x: 420, y: 430 },
    },
  },
  characters: {
    judge: { sprite: '/simulations/characters/judge.svg', accentColor: '#f59e0b' },
    counsel: { sprite: '/simulations/characters/counsel.svg', accentColor: '#0ea5e9' },
  },
};

vi.mock('@/hooks/useSimulationAssets', () => ({
  useSimulationAssets: () => ({ manifest, status: 'loaded', error: undefined, reload: vi.fn() }),
}));

const scenario: ScenarioDefinition = {
  scenario_id: 'opening-arguments',
  title: 'Opening Arguments',
  description: 'Simulate a patent case.',
  category: 'trial',
  difficulty: 'Intermediate',
  tags: ['trial'],
  participants: [
    {
      id: 'judge',
      name: 'Hon. Rivera',
      role: 'Judge',
      description: 'Presiding judge.',
      sprite: '/simulations/characters/judge.svg',
      accent_color: '#f59e0b',
      voice: 'larynx:judge',
      default: true,
      optional: false,
    },
    {
      id: 'counsel',
      name: 'Avery Chen',
      role: 'Lead Counsel',
      description: 'Delivers the opening statement.',
      sprite: '/simulations/characters/counsel.svg',
      accent_color: '#0ea5e9',
      voice: 'larynx:counsel',
      default: true,
      optional: false,
    },
  ],
  variables: {},
  evidence: [],
  beats: [
    {
      id: 'beat-1',
      kind: 'scripted',
      speaker: 'counsel',
    },
  ],
};

const transcript: ScenarioRunTurn[] = [
  {
    beat_id: 'beat-1',
    speaker_id: 'counsel',
    speaker: scenario.participants[1],
    text: 'Ladies and gentlemen of the jury…',
    kind: 'scripted',
    stage_direction: 'Steps forward to the podium.',
    emphasis: 'assertive',
    duration_ms: 3200,
  },
];

describe('SimulationCanvas snapshot', () => {
  it('renders deterministic fallback layout', () => {
    const { container } = render(
      <SimulationCanvas
        scenario={scenario}
        transcript={transcript}
        enabledParticipants={{ judge: true, counsel: true }}
        activeIndex={0}
        isPlaying={false}
        forceFallback
      />
    );

    expect(container.firstChild).toMatchSnapshot();
  });
});
