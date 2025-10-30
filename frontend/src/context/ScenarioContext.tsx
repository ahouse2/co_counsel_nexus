import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from 'react';

import {
  ScenarioDefinition,
  ScenarioDirectorBeatOverride,
  ScenarioDirectorManifest,
  ScenarioEvidenceBinding,
  ScenarioListResponse,
  ScenarioMetadata,
  ScenarioRunRequestPayload,
  ScenarioRunResponse,
  TextToSpeechResponsePayload,
} from '@/types';
import {
  fetchScenarioDefinition,
  fetchScenarioMetadata,
  runScenarioSimulation,
  synthesiseSpeech,
} from '@/utils/apiClient';

interface ScenarioConfigurationState {
  participants: Record<string, boolean>;
  variables: Record<string, string>;
  evidence: Record<string, ScenarioEvidenceBinding>;
  enableTTS: boolean;
  caseId: string;
}

interface ScenarioState {
  metadata: ScenarioMetadata[];
  metadataStatus: 'idle' | 'loading' | 'loaded' | 'error';
  metadataError?: string;
  scenario?: ScenarioDefinition;
  scenarioStatus: 'idle' | 'loading' | 'loaded' | 'error';
  scenarioError?: string;
  configuration: ScenarioConfigurationState;
  running: boolean;
  runError?: string;
  runResult?: ScenarioRunResponse;
  voicePreview?: TextToSpeechResponsePayload;
  directorManifest?: ScenarioDirectorManifest;
  directorOverrides: Record<string, ScenarioDirectorBeatOverride>;
}

interface ScenarioContextValue {
  state: ScenarioState;
  selectScenario: (scenarioId: string) => Promise<void>;
  updateParticipant: (participantId: string, enabled: boolean) => void;
  updateVariable: (key: string, value: string) => void;
  updateEvidence: (slot: string, value: string, documentId?: string) => void;
  toggleTTS: (enabled: boolean) => void;
  updateCaseId: (caseId: string) => void;
  runScenario: () => Promise<void>;
  previewVoice: (participantId: string, sampleText: string) => Promise<void>;
  updateDirectorOverride: (beatId: string, override: ScenarioDirectorBeatOverride) => void;
  resetDirectorOverride: (beatId?: string) => void;
}

const ScenarioContext = createContext<ScenarioContextValue | undefined>(undefined);

const INITIAL_CONFIGURATION: ScenarioConfigurationState = {
  participants: {},
  variables: {},
  evidence: {},
  enableTTS: false,
  caseId: '',
};

const INITIAL_STATE: ScenarioState = {
  metadata: [],
  metadataStatus: 'idle',
  scenarioStatus: 'idle',
  configuration: INITIAL_CONFIGURATION,
  running: false,
  directorOverrides: {},
};

type Action =
  | { type: 'metadata:loading' }
  | { type: 'metadata:error'; error: string }
  | { type: 'metadata:loaded'; payload: ScenarioMetadata[] }
  | { type: 'scenario:loading' }
  | { type: 'scenario:error'; error: string }
  | { type: 'scenario:loaded'; payload: ScenarioDefinition; configuration: ScenarioConfigurationState }
  | { type: 'config:update'; payload: Partial<ScenarioConfigurationState> }
  | { type: 'config:update-participant'; participant: string; enabled: boolean }
  | { type: 'config:update-variable'; key: string; value: string }
  | { type: 'config:update-evidence'; slot: string; binding: ScenarioEvidenceBinding }
  | { type: 'config:update-case'; caseId: string }
  | { type: 'run:start' }
  | { type: 'run:error'; error: string }
  | { type: 'run:success'; result: ScenarioRunResponse }
  | { type: 'tts:preview'; payload?: TextToSpeechResponsePayload }
  | { type: 'director:update'; beatId: string; override: ScenarioDirectorBeatOverride }
  | { type: 'director:reset'; beatId?: string };

