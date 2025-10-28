import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { v4 as uuid } from 'uuid';
import { buildStreamUrl, fetchTimeline, postQuery } from '@/utils/apiClient';
import { useWebSocket } from '@/hooks/useWebSocket';
import { loadChatHistory, loadTimeline, saveChatHistory, saveTimeline } from '@/utils/cache';
import { ChatMessage, Citation, TimelineEvent, TimelineResponse } from '@/types';

type QueryContextValue = {
  messages: ChatMessage[];
  citations: Citation[];
  timelineEvents: TimelineEvent[];
  timelineMeta: TimelineResponse['meta'] | null;
  timelineLoading: boolean;
  loading: boolean;
  error?: string;
  sendMessage: (prompt: string) => Promise<void>;
  retryLast: () => Promise<void>;
  activeCitation: Citation | null;
  setActiveCitation: (citation: Citation | null) => void;
  loadMoreTimeline: () => Promise<void>;
  refreshTimelineOnDemand: () => Promise<void>;
  timelineEntityFilter: string | null;
  setTimelineEntityFilter: (entity: string | null) => void;
};

const QueryContext = createContext<QueryContextValue | undefined>(undefined);

const initialMeta = { cursor: null, limit: 20, has_more: false };

export function QueryProvider({ children }: { children: ReactNode }): JSX.Element {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [timelineMeta, setTimelineMeta] = useState<TimelineResponse['meta'] | null>(initialMeta);
  const [timelineEntityFilter, setTimelineEntityFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const currentStreamId = useRef<string | null>(null);
  const pendingPromptRef = useRef<string | null>(null);

  useEffect(() => {
    loadChatHistory().then((history) => {
      if (history.length) {
        setMessages(history);
        const lastAssistant = history.filter((message) => message.role === 'assistant').slice(-1)[0];
        setCitations(lastAssistant?.citations ?? []);
      }
    });
    loadTimeline().then((cached) => {
      if (cached.length) {
        setTimelineEvents(cached);
      }
    });
  }, []);

  const persistChat = useCallback(
    (nextMessages: ChatMessage[]) => {
      setMessages(nextMessages);
      void saveChatHistory(nextMessages);
    },
    []
  );

  const persistTimeline = useCallback((events: TimelineEvent[]) => {
    setTimelineEvents(events);
    void saveTimeline(events);
  }, []);

  const handleCompletion = useCallback(
    (assistantId: string, response?: StreamPayloadLike) => {
      setMessages((prev) => {
        const updated = prev.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                streaming: false,
                citations: response?.citations ?? message.citations,
                content: response?.answer ?? message.content,
              }
            : message
        );
        void saveChatHistory(updated);
        return updated;
      });
      setCitations(response?.citations ?? []);
      pendingPromptRef.current = null;
    },
    []
  );

  const messagesRef = useRef<ChatMessage[]>([]);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const streamUrl = useMemo(() => buildStreamUrl(), []);

  const { start: startStream, stop: stopStream } = useWebSocket({
    url: streamUrl,
    onToken: (token) => {
      const assistantId = currentStreamId.current;
      if (!assistantId) return;
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantId ? { ...message, content: `${message.content}${token}` } : message
        )
      );
    },
    onDone: (payload) => {
      const assistantId = currentStreamId.current;
      if (!assistantId) return;
      stopStream();
      const responsePayload: StreamPayloadLike = {
        answer: payload?.token ? payload.token : undefined,
        citations: (payload as unknown as { citations?: Citation[] })?.citations,
      };
      handleCompletion(assistantId, responsePayload);
      void refreshTimelineOnDemand();
    },
    onError: (streamError) => {
      const assistantId = currentStreamId.current;
      if (!assistantId) return;
      stopStream();
      setMessages((prev) => {
        const updated = prev.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                streaming: false,
                error: streamError.message,
              }
            : message
        );
        void saveChatHistory(updated);
        return updated;
      });
      setError(streamError.message);
      if (pendingPromptRef.current) {
        void completeViaHttp(assistantId, pendingPromptRef.current);
      }
    },
  });

  const completeViaHttp = useCallback(
    async (assistantId: string, prompt: string) => {
      try {
        const response = await postQuery({ q: prompt });
        setMessages((prev) => {
          const updated = prev.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  streaming: false,
                  error: undefined,
                  content: response.answer,
                  citations: response.citations,
                }
              : message
          );
          void saveChatHistory(updated);
          return updated;
        });
        setCitations(response.citations);
        setLoading(false);
        pendingPromptRef.current = null;
        void refreshTimelineOnDemand();
      } catch (httpError) {
        const detail = httpError instanceof Error ? httpError.message : 'Unable to complete query.';
        setMessages((prev) => {
          const updated = prev.map((message) =>
            message.id === assistantId ? { ...message, streaming: false, error: detail } : message
          );
          void saveChatHistory(updated);
          return updated;
        });
        setError(detail);
        setLoading(false);
      }
    },
    []
  );

  const sendMessage = useCallback(
    async (prompt: string) => {
      if (!prompt.trim()) return;
      setError(undefined);
      setLoading(true);
      const timestamp = new Date().toISOString();
      const userMessage: ChatMessage = {
        id: uuid(),
        role: 'user',
        content: prompt,
        citations: [],
        createdAt: timestamp,
      };
      const assistantId = uuid();
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        citations: [],
        createdAt: timestamp,
        streaming: true,
      };
      currentStreamId.current = assistantId;
      pendingPromptRef.current = prompt;
      persistChat([...messagesRef.current, userMessage, assistantMessage]);
      try {
        startStream({ q: prompt, history: messagesRef.current.map((message) => ({ role: message.role, content: message.content })) });
      } catch (errorStream) {
        const detail = errorStream instanceof Error ? errorStream.message : 'Streaming unavailable';
        setMessages((prev) => {
          const updated = prev.map((message) =>
            message.id === assistantId ? { ...message, streaming: false, error: detail } : message
          );
          void saveChatHistory(updated);
          return updated;
        });
        setError(detail);
        await completeViaHttp(assistantId, prompt);
      }
    },
    [completeViaHttp, persistChat, startStream]
  );

  const retryLast = useCallback(async () => {
    const lastUser = [...messagesRef.current].reverse().find((message) => message.role === 'user');
    if (lastUser) {
      await sendMessage(lastUser.content);
    }
  }, [sendMessage]);

  const refreshTimelineOnDemand = useCallback(async () => {
    setTimelineLoading(true);
    try {
      const response = await fetchTimeline({ entity: timelineEntityFilter ?? undefined, limit: 20 });
      persistTimeline(response.events);
      setTimelineMeta(response.meta);
      setTimelineLoading(false);
    } catch (timelineError) {
      console.warn('Timeline refresh failed', timelineError);
      setTimelineLoading(false);
    }
  }, [persistTimeline, timelineEntityFilter]);

  const loadMoreTimeline = useCallback(async () => {
    if (!timelineMeta?.has_more) return;
    setTimelineLoading(true);
    try {
      const response = await fetchTimeline({
        cursor: timelineMeta.cursor ?? undefined,
        entity: timelineEntityFilter ?? undefined,
        limit: timelineMeta.limit ?? 20,
      });
      const merged = [...timelineEvents, ...response.events];
      persistTimeline(merged);
      setTimelineMeta(response.meta);
      setTimelineLoading(false);
    } catch (errorTimeline) {
      console.warn('Timeline pagination failed', errorTimeline);
      setTimelineLoading(false);
    }
  }, [persistTimeline, timelineEntityFilter, timelineEvents, timelineMeta]);

  const value = useMemo<QueryContextValue>(
    () => ({
      messages,
      citations,
      timelineEvents,
      timelineMeta,
      timelineLoading,
      loading,
      error,
      sendMessage,
      retryLast,
      activeCitation,
      setActiveCitation,
      loadMoreTimeline,
      refreshTimelineOnDemand,
      timelineEntityFilter,
      setTimelineEntityFilter,
    }),
    [
      messages,
      citations,
      timelineEvents,
      timelineMeta,
      timelineLoading,
      loading,
      error,
      sendMessage,
      retryLast,
      activeCitation,
      loadMoreTimeline,
      refreshTimelineOnDemand,
      timelineEntityFilter,
    ]
  );

  return <QueryContext.Provider value={value}>{children}</QueryContext.Provider>;
}

export function useQueryContext(): QueryContextValue {
  const context = useContext(QueryContext);
  if (!context) {
    throw new Error('useQueryContext must be used within QueryProvider');
  }
  return context;
}

type StreamPayloadLike = {
  answer?: string;
  citations?: Citation[];
};
