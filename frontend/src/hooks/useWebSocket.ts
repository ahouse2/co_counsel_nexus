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

interface ManagedSocket extends WebSocket {
  shouldReconnect?: boolean;
}

export function useWebSocket({
  url,
  onToken,
  onDone,
  onError,
}: UseWebSocketOptions): { start: (body: Record<string, unknown>) => void; stop: () => void } {
  const socketRef = useRef<ManagedSocket | null>(null);
  const reconnectRef = useRef<number>(0);
  const lastBodyRef = useRef<Record<string, unknown> | null>(null);

  const start = useCallback<(body: Record<string, unknown>) => void>(
    (body) => {
      try {
        lastBodyRef.current = body;
        if (
          socketRef.current &&
          (socketRef.current.readyState === WebSocket.OPEN ||
            socketRef.current.readyState === WebSocket.CONNECTING)
        ) {
          socketRef.current.shouldReconnect = false;
          socketRef.current.close(1000, 'reset');
        }
        const socket = new WebSocket(url) as ManagedSocket;
        socket.shouldReconnect = true;
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
        socket.onclose = (event) => {
          if (socketRef.current === socket) {
            socketRef.current = null;
          }
          const isCleanClosure = event.code === 1000 || event.code === 1001;
          if (socket.shouldReconnect && !isCleanClosure && lastBodyRef.current) {
            if (reconnectRef.current < 2) {
              reconnectRef.current += 1;
              const retryPayload = lastBodyRef.current;
              setTimeout(() => start(retryPayload), reconnectRef.current * 500);
            }
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
      socketRef.current.shouldReconnect = false;
      const socket = socketRef.current;
      socketRef.current = null;
      lastBodyRef.current = null;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close(1000, 'complete');
      }
    }
  }, []);

  return { start, stop };
}
