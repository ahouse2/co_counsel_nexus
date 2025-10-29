import { useCallback, useRef } from 'react';

interface StreamPayload {
  type: 'token' | 'done' | 'error';
  token?: string;
  detail?: string;
  citations?: unknown[];
}

interface UseWebSocketOptions {
  url: string;
  onToken: (token: string) => void;
  onDone: (payload?: StreamPayload) => void;
  onError: (error: Error) => void;
}

export function useWebSocket({
  url,
  onToken,
  onDone,
  onError,
}: UseWebSocketOptions): { start: (body: Record<string, unknown>) => void; stop: () => void } {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number>(0);

  const start = useCallback<(body: Record<string, unknown>) => void>(
    (body) => {
      try {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          socketRef.current.close(1000, 'reset');
        }
        const socket = new WebSocket(url);
        socketRef.current = socket;
        socket.onopen = () => {
          reconnectRef.current = 0;
          socket.send(JSON.stringify(body));
        };
        socket.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data) as StreamPayload;
            if (payload.type === 'token' && payload.token) {
              onToken(payload.token);
            } else if (payload.type === 'done') {
              onDone(payload);
            } else if (payload.type === 'error') {
              const error = new Error(payload.detail || 'Streaming error');
              onError(error);
            }
          } catch (error) {
            onError(error instanceof Error ? error : new Error('Malformed streaming payload'));
          }
        };
        socket.onerror = () => {
          onError(new Error('WebSocket error'));
        };
        socket.onclose = () => {
          if (reconnectRef.current < 2) {
            reconnectRef.current += 1;
            setTimeout(() => start(body), reconnectRef.current * 500);
          }
        };
      } catch (error) {
        onError(error instanceof Error ? error : new Error('WebSocket setup failed'));
      }
    },
    [onDone, onError, onToken, url]
  );

  const stop = useCallback((): void => {
    if (socketRef.current) {
      socketRef.current.close(1000, 'complete');
      socketRef.current = null;
    }
  }, []);

  return { start, stop };
}
