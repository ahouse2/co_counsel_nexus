export type Role = 'user' | 'assistant' | 'system';

export interface Citation {
  docId: string;
  span: string;
  uri?: string | null;
  title?: string;
  confidence?: number | null;
  entities?: EntityHighlight[];
}

export interface EntityHighlight {
  id: string;
  label: string;
  type: string;
}

export interface RelationTag {
  source: string;
  target: string;
  type: string;
  label: string;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  citations: Citation[];
  createdAt: string;
  streaming?: boolean;
  error?: string;
}

export interface TimelineEvent {
  id: string;
  ts: string;
  title: string;
  summary: string;
  citations: string[];
  entity_highlights: EntityHighlight[];
  relation_tags: RelationTag[];
  confidence?: number | null;
}

export interface TimelineResponse {
  events: TimelineEvent[];
  meta: {
    cursor?: string | null;
    limit: number;
    has_more: boolean;
  };
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  traces: {
    vector: unknown[];
    graph: Record<string, unknown>;
    forensics: unknown[];
  };
  meta: {
    page: number;
    page_size: number;
    total_items: number;
    has_next: boolean;
  };
}
