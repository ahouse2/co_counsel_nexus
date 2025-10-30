import {
  BillingPlanListResponse,
  BillingUsageResponse,
  KnowledgeBookmarkResponse,
  KnowledgeLessonDetail,
  KnowledgeLessonListResponse,
  KnowledgeProgressUpdateResponse,
  KnowledgeSearchResponse,
  OnboardingSubmissionPayload,
  OnboardingSubmissionResponse,
  QueryResponse,
  ScenarioDefinition,
  ScenarioListResponse,
  ScenarioRunRequestPayload,
  ScenarioRunResponse,
  TextToSpeechResponsePayload,
  TimelineResponse,
  VoicePersona,
  VoiceSession,
  VoiceSessionResponse,
  DevAgentApplyResponse,
  DevAgentProposalListResponse,
} from '@/types';

const BASE = (() => {
  if (typeof __API_BASE__ !== 'undefined' && __API_BASE__) {
    return __API_BASE__;
  }
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }
  return '';
})();

function withBase(path: string): string {
  return `${BASE}${path}`;
}

export class HttpError extends Error {
  status: number;
  detail?: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function readErrorDetail(response: Response): Promise<unknown> {
  const clone = response.clone();
  try {
    const contentType = clone.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      return await clone.json();
    }
    return await clone.text();
  } catch {
    try {
      return await clone.text();
    } catch {
      return undefined;
    }
  }
}

type QueryPayload = {
  q: string;
  filters?: Record<string, string>;
  mode?: 'precision' | 'recall';
};

export async function postQuery(payload: QueryPayload): Promise<QueryResponse> {
  const params = new URLSearchParams();
  params.set('q', payload.q);
  params.set('mode', payload.mode ?? 'precision');
  if (payload.filters) {
    Object.entries(payload.filters).forEach(([key, value]) => {
      if (value) {
        params.set(`filters[${key}]`, value);
      }
    });
  }
  const response = await fetch(withBase(`/query?${params.toString()}`));
  if (response.status === 204) {
    return {
      answer: 'No supporting evidence found for the supplied query.',
      citations: [],
      traces: { vector: [], graph: {}, forensics: [] },
      meta: { page: 1, page_size: 10, total_items: 0, has_next: false },
    };
  }
  if (!response.ok) {
    throw new Error(`Query request failed with status ${response.status}`);
  }
  return (await response.json()) as QueryResponse;
}

export async function fetchBillingPlans(): Promise<BillingPlanListResponse> {
  const response = await fetch(withBase('/billing/plans'));
  if (!response.ok) {
    throw new Error(`Failed to load billing plans (${response.status})`);
  }
  return (await response.json()) as BillingPlanListResponse;
}

export async function fetchBillingUsage(token?: string): Promise<BillingUsageResponse> {
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(withBase('/billing/usage'), { headers });
  if (response.status === 401) {
    throw new Error('Unauthorized: billing usage requires a bearer token with billing:read scope');
  }
  if (!response.ok) {
    throw new Error(`Failed to load billing usage (${response.status})`);
  }
  return (await response.json()) as BillingUsageResponse;
}

