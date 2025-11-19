import React, { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";

interface AgentEvent {
  timestamp: number;
  type: string;
  agent: string;
  action: string;
  target?: string;
  message: string;
}

export default function AgentLiveGraph() {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Connect to SSE
    const eventSource = new EventSource('/api/agents/stream');
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      console.log('Agent stream connected');
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents((prev) => [data, ...prev].slice(0, 50)); // Keep last 50 events
      } catch (e) {
        console.error('Failed to parse agent event', e);
      }
    };

    eventSource.onerror = (err) => {
      console.error('Agent stream error', err);
      setIsConnected(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  return (
    <Card className="h-full bg-black/40 border-zinc-800 text-zinc-100">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-lg font-light tracking-wide">
            NEURAL LINK
          </CardTitle>
          <Badge variant={isConnected ? "default" : "destructive"} className="text-xs">
            {isConnected ? "LIVE" : "OFFLINE"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] w-full pr-4">
          <div className="space-y-3">
            {events.map((evt, i) => (
              <div key={i} className="flex flex-col gap-1 border-l-2 border-zinc-700 pl-3 py-1">
                <div className="flex justify-between text-xs text-zinc-400">
                  <span>{new Date(evt.timestamp * 1000).toLocaleTimeString()}</span>
                  <span className="uppercase tracking-wider text-[10px]">{evt.type}</span>
                </div>
                <div className="text-sm font-medium text-cyan-400">
                  {evt.agent} <span className="text-zinc-500">→</span> {evt.action}
                </div>
                {evt.target && (
                  <div className="text-xs text-zinc-300">
                    Target: {evt.target}
                  </div>
                )}
                <div className="text-xs text-zinc-500 italic">
                  "{evt.message}"
                </div>
              </div>
            ))}
            {events.length === 0 && (
              <div className="text-center text-zinc-600 py-8">
                Waiting for neural activity...
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
