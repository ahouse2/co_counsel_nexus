import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { TimelineView } from '@/components/TimelineView';
import { TimelineEvent } from '@/types';
import { useQueryContext } from '@/context/QueryContext';

vi.mock('@/context/QueryContext', () => ({
  useQueryContext: vi.fn(),
}));

const baseEvent: TimelineEvent = {
  id: 'event-1',
  ts: '2024-01-01T00:00:00',
  title: 'Motion to compel',
  summary: 'Filed emergency motion to compel production of withheld discovery.',
  citations: ['doc-1'],
  entity_highlights: [
    { id: 'entity-1', label: 'Acme Corp', type: 'Organization' },
  ],
  relation_tags: [
    { source: 'entity-1', target: 'entity-2', type: 'MENTIONS', label: 'mentions', doc: 'doc-1' },
  ],
  confidence: 0.82,
  risk_score: 0.74,
  risk_band: 'high',
  outcome_probabilities: [
    { label: 'Adverse outcome', probability: 0.5 },
    { label: 'Favorable outcome', probability: 0.3 },
    { label: 'Settlement', probability: 0.2 },
  ],
  recommended_actions: [
    'Escalate to lead counsel for immediate review.',
    'Prepare contingency brief addressing adverse arguments.',
  ],
  motion_deadline: '2024-01-21T00:00:00',
};

describe('TimelineView', () => {
  const setTimelineRiskBand = vi.fn();
  const setTimelineDeadline = vi.fn();
  const setTimelineEntityFilter = vi.fn();
  const loadMoreTimeline = vi.fn();

  beforeEach(() => {
    vi.mocked(useQueryContext).mockReturnValue({
      messages: [],
      citations: [],
      timelineEvents: [baseEvent],
      timelineMeta: { cursor: null, limit: 20, has_more: false },
      timelineLoading: false,
      loading: false,
      error: undefined,
      sendMessage: vi.fn(),
      retryLast: vi.fn(),
      activeCitation: null,
      setActiveCitation: vi.fn(),
      loadMoreTimeline,
      refreshTimelineOnDemand: vi.fn(),
      timelineEntityFilter: null,
      setTimelineEntityFilter,
      timelineRiskBand: null,
      setTimelineRiskBand,
      timelineDeadline: null,
      setTimelineDeadline,
      retrievalMode: 'precision',
      setRetrievalMode: vi.fn(),
    });
    setTimelineRiskBand.mockClear();
    setTimelineDeadline.mockClear();
    setTimelineEntityFilter.mockClear();
  });

  it('renders probability arcs and recommended actions', () => {
    const { container } = render(<TimelineView />);

    expect(screen.getByText(/recommended actions/i)).toBeInTheDocument();
    expect(screen.getByText(/Predicted risk score/i)).toBeInTheDocument();
    expect(screen.getByText(/HIGH risk/)).toBeInTheDocument();

    const arc = container.querySelector('svg.probability-arcs');
    expect(arc).not.toBeNull();
    expect(arc).toMatchInlineSnapshot(`
<svg
  class="probability-arcs"
  role="presentation"
  viewBox="0 0 80 80"
>
  <circle
    class="probability-arcs__background"
    cx="40"
    cy="40"
    r="32"
  />
  <circle
    class="probability-arcs__segment"
    cx="40"
    cy="40"
    data-index="0"
    r="32"
    stroke-dasharray="100.53096491487338 100.53096491487338"
    style="stroke: #ff6b6b;"
    transform="rotate(-90 40 40)"
  />
  <circle
    class="probability-arcs__segment"
    cx="40"
    cy="40"
    data-index="1"
    r="32"
    stroke-dasharray="60.31857894892403 140.74335088082273"
    style="stroke: #4dabf7;"
    transform="rotate(90 40 40)"
  />
  <circle
    class="probability-arcs__segment"
    cx="40"
    cy="40"
    data-index="2"
    r="32"
    stroke-dasharray="40.21238596594935 160.8495438637974"
    style="stroke: #ffd43b;"
    transform="rotate(198 40 40)"
  />
</svg>
`);
  });

  it('updates risk and deadline filters from the advanced controls', () => {
    render(<TimelineView />);

    const riskSelect = screen.getByLabelText(/risk band/i);
    fireEvent.change(riskSelect, { target: { value: 'high' } });
    expect(setTimelineRiskBand).toHaveBeenCalledWith('high');

    const deadlineInput = screen.getByLabelText(/motion deadline/i);
    fireEvent.change(deadlineInput, { target: { value: '2025-01-31' } });
    expect(setTimelineDeadline).toHaveBeenCalledWith('2025-01-31T23:59:59');

    const entityInput = screen.getByPlaceholderText(/filter by entity/i);
    fireEvent.change(entityInput, { target: { value: 'Acme' } });
    expect(setTimelineEntityFilter).toHaveBeenCalledWith('Acme');
  });

  it('clears the deadline filter when requested', () => {
    vi.mocked(useQueryContext).mockReturnValue({
      messages: [],
      citations: [],
      timelineEvents: [baseEvent],
      timelineMeta: { cursor: null, limit: 20, has_more: false },
      timelineLoading: false,
      loading: false,
      error: undefined,
      sendMessage: vi.fn(),
      retryLast: vi.fn(),
      activeCitation: null,
      setActiveCitation: vi.fn(),
      loadMoreTimeline,
      refreshTimelineOnDemand: vi.fn(),
      timelineEntityFilter: null,
      setTimelineEntityFilter,
      timelineRiskBand: 'high',
      setTimelineRiskBand,
      timelineDeadline: '2025-02-01T23:59:59',
      setTimelineDeadline,
      retrievalMode: 'precision',
      setRetrievalMode: vi.fn(),
    });

    render(<TimelineView />);
    fireEvent.click(screen.getByRole('button', { name: /clear deadline/i }));
    expect(setTimelineDeadline).toHaveBeenCalledWith(null);
  });
});