export async function submitOnboarding(
  payload: OnboardingSubmissionPayload
): Promise<OnboardingSubmissionResponse> {
  const response = await fetch(withBase('/onboarding'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Onboarding submission failed (${response.status}): ${detail}`);
  }
  return (await response.json()) as OnboardingSubmissionResponse;
}

export async function fetchTimeline(
  params: {
    cursor?: string | null;
    entity?: string | null;
    from_ts?: string | null;
    to_ts?: string | null;
    limit?: number;
    risk_band?: 'low' | 'medium' | 'high' | null;
    motion_due_before?: string | null;
    motion_due_after?: string | null;
  } = {}
): Promise<TimelineResponse> {
  const search = new URLSearchParams();
  if (params.cursor) search.set('cursor', params.cursor);
  if (params.entity) search.set('entity', params.entity);
  if (params.from_ts) search.set('from_ts', params.from_ts);
  if (params.to_ts) search.set('to_ts', params.to_ts);
  if (typeof params.limit === 'number') search.set('limit', String(params.limit));
  if (params.risk_band) search.set('risk_band', params.risk_band);
  if (params.motion_due_before) search.set('motion_due_before', params.motion_due_before);
  if (params.motion_due_after) search.set('motion_due_after', params.motion_due_after);
  const response = await fetch(withBase(`/timeline?${search.toString()}`));
  if (!response.ok) {
    throw new Error(`Timeline request failed with status ${response.status}`);
  }
  return (await response.json()) as TimelineResponse;
}

export async function fetchDevAgentBacklog(): Promise<DevAgentProposalListResponse> {
  const response = await fetch(withBase('/dev-agent/proposals'));
  if (response.status === 401 || response.status === 403) {
    throw new HttpError('Dev Team backlog access denied.', response.status, await readErrorDetail(response));
  }
  if (!response.ok) {
    throw new HttpError(
      `Failed to load Dev Team backlog (${response.status})`,
      response.status,
      await readErrorDetail(response)
    );
  }
  return (await response.json()) as DevAgentProposalListResponse;
}

export async function applyDevAgentProposal(proposalId: string): Promise<DevAgentApplyResponse> {
  const response = await fetch(withBase('/dev-agent/apply'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ proposal_id: proposalId }),
  });
  if (response.status === 401 || response.status === 403) {
    throw new HttpError('Dev Team approvals require elevated access.', response.status, await readErrorDetail(response));
  }
  if (response.status === 422) {
    throw new HttpError('Proposal validation failed.', response.status, await readErrorDetail(response));
  }
  if (!response.ok) {
    throw new HttpError(
      `Failed to approve proposal (${response.status})`,
      response.status,
      await readErrorDetail(response)
    );
  }
  return (await response.json()) as DevAgentApplyResponse;
}

export function buildStreamUrl(params?: { mode?: string; filters?: Record<string, string> }): string {
  const base = BASE || (typeof window !== 'undefined' ? window.location.origin : '');
  if (!base) {
    const search = new URLSearchParams();
    if (params?.mode) {
      search.set('mode', params.mode);
    }
    if (params?.filters) {
      Object.entries(params.filters).forEach(([key, value]) => {
        if (value) {
          search.set(`filters[${key}]`, value);
        }
      });
    }
    const suffix = search.toString();
    return suffix ? `/query/stream?${suffix}` : '/query/stream';
  }
  const url = new URL(base);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = '/query/stream';
  if (params?.mode) {
    url.searchParams.set('mode', params.mode);
  }
  if (params?.filters) {
    Object.entries(params.filters).forEach(([key, value]) => {
      if (value) {
        url.searchParams.set(`filters[${key}]`, value);
      }
    });
  }
  return url.toString();
}

export async function fetchScenarioMetadata(): Promise<ScenarioListResponse> {
  const response = await fetch(withBase('/scenarios'));
  if (!response.ok) {
    throw new Error(`Failed to load scenarios (${response.status})`);
  }
  return (await response.json()) as ScenarioListResponse;
}

export async function fetchScenarioDefinition(id: string): Promise<ScenarioDefinition> {
  const response = await fetch(withBase(`/scenarios/${encodeURIComponent(id)}`));
  if (response.status === 404) {
    throw new Error(`Scenario ${id} was not found`);
  }
  if (!response.ok) {
    throw new Error(`Failed to load scenario ${id} (${response.status})`);
  }
  return (await response.json()) as ScenarioDefinition;
}

export async function runScenarioSimulation(payload: ScenarioRunRequestPayload): Promise<ScenarioRunResponse> {
  const response = await fetch(withBase('/scenarios/run'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Scenario run failed (${response.status}): ${detail}`);
  }
  return (await response.json()) as ScenarioRunResponse;
}

