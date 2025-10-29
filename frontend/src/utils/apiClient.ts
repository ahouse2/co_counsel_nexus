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
  TimelineResponse,
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

export async function postQuery(payload: { q: string; filters?: Record<string, string> }): Promise<QueryResponse> {
  const response = await fetch(withBase('/query'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
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
  params: { cursor?: string | null; entity?: string | null; from_ts?: string | null; to_ts?: string | null; limit?: number } = {}
): Promise<TimelineResponse> {
  const search = new URLSearchParams();
  if (params.cursor) search.set('cursor', params.cursor);
  if (params.entity) search.set('entity', params.entity);
  if (params.from_ts) search.set('from_ts', params.from_ts);
  if (params.to_ts) search.set('to_ts', params.to_ts);
  if (typeof params.limit === 'number') search.set('limit', String(params.limit));
  const response = await fetch(withBase(`/timeline?${search.toString()}`));
  if (!response.ok) {
    throw new Error(`Timeline request failed with status ${response.status}`);
  }
  return (await response.json()) as TimelineResponse;
}

export function buildStreamUrl(): string {
  const base = BASE || (typeof window !== 'undefined' ? window.location.origin : '');
  if (!base) {
    return '/query/stream';
  }
  const url = new URL(base);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = '/query/stream';
  return url.toString();
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