function reducer(state: ScenarioState, action: Action): ScenarioState {
  switch (action.type) {
    case 'metadata:loading':
      return { ...state, metadataStatus: 'loading', metadataError: undefined };
    case 'metadata:error':
      return { ...state, metadataStatus: 'error', metadataError: action.error };
    case 'metadata:loaded':
      return { ...state, metadataStatus: 'loaded', metadata: action.payload };
    case 'scenario:loading':
      return {
        ...state,
        scenarioStatus: 'loading',
        scenarioError: undefined,
        directorManifest: undefined,
        directorOverrides: {},
      };
    case 'scenario:error':
      return {
        ...state,
        scenarioStatus: 'error',
        scenarioError: action.error,
        directorManifest: undefined,
        directorOverrides: {},
      };
    case 'scenario:loaded':
      return {
        ...state,
        scenarioStatus: 'loaded',
        scenario: action.payload,
        configuration: action.configuration,
        runResult: undefined,
        runError: undefined,
        directorManifest: action.payload.director,
        directorOverrides: {},
      };
    case 'config:update':
      return { ...state, configuration: { ...state.configuration, ...action.payload } };
    case 'config:update-participant':
      return {
        ...state,
        configuration: {
          ...state.configuration,
          participants: {
            ...state.configuration.participants,
            [action.participant]: action.enabled,
          },
        },
      };
    case 'config:update-variable':
      return {
        ...state,
        configuration: {
          ...state.configuration,
          variables: {
            ...state.configuration.variables,
            [action.key]: action.value,
          },
        },
      };
    case 'config:update-evidence':
      return {
        ...state,
        configuration: {
          ...state.configuration,
          evidence: {
            ...state.configuration.evidence,
            [action.slot]: action.binding,
          },
        },
      };
    case 'config:update-case':
      return {
        ...state,
        configuration: {
          ...state.configuration,
          caseId: action.caseId,
        },
      };
    case 'run:start':
      return { ...state, running: true, runError: undefined };
    case 'run:error':
      return { ...state, running: false, runError: action.error };
    case 'run:success':
      return { ...state, running: false, runResult: action.result, runError: undefined };
    case 'tts:preview':
      return { ...state, voicePreview: action.payload };
    case 'director:update': {
      const current = state.directorOverrides[action.beatId] ?? {};
      return {
        ...state,
        directorOverrides: {
          ...state.directorOverrides,
          [action.beatId]: { ...current, ...action.override },
        },
      };
    }
    case 'director:reset': {
      if (!action.beatId) {
        return { ...state, directorOverrides: {} };
      }
      const next = { ...state.directorOverrides };
      delete next[action.beatId];
      return { ...state, directorOverrides: next };
    }
    default:
      return state;
  }
}

function buildDefaultConfiguration(definition: ScenarioDefinition): ScenarioConfigurationState {
  const participants = definition.participants.reduce<Record<string, boolean>>((acc, participant) => {
    acc[participant.id] = !participant.optional || participant.default;
    return acc;
  }, {});
  const variables = Object.entries(definition.variables).reduce<Record<string, string>>((acc, [key, variable]) => {
    acc[key] = variable.default ?? '';
    return acc;
  }, {});
  const evidence = definition.evidence.reduce<Record<string, ScenarioEvidenceBinding>>((acc, spec) => {
    acc[spec.id] = {
      value: spec.document_id ?? '',
      document_id: spec.document_id ?? undefined,
      type: spec.type,
    };
    return acc;
  }, {});
  return {
    participants,
    variables,
    evidence,
    enableTTS: false,
    caseId: definition.scenario_id,
  };
}

function validateConfiguration(
  definition: ScenarioDefinition | undefined,
  config: ScenarioConfigurationState
): string | undefined {
  if (!definition) {
    return 'Select a scenario to run the simulation.';
  }
  if (!config.caseId.trim()) {
    return 'Provide a case identifier before running the simulation.';
  }
  const missingVariables: string[] = [];
  const missingEvidence: string[] = [];
  Object.entries(definition.variables).forEach(([key, variable]) => {
    if (variable.required && !config.variables[key]?.trim()) {
      missingVariables.push(variable.name ?? key);
    }
  });
  definition.evidence.forEach((spec) => {
    if (!spec.required) return;
    const binding = config.evidence[spec.id];
    if (!binding || !binding.value?.trim()) {
      missingEvidence.push(spec.label ?? spec.id);
    }
  });
  if (missingVariables.length || missingEvidence.length) {
    const parts = [];
    if (missingVariables.length) {
      parts.push(`variables: ${missingVariables.join(', ')}`);
    }
    if (missingEvidence.length) {
      parts.push(`evidence: ${missingEvidence.join(', ')}`);
    }
    return `Provide values for ${parts.join(' and ')}.`;
  }
  return undefined;
}