export async function synthesiseSpeech(payload: {
  text: string;
  voice?: string;
}): Promise<TextToSpeechResponsePayload> {
  const response = await fetch(withBase('/tts/speak'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (response.status === 503) {
    throw new Error('TTS service is not available in this environment.');
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`TTS request failed (${response.status}): ${detail}`);
  }
  return (await response.json()) as TextToSpeechResponsePayload;
}
export async function fetchKnowledgeLessons(): Promise<KnowledgeLessonListResponse> {
  const response = await fetch(withBase('/knowledge/lessons'));
  if (!response.ok) {
    throw new Error(`Failed to load knowledge lessons (${response.status})`);
  }
  return (await response.json()) as KnowledgeLessonListResponse;
}

export async function fetchKnowledgeLesson(lessonId: string): Promise<KnowledgeLessonDetail> {
  const response = await fetch(withBase(`/knowledge/lessons/${lessonId}`));
  if (response.status === 404) {
    throw new Error('Lesson not found');
  }
  if (!response.ok) {
    throw new Error(`Failed to load lesson ${lessonId} (${response.status})`);
  }
  return (await response.json()) as KnowledgeLessonDetail;
}

type KnowledgeSearchPayload = {
  query: string;
  limit?: number;
  filters?: {
    tags?: string[];
    difficulty?: string[];
    media_types?: string[];
  };
};

export async function searchKnowledge(payload: KnowledgeSearchPayload): Promise<KnowledgeSearchResponse> {
  const response = await fetch(withBase('/knowledge/search'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: payload.query,
      limit: payload.limit ?? 10,
      filters: payload.filters,
    }),
  });
  if (!response.ok) {
    throw new Error(`Knowledge search failed (${response.status})`);
  }
  return (await response.json()) as KnowledgeSearchResponse;
}

export async function updateKnowledgeProgress(
  lessonId: string,
  sectionId: string,
  completed = true
): Promise<KnowledgeProgressUpdateResponse> {
  const response = await fetch(withBase(`/knowledge/lessons/${lessonId}/progress`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ section_id: sectionId, completed }),
  });
  if (response.status === 404) {
    throw new Error('Lesson section not found');
  }
  if (!response.ok) {
    throw new Error(`Failed to update progress (${response.status})`);
  }
  return (await response.json()) as KnowledgeProgressUpdateResponse;
}

export async function updateKnowledgeBookmark(
  lessonId: string,
  bookmarked: boolean
): Promise<KnowledgeBookmarkResponse> {
  const response = await fetch(withBase(`/knowledge/lessons/${lessonId}/bookmark`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bookmarked }),
  });
  if (response.status === 404) {
    throw new Error('Lesson not found');
  }
  if (!response.ok) {
    throw new Error(`Failed to update bookmark (${response.status})`);
  }
  return (await response.json()) as KnowledgeBookmarkResponse;
}
export async function fetchVoicePersonas(): Promise<VoicePersona[]> {
  const response = await fetch(withBase('/voice/personas'));
  if (response.status === 401) {
    throw new Error('Voice personas require agents:run scope');
  }
  if (!response.ok) {
    throw new Error(`Failed to load voice personas (${response.status})`);
  }
  const payload = (await response.json()) as { personas: VoicePersona[] };
  return payload.personas;
}

export async function createVoiceSession(formData: FormData): Promise<VoiceSessionResponse> {
  const response = await fetch(withBase('/voice/sessions'), {
    method: 'POST',
    body: formData,
  });
  if (response.status === 401) {
    throw new Error('Voice session creation requires agents:run scope');
  }
  if (response.status === 400) {
    const detail = await response.text();
    throw new Error(detail || 'Voice session rejected');
  }
  if (!response.ok) {
    throw new Error(`Voice session failed (${response.status})`);
  }
  return (await response.json()) as VoiceSessionResponse;
}

export async function fetchVoiceSession(sessionId: string): Promise<VoiceSession> {
  const response = await fetch(withBase(`/voice/sessions/${sessionId}`));
  if (response.status === 404) {
    throw new Error('Voice session not found');
  }
  if (response.status === 401) {
    throw new Error('Voice session requires agents:read scope');
  }
  if (!response.ok) {
    throw new Error(`Failed to load voice session (${response.status})`);
  }
  return (await response.json()) as VoiceSession;
}
