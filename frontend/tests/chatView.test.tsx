import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryProvider } from '@/context/QueryContext';
import { ChatView } from '@/components/ChatView';

const mockResolvedModels = {
  chat: {
    providerId: 'gemini',
    model: {
      id: 'gemini-2.5-flash',
      display_name: 'Gemini 2.5 Flash',
      capabilities: ['chat', 'vision'],
      modalities: ['text', 'vision'],
      context_window: 1000,
      availability: 'general-cloud',
    },
  },
  embeddings: {
    providerId: 'gemini',
    model: {
      id: 'text-embedding-004',
      display_name: 'Text Embedding 004',
      capabilities: ['embeddings'],
      modalities: ['text'],
      context_window: 8192,
      availability: 'general-cloud',
    },
  },
  vision: {
    providerId: 'gemini',
    model: {
      id: 'gemini-2.5-flash',
      display_name: 'Gemini 2.5 Flash',
      capabilities: ['vision', 'chat'],
      modalities: ['text', 'vision'],
      context_window: 1000,
      availability: 'general-cloud',
    },
  },
};

vi.mock('@/utils/apiClient', () => ({
  postQuery: vi.fn(async () => ({
    answer: 'Mock answer',
    citations: [],
    traces: { vector: [], graph: {}, forensics: [] },
    meta: {
      page: 1,
      page_size: 1,
      total_items: 1,
      has_next: false,
      mode: 'precision',
      reranker: 'rrf',
      llm_provider: 'gemini',
      llm_model: 'gemini-2.5-flash',
      embedding_provider: 'gemini',
      embedding_model: 'text-embedding-004',
    },
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

const mockContextValue = {
  loading: false,
  saving: false,
  error: undefined,
  settings: {
    providers: {
      primary: 'gemini',
      secondary: null,
      defaults: {
        chat: 'gemini-2.5-flash',
        embeddings: 'text-embedding-004',
        vision: 'gemini-2.5-flash',
      },
      api_base_urls: {},
      local_runtime_paths: {},
      available: [
        {
          id: 'gemini',
          display_name: 'Google Gemini',
          capabilities: ['chat', 'embeddings', 'vision'],
          models: [
            mockResolvedModels.chat.model,
            mockResolvedModels.embeddings.model,
          ],
        },
      ],
    },
    credentials: { providers: [], services: {} },
    appearance: { theme: 'system' },
    updated_at: null,
  },
  catalog: [],
  resolvedModels: mockResolvedModels,
  themePreference: 'system',
  refresh: vi.fn(),
  updateSettings: vi.fn(),
  setThemePreference: vi.fn(),
};

vi.mock('@/context/SettingsContext', () => ({
  useSettingsContext: () => mockContextValue,
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
