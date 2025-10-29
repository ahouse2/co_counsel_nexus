import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ScenarioProvider, useScenario } from '@/context/ScenarioContext';
import type {
  ScenarioDefinition,
  ScenarioListResponse,
  ScenarioRunResponse,
  TextToSpeechResponsePayload,
} from '@/types';

vi.mock('@/utils/apiClient', () => ({
  fetchScenarioMetadata: vi.fn(),
  fetchScenarioDefinition: vi.fn(),
  runScenarioSimulation: vi.fn(),
  synthesiseSpeech: vi.fn(),
}));

import * as api from '@/utils/apiClient';

const metadataResponse: ScenarioListResponse = {
  scenarios: [
    {
      scenario_id: 'opening-arguments',
      title: 'Opening Arguments',
      description: 'Simulate a high-stakes patent dispute.',
      category: 'trial',
      difficulty: 'Intermediate',
      tags: ['trial', 'patent'],
      participants: ['judge', 'counsel', 'opposition'],
    },
  ],
};

const definition: ScenarioDefinition = {
  scenario_id: 'opening-arguments',
  title: 'Opening Arguments',
  description: 'Simulate a high-stakes patent dispute.',
  category: 'trial',
  difficulty: 'Intermediate',
  tags: ['trial', 'patent'],
  participants: [
    {
      id: 'judge',
      name: 'Hon. Rivera',
      role: 'Judge',
      description: 'Presiding judge keeping the courtroom focused.',
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
      description: 'Defense counsel delivering the opening argument.',
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
      description: 'Prepared opening brief reference.',
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
      duration_ms: 3200,
      fallback_text: 'Ladies and gentlemen of the jury…',
    },
  ],
};

const runResponse: ScenarioRunResponse = {
  run_id: 'run-123',
  scenario: definition,
  transcript: [
    {
      beat_id: 'beat-1',
      speaker_id: 'counsel',
      speaker: definition.participants[1],
      text: 'Ladies and gentlemen of the jury…',
      kind: 'scripted',
      stage_direction: 'Steps forward to the podium.',
      emphasis: 'assertive',
      duration_ms: 3200,
      audio: {
        voice: 'larynx:counsel',
        mime_type: 'audio/wav',
        base64: 'UklGRg==',
        cache_hit: false,
        sha256: 'abc123',
      },
    },
  ],
  telemetry: { turns: 1, latency_ms: 1234 },
};

const ttsResponse: TextToSpeechResponsePayload = {
  voice: 'larynx:counsel',
  mime_type: 'audio/wav',
  base64: 'UklGRg==',
  cache_hit: true,
  sha256: 'tts123',
};

const wrapper = ({ children }: { children: ReactNode }) => <ScenarioProvider>{children}</ScenarioProvider>;

describe('ScenarioContext', () => {
  beforeEach(() => {
    (api.fetchScenarioMetadata as ReturnType<typeof vi.fn>).mockResolvedValue(metadataResponse);
    (api.fetchScenarioDefinition as ReturnType<typeof vi.fn>).mockResolvedValue(definition);
    (api.runScenarioSimulation as ReturnType<typeof vi.fn>).mockResolvedValue(runResponse);
    (api.synthesiseSpeech as ReturnType<typeof vi.fn>).mockResolvedValue(ttsResponse);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('loads metadata on mount and selects a scenario', async () => {
    const { result } = renderHook(() => useScenario(), { wrapper });

    await waitFor(() => expect(result.current.state.metadataStatus).toBe('loaded'));
    expect(result.current.state.metadata).toHaveLength(1);

    await act(async () => {
      await result.current.selectScenario('opening-arguments');
    });

    await waitFor(() => expect(result.current.state.scenarioStatus).toBe('loaded'));
    expect(result.current.state.scenario?.scenario_id).toBe('opening-arguments');
    expect(result.current.state.configuration.participants).toMatchObject({ judge: true, counsel: true });
  });

  it('runs simulations and records transcripts', async () => {
    const { result } = renderHook(() => useScenario(), { wrapper });
    await waitFor(() => expect(result.current.state.metadataStatus).toBe('loaded'));
    await act(async () => {
      await result.current.selectScenario('opening-arguments');
    });
    await waitFor(() => expect(result.current.state.scenarioStatus).toBe('loaded'));

    await act(async () => {
      await result.current.runScenario();
    });
    await waitFor(() => expect(result.current.state.running).toBe(false));

    expect(result.current.state.runResult?.run_id).toBe('run-123');
    expect(api.runScenarioSimulation).toHaveBeenCalledWith(
      expect.objectContaining({ scenario_id: 'opening-arguments', case_id: 'opening-arguments' })
    );
  });

  it('updates case id and previews voices', async () => {
    const { result } = renderHook(() => useScenario(), { wrapper });
    await waitFor(() => expect(result.current.state.metadataStatus).toBe('loaded'));
    await act(async () => {
      await result.current.selectScenario('opening-arguments');
    });
    await waitFor(() => expect(result.current.state.scenarioStatus).toBe('loaded'));

    act(() => {
      result.current.updateCaseId('CASE-42');
    });
    await act(async () => {
      await result.current.previewVoice('counsel', 'Testing preview');
    });

    expect(result.current.state.configuration.caseId).toBe('CASE-42');
    await waitFor(() => expect(result.current.state.voicePreview?.sha256).toBe('tts123'));
    expect(api.synthesiseSpeech).toHaveBeenCalledWith({ text: 'Testing preview', voice: 'larynx:counsel' });
  });
});
