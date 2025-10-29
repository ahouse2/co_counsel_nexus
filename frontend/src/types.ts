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

export interface BillingPlan {
  plan_id: string;
  label: string;
  monthly_price_usd: number;
  included_queries: number;
  included_ingest_gb: number;
  included_seats: number;
  support_tier: string;
  support_response_sla_hours: number;
  support_contact: string;
  overage_per_query_usd: number;
  overage_per_gb_usd: number;
  onboarding_sla_hours: number;
  description: string;
}

export interface BillingPlanListResponse {
  generated_at: string;
  plans: BillingPlan[];
}

export interface BillingTenantHealth {
  tenant_id: string;
  plan_id: string;
  plan_label: string;
  support_tier: string;
  support_sla_hours: number;
  support_channel: string;
  total_events: number;
  success_rate: number;
  usage_ratio: number;
  health_score: number;
  ingestion_jobs: number;
  ingestion_gb: number;
  query_count: number;
  average_query_latency_ms: number;
  timeline_requests: number;
  agent_runs: number;
  projected_monthly_cost: number;
  seats_requested: number;
  onboarding_completed: boolean;
  last_event_at: string;
  metadata: Record<string, unknown>;
}

export interface BillingUsageResponse {
  generated_at: string;
  tenants: BillingTenantHealth[];
}

export interface OnboardingSubmissionPayload {
  tenant_id: string;
  organization: string;
  contact_name: string;
  contact_email: string;
  seats: number;
  primary_use_case: string;
  departments: string[];
  estimated_matters_per_month: number;
  roi_baseline_hours_per_matter: number;
  automation_target_percent: number;
  go_live_date?: string | null;
  notes?: string | null;
  success_criteria: string[];
}

export interface OnboardingSubmissionResponse {
  tenant_id: string;
  recommended_plan: string;
  message: string;
  received_at: string;
}

export interface ScenarioParticipant {
  id: string;
  name: string;
  role: string;
  description: string;
  sprite: string;
  accent_color: string;
  voice?: string | null;
  default: boolean;
  optional: boolean;
}

export interface ScenarioVariable {
  name: string;
  description: string;
  required: boolean;
  default?: string | null;
}

export interface ScenarioEvidenceSpec {
  id: string;
  label: string;
  description?: string | null;
  required: boolean;
  type: string;
  document_id?: string | null;
}

export interface ScenarioBeatSpec {
  id: string;
  kind: 'scripted' | 'dynamic';
  speaker: string;
  stage_direction?: string | null;
  emphasis?: string | null;
  duration_ms?: number | null;
  fallback_text?: string | null;
  delegate?: string | null;
  top_k?: number | null;
}

export interface ScenarioDefinition {
  scenario_id: string;
  title: string;
  description: string;
  category: string;
  difficulty: string;
  tags: string[];
  participants: ScenarioParticipant[];
  variables: Record<string, ScenarioVariable>;
  evidence: ScenarioEvidenceSpec[];
  beats: ScenarioBeatSpec[];
}

export interface ScenarioMetadata {
  scenario_id: string;
  title: string;
  description: string;
  category: string;
  difficulty: string;
  tags: string[];
  participants: string[];
}

export interface ScenarioListResponse {
  scenarios: ScenarioMetadata[];
}

export interface ScenarioEvidenceBinding {
  value: string;
  document_id?: string | null;
  type?: string | null;
}

export interface ScenarioRunAudio {
  voice: string;
  mime_type: string;
  base64: string;
  cache_hit: boolean;
  sha256: string;
}

export interface ScenarioRunTurn {
  beat_id: string;
  speaker_id: string;
  speaker: ScenarioParticipant;
  text: string;
  kind: string;
  stage_direction?: string | null;
  emphasis?: string | null;
  duration_ms?: number | null;
  thread_id?: string | null;
  audio?: ScenarioRunAudio | null;
}

export interface ScenarioRunResponse {
  run_id: string;
  scenario: ScenarioDefinition;
  transcript: ScenarioRunTurn[];
  telemetry: Record<string, unknown>;
}

export interface ScenarioRunRequestPayload {
  scenario_id: string;
  case_id: string;
  participants: string[];
  variables: Record<string, string>;
  evidence: Record<string, ScenarioEvidenceBinding>;
  enable_tts: boolean;
}

export interface TextToSpeechResponsePayload {
  voice: string;
  mime_type: string;
  base64: string;
  cache_hit: boolean;
  sha256: string;
}
export interface KnowledgeMedia {
  type: string;
  title: string;
  url: string;
  provider?: string | null;
}

export interface KnowledgeProgress {
  completed_sections: string[];
  total_sections: number;
  percent_complete: number;
  last_viewed_at?: string | null;
}

export interface KnowledgeLessonSection {
  id: string;
  title: string;
  content: string;
  completed: boolean;
}

export interface KnowledgeLessonSummary {
  lesson_id: string;
  title: string;
  summary: string;
  tags: string[];
  difficulty: string;
  estimated_minutes: number;
  jurisdictions: string[];
  media: KnowledgeMedia[];
  progress: KnowledgeProgress;
  bookmarked: boolean;
}

export interface KnowledgeLessonDetail extends KnowledgeLessonSummary {
  sections: KnowledgeLessonSection[];
}

export interface KnowledgeLessonListResponse {
  lessons: KnowledgeLessonSummary[];
  filters: {
    tags: string[];
    difficulty: string[];
    media_types: string[];
  };
}

export interface KnowledgeSearchResult {
  lesson_id: string;
  lesson_title: string;
  section_id: string;
  section_title: string;
  snippet: string;
  score: number;
  tags: string[];
  difficulty: string;
  media: KnowledgeMedia[];
}

export interface KnowledgeSearchResponse {
  results: KnowledgeSearchResult[];
  elapsed_ms: number;
  applied_filters: Record<string, string[]>;
}

export interface KnowledgeProgressUpdateResponse extends KnowledgeProgress {
  lesson_id: string;
  section_id: string;
}

export interface KnowledgeBookmarkResponse {
  lesson_id: string;
  bookmarked: boolean;
  bookmarks: string[];
}
export interface VoicePersona {
  persona_id: string;
  label: string;
  description?: string | null;
  speaker_id?: string | null;
}

export interface VoiceSentiment {
  label: 'positive' | 'negative' | 'neutral';
  score: number;
  pace: number;
}

export interface VoiceSegment {
  start: number;
  end: number;
  text: string;
  confidence: number;
}

export interface VoiceSession {
  session_id: string;
  thread_id: string;
  case_id: string;
  persona_id: string;
  transcript: string;
  sentiment: VoiceSentiment;
  segments: VoiceSegment[];
  created_at: string;
  updated_at: string;
  voice_memory?: Record<string, unknown>;
}

export interface VoiceSessionResponse extends VoiceSession {
  assistant_text: string;
  audio_url: string;
}
