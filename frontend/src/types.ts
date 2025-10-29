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
