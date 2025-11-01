import type { ReactNode } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Mock } from 'vitest';
import { ScenarioProvider } from '@/context/ScenarioContext';
import { SimulationWorkbench } from '@/components/simulation/SimulationWorkbench';
import type { ScenarioDefinition, ScenarioListResponse, ScenarioRunResponse } from '@/types';
import * as api from '@/utils/apiClient';

vi.mock('@/utils/apiClient');

const metadata: ScenarioListResponse = {
  scenarios: [
    {
      scenario_id: 'opening-arguments',
      title: 'Opening Arguments',
      description: 'Simulate a patent case.',
      category: 'trial',
      difficulty: 'Intermediate',
      tags: ['trial'],
      participants: ['judge', 'counsel'],
    },
  ],
};

const definition: ScenarioDefinition = {
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
  variables: {
    company: {
      name: 'Client Company',
      description: 'Name of the client organisation.',
      required: true,
      default: 'Acme Labs',
    },
  },
  evidence: [
    {
      id: 'brief',
      label: 'Opening Brief',
      description: 'Prepared remarks reference.',
      required: true,
      type: 'document',
      document_id: 'DOC-001',
    },
  ],
  beats: [
    {
      id: 'beat-1',
      kind: 'scripted',
      speaker: 'counsel',
      stage_direction: 'Steps forward to the podium.',
      emphasis: 'assertive',
      duration_ms: 50,
    },
  ],
  director: {
    version: '1.0',
    beats: {
      'beat-1': {
        beat_id: 'beat-1',
        emotional_tone: 'assertive',
        counter_argument: 'Reinforce {issue}.',
        lighting: { preset: 'assertive', palette: ['#fef08a', '#c2410c'], intensity: 1, focus: 1.2, ambient: 0.6 },
        motion: { direction: 'forward', intensity: 0.7, tempo: 0.9 },
        persona: { expression: 'assertive', vocal_register: 'steady', confidence: 0.85 },
      },
    },
  },
};

const run: ScenarioRunResponse = {
  run_id: 'run-001',
  scenario: definition,
  transcript: [
    {
      beat_id: 'beat-1',
      speaker_id: 'counsel',
      speaker: definition.participants[1],
      text: 'Ladies and gentlemen of the jury…',
      kind: 'scripted',
      stage_direction: 'Steps forward to the podium.',
      duration_ms: 50,
      audio: {
        voice: 'larynx:counsel',
        mime_type: 'audio/wav',
        base64: 'UklGRg==',
        cache_hit: false,
        sha256: 'audio-hash',
      },
      director: definition.director.beats['beat-1'],
    },
  ],
  telemetry: { turns: 1 },
};

const wrapper = ({ children }: { children: ReactNode }) => <ScenarioProvider>{children}</ScenarioProvider>;

class MockAudio {
  paused = true;
  currentTime = 0;
  constructor(public readonly src: string) {}
  play = vi.fn().mockImplementation(() => {
    this.paused = false;
    return Promise.resolve();
  });
  pause = vi.fn().mockImplementation(() => {
    this.paused = true;
  });
}

describe('SimulationWorkbench', () => {
  let originalAudio: typeof Audio | undefined;

  beforeAll(() => {
    originalAudio = globalThis.Audio;
    vi.stubGlobal('Audio', MockAudio as unknown as typeof Audio);
  });

  afterAll(() => {
    if (originalAudio) {
      vi.stubGlobal('Audio', originalAudio);
    }
  });

  beforeEach(() => {
    (api.fetchScenarioMetadata as unknown as Mock).mockResolvedValue(metadata);
    (api.fetchScenarioDefinition as unknown as Mock).mockResolvedValue(definition);
    (api.runScenarioSimulation as unknown as Mock).mockResolvedValue(run);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('configures and plays back simulations', async () => {
    render(<SimulationWorkbench />, { wrapper });

    const select = await screen.findByRole('combobox');
    fireEvent.change(select, { target: { value: 'opening-arguments' } });

    await waitFor(() => expect(screen.getByText('Simulate a patent case.')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('Beat authoring')).toBeInTheDocument());

    const caseId = screen.getByPlaceholderText('Enter case identifier');
    fireEvent.change(caseId, { target: { value: 'CASE-77' } });

    const runButton = screen.getByRole('button', { name: /Run simulation/i });
    fireEvent.click(runButton);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(/Ladies and gentlemen/));
    expect(api.runScenarioSimulation).toHaveBeenCalledWith(
      expect.objectContaining({ case_id: 'CASE-77', participants: expect.arrayContaining(['judge', 'counsel']) })
    );

    const progress = screen.getByRole('progressbar');
    expect(progress).toHaveAttribute('aria-valuenow', '100');

    const playButton = screen.getByRole('button', { name: 'Play' });
    fireEvent.click(playButton);

    await waitFor(() => expect(screen.getByRole('button', { name: 'Play' })).toBeInTheDocument());

    const lists = screen.getAllByRole('list');
    const transcript = lists[lists.length - 1];
    const [active] = within(transcript).getAllByRole('listitem');
    expect(active).toHaveAttribute('data-active', 'true');
  });
});
