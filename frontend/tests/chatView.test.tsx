import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryProvider } from '@/context/QueryContext';
import { ChatView } from '@/components/ChatView';

vi.mock('@/utils/apiClient', () => ({
  postQuery: vi.fn(async () => ({
    answer: 'Mock answer',
    citations: [],
    traces: { vector: [], graph: {}, forensics: [] },
    meta: { page: 1, page_size: 1, total_items: 1, has_next: false },
  })),
  fetchTimeline: vi.fn(async () => ({
    events: [],
    meta: { cursor: null, limit: 20, has_more: false },
  })),
  buildStreamUrl: vi.fn(() => 'ws://localhost/mock'),
  fetchVoicePersonas: vi.fn(async () => []),
}));

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    start: vi.fn(),
    stop: vi.fn(),
  }),
}));

vi.mock('@/utils/cache', () => ({
  saveChatHistory: vi.fn(),
  loadChatHistory: vi.fn(async () => []),
  saveTimeline: vi.fn(),
  loadTimeline: vi.fn(async () => []),
}));

let uid = 0;
vi.mock('uuid', () => ({ v4: () => `uuid-${uid++}` }));

function Wrapper({ children }: { children: React.ReactNode }) {
  return <QueryProvider>{children}</QueryProvider>;
}

describe('ChatView', () => {
  it('renders compose area and allows submission', async () => {
    render(
      <Wrapper>
        <ChatView />
      </Wrapper>
    );
    const textarea = screen.getByLabelText(/ask a question/i);
    fireEvent.change(textarea, { target: { value: 'Hello world' } });
    fireEvent.submit(textarea.closest('form')!);
    expect(await screen.findByText(/sending/i)).toBeInTheDocument();
  });
});
