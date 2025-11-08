import type { ReactNode } from 'react';
import { describe, expect, it, beforeEach, vi, Mock } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { KnowledgeHub } from '@/components/KnowledgeHub';
import {
  fetchKnowledgeLessons,
  fetchKnowledgeLesson,
  searchKnowledge,
  updateKnowledgeBookmark,
  updateKnowledgeProgress,
} from '@/utils/apiClient';
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock('remark-gfm', () => ({ default: () => null }));
vi.mock('@/utils/apiClient', async () => {
  const actual = await vi.importActual<typeof import('@/utils/apiClient')>('@/utils/apiClient');
  return {
    ...actual,
    fetchKnowledgeLessons: vi.fn(),
    fetchKnowledgeLesson: vi.fn(),
    searchKnowledge: vi.fn(),
    updateKnowledgeBookmark: vi.fn(),
    updateKnowledgeProgress: vi.fn(),
  };
});

describe('KnowledgeHub', () => {
  beforeEach(() => {
    (fetchKnowledgeLessons as unknown as Mock).mockResolvedValue({
      lessons: [
        {
          lesson_id: 'civil-discovery-foundations',
          title: 'Civil Discovery Foundations',
          summary: 'Operational blueprint for proportional discovery.',
          tags: ['discovery', 'litigation'],
          difficulty: 'intermediate',
          estimated_minutes: 35,
          jurisdictions: ['Federal'],
          media: [],
          progress: {
            completed_sections: [],
            total_sections: 5,
            percent_complete: 0,
            last_viewed_at: null,
          },
          bookmarked: false,
        },
      ],
      filters: {
        tags: ['discovery'],
        difficulty: ['intermediate'],
        media_types: ['pdf'],
      },
    });
    (fetchKnowledgeLesson as unknown as Mock).mockResolvedValue({
      lesson_id: 'civil-discovery-foundations',
      title: 'Civil Discovery Foundations',
      summary: 'Operational blueprint for proportional discovery.',
      tags: ['discovery', 'litigation'],
      difficulty: 'intermediate',
      estimated_minutes: 35,
      jurisdictions: ['Federal'],
      media: [],
      bookmarked: false,
      progress: {
        completed_sections: [],
        total_sections: 5,
        percent_complete: 0,
        last_viewed_at: null,
      },
      sections: [
        { id: 'overview', title: 'Overview', content: 'Issue litigation holds.', completed: false },
      ],
      strategy_brief: {
        generated_at: '2025-01-01T00:00:00Z',
        summary: 'Strategy map synthesised with 1 argument focus node(s), 1 contradiction link(s), 1 leverage point(s).',
        focus_nodes: [
          { id: 'claim-alpha', type: 'Claim', properties: { label: 'Alpha Claim' } },
        ],
        argument_map: [
          {
            node: { id: 'claim-alpha', type: 'Claim', properties: { label: 'Alpha Claim' } },
            supporting: [
              {
                node: { id: 'evidence-email', type: 'Evidence', properties: { label: 'Email Log' } },
                relation: 'SUPPORTED_BY',
                stance: 'support',
                documents: ['doc-1'],
                weight: 0.8,
              },
            ],
            opposing: [],
            neutral: [],
            documents: ['doc-1'],
          },
        ],
        contradictions: [
          {
            source: { id: 'memo', type: 'Evidence', properties: { label: 'Memo' } },
            target: { id: 'claim-alpha', type: 'Claim', properties: { label: 'Alpha Claim' } },
            relation: 'CONTRADICTS',
            documents: ['doc-2'],
          },
        ],
        leverage_points: [
          {
            node: { id: 'claim-alpha', type: 'Claim', properties: { label: 'Alpha Claim' } },
            influence: 0.42,
            connections: 3,
            documents: ['doc-1', 'doc-2'],
            reason: 'Alpha Claim is connected to 3 node(s), linked to 2 document(s).',
          },
        ],
      },
    });
    (searchKnowledge as unknown as Mock).mockResolvedValue({
      results: [
        {
          lesson_id: 'civil-discovery-foundations',
          lesson_title: 'Civil Discovery Foundations',
          section_id: 'overview',
          section_title: 'Overview',
          snippet: 'Issue litigation holds within 24 hours.',
          score: 0.98,
          tags: ['discovery'],
          difficulty: 'intermediate',
          media: [],
        },
      ],
      elapsed_ms: 12.5,
      applied_filters: {},
    });
    (updateKnowledgeBookmark as unknown as Mock).mockResolvedValue({
      lesson_id: 'civil-discovery-foundations',
      bookmarked: true,
      bookmarks: ['civil-discovery-foundations'],
    });
    (updateKnowledgeProgress as unknown as Mock).mockResolvedValue({
      lesson_id: 'civil-discovery-foundations',
      section_id: 'overview',
      completed_sections: ['overview'],
      total_sections: 5,
      percent_complete: 0.2,
      last_viewed_at: null,
    });
  });

  it('renders catalog and allows bookmarking and progress updates', async () => {
    render(<KnowledgeHub />);

    expect(fetchKnowledgeLessons).toHaveBeenCalled();
    const headings = await screen.findAllByRole('heading', { name: 'Civil Discovery Foundations' });
    expect(headings.length).toBeGreaterThan(0);

    const bookmarkButtons = await screen.findAllByRole('button', { name: /bookmark/i });
    fireEvent.click(bookmarkButtons[0]);
    await waitFor(() => expect(updateKnowledgeBookmark).toHaveBeenCalledWith('civil-discovery-foundations', true));

    const completeButton = await screen.findByRole('button', { name: /mark complete/i });
    fireEvent.click(completeButton);
    await waitFor(() => expect(updateKnowledgeProgress).toHaveBeenCalledWith('civil-discovery-foundations', 'overview', true));

    expect(await screen.findByRole('heading', { level: 4, name: 'Strategy Map' })).toBeInTheDocument();
    expect(screen.getByText(/Strategy map synthesised/i)).toBeInTheDocument();
    expect(screen.getByText('Email Log')).toBeInTheDocument();
    expect(screen.getByText(/Alpha Claim is connected/)).toBeInTheDocument();
  });

  it('submits search queries and renders results', async () => {
    render(<KnowledgeHub />);
    const headings = await screen.findAllByRole('heading', { name: 'Civil Discovery Foundations' });
    expect(headings.length).toBeGreaterThan(0);

    const input = screen.getByRole('searchbox');
    fireEvent.change(input, { target: { value: 'litigation holds' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() =>
      expect(searchKnowledge).toHaveBeenCalledWith({
        query: 'litigation holds',
        filters: { tags: [], difficulty: [], media_types: [] },
      }),
    );
    const snippets = await screen.findAllByText(/Issue litigation holds/i);
    expect(snippets.length).toBeGreaterThan(0);
  });
});