export function ScenarioProvider({ children }: { children: ReactNode }): JSX.Element {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);

  useEffect(() => {
    let cancelled = false;
    const load = async (): Promise<void> => {
      dispatch({ type: 'metadata:loading' });
      try {
        const response: ScenarioListResponse = await fetchScenarioMetadata();
        if (!cancelled) {
          dispatch({ type: 'metadata:loaded', payload: response.scenarios });
        }
      } catch (error) {
        if (!cancelled) {
          dispatch({ type: 'metadata:error', error: (error as Error).message });
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectScenario = useCallback(
    async (scenarioId: string) => {
      if (state.scenarioStatus === 'loading' && state.scenario?.scenario_id === scenarioId) {
        return;
      }
      dispatch({ type: 'scenario:loading' });
      try {
        const definition = await fetchScenarioDefinition(scenarioId);
        const configuration = buildDefaultConfiguration(definition);
        dispatch({ type: 'scenario:loaded', payload: definition, configuration });
      } catch (error) {
        dispatch({ type: 'scenario:error', error: (error as Error).message });
      }
    },
    [state.scenarioStatus, state.scenario]
  );

  const updateParticipant = useCallback((participantId: string, enabled: boolean) => {
    dispatch({ type: 'config:update-participant', participant: participantId, enabled });
  }, []);

  const updateVariable = useCallback((key: string, value: string) => {
    dispatch({ type: 'config:update-variable', key, value });
  }, []);

  const updateEvidence = useCallback((slot: string, value: string, documentId?: string) => {
    dispatch({
      type: 'config:update-evidence',
      slot,
      binding: {
        value,
        document_id: documentId,
        type:
          state.scenario?.evidence.find((spec) => spec.id === slot)?.type ??
          state.configuration.evidence[slot]?.type ??
          null,
      },
    });
  }, [state.configuration.evidence, state.scenario?.evidence]);

  const updateCaseId = useCallback((caseId: string) => {
    dispatch({ type: 'config:update-case', caseId });
  }, []);

  const toggleTTS = useCallback((enabled: boolean) => {
    dispatch({ type: 'config:update', payload: { enableTTS: enabled } });
  }, []);

  const runScenario = useCallback(async () => {
    const validationError = validateConfiguration(state.scenario, state.configuration);
    if (validationError) {
      dispatch({ type: 'run:error', error: validationError });
      return;
    }
    if (!state.scenario) {
      dispatch({ type: 'run:error', error: 'Select a scenario to run.' });
      return;
    }
    const payload: ScenarioRunRequestPayload = {
      scenario_id: state.scenario.scenario_id,
      case_id: state.configuration.caseId.trim() || state.scenario.scenario_id,
      participants: Object.entries(state.configuration.participants)
        .filter(([, enabled]) => enabled)
        .map(([id]) => id),
      variables: state.configuration.variables,
      evidence: state.configuration.evidence,
      enable_tts: state.configuration.enableTTS,
      director_overrides: state.directorOverrides,
    };
    dispatch({ type: 'run:start' });
    try {
      const result = await runScenarioSimulation(payload);
      dispatch({ type: 'run:success', result });
    } catch (error) {
      dispatch({ type: 'run:error', error: (error as Error).message });
    }
  }, [state.configuration, state.scenario]);

  const previewVoice = useCallback(
    async (participantId: string, sampleText: string) => {
      const participant = state.scenario?.participants.find((item) => item.id === participantId);
      if (!participant || !participant.voice) {
        dispatch({ type: 'tts:preview', payload: undefined });
        return;
      }
      try {
        const response = await synthesiseSpeech({ text: sampleText, voice: participant.voice });
        dispatch({ type: 'tts:preview', payload: response });
      } catch (error) {
        dispatch({ type: 'tts:preview', payload: undefined });
        dispatch({ type: 'run:error', error: (error as Error).message });
      }
    },
    [state.scenario]
  );

  const updateDirectorOverride = useCallback(
    (beatId: string, override: ScenarioDirectorBeatOverride) => {
      dispatch({ type: 'director:update', beatId, override });
    },
    []
  );

  const resetDirectorOverride = useCallback(
    (beatId?: string) => {
      dispatch({ type: 'director:reset', beatId });
    },
    []
  );

  const value = useMemo<ScenarioContextValue>(
    () => ({
      state,
      selectScenario,
      updateParticipant,
      updateVariable,
      updateEvidence,
      toggleTTS,
      updateCaseId,
      runScenario,
      previewVoice,
      updateDirectorOverride,
      resetDirectorOverride,
    }),
    [
      state,
      selectScenario,
      updateParticipant,
      updateVariable,
      updateEvidence,
      toggleTTS,
      updateCaseId,
      runScenario,
      previewVoice,
      updateDirectorOverride,
      resetDirectorOverride,
    ]
  );

  return <ScenarioContext.Provider value={value}>{children}</ScenarioContext.Provider>;
}

export function useScenario(): ScenarioContextValue {
  const context = useContext(ScenarioContext);
  if (!context) {
    throw new Error('useScenario must be used within a ScenarioProvider');
  }
  return context;
}
