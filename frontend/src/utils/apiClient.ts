import { QueryResponse, TimelineResponse } from '@/types';

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
