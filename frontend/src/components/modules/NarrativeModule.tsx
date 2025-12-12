import { useState, useEffect, useCallback } from 'react';
import { BookOpen, AlertTriangle, Clock, GitCommit, Play, RefreshCw } from 'lucide-react';
import { endpoints } from '../../services/api';

interface TimelineEvent {
  id: string;
  ts: string;
  title: string;
  summary: string;
  citations: string[];
  risk_score?: number;
}

interface Contradiction {
  title: string;
  description: string;
  event_ids: string[];
  confidence: number;
  severity: 'high' | 'medium' | 'low';
}

export function NarrativeModule() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [contradictions, setContradictions] = useState<Contradiction[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  // Wrap in useCallback to prevent infinite loops and satisfy linter
  const fetchTimeline = useCallback(async () => {
    setLoading(true);
    try {
      const response = await endpoints.timeline.list();
      setEvents(response.data.events);
    } catch (error) {
      console.error("Failed to fetch timeline:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);

  const handleWeave = async () => {
    setLoading(true);
    try {
      // @ts-ignore - explicitly ignoring if type definition is lagging in api.ts
      await endpoints.narrative.weave('default_case');
      await fetchTimeline();
    } catch (error) {
      console.error("Failed to weave narrative:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      // @ts-ignore - explicitly ignoring if type definition is lagging in api.ts
      const response = await endpoints.narrative.detectContradictions('default_case');
      setContradictions(response.data);
    } catch (error) {
      console.error("Failed to analyze contradictions:", error);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <h3 className="text-2xl font-bold mb-2 flex items-center gap-2">
        <BookOpen className="inline-block" /> Narrative Weaver
      </h3>
      <p className="mb-4 text-halo-muted">AI-driven timeline reconstruction and contradiction detection</p>
      
      <div className="flex gap-4 mb-8">
        <button
          className="bg-halo-cyan text-white px-4 py-2 rounded flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleWeave}
          disabled={loading}
        >
          {loading ? <RefreshCw className="animate-spin" /> : <Play />}
          WEAVE NARRATIVE
        </button>
        <button
          className="bg-halo-yellow text-black px-4 py-2 rounded flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleAnalyze}
          disabled={analyzing}
        >
          {analyzing ? <RefreshCw className="animate-spin" /> : <AlertTriangle />}
          DETECT CONTRADICTIONS
        </button>
      </div>

      {/* Timeline Column */}
      <h4 className="text-xl font-semibold mb-2 flex items-center gap-2">
        <Clock /> Master Timeline
      </h4>
      
      <div className="mb-8">
        {loading && events.length === 0 ? (
          <div className="text-halo-muted">Weaving narrative...</div>
        ) : events.length === 0 ? (
          <div className="text-halo-muted">No events found. Click "Weave Narrative" to start.</div>
        ) : (
          events.map((event) => (
            <div key={event.id} className="mb-6 pl-4 border-l-2 border-halo-cyan relative">
              {/* Dot */}
              <div className="absolute -left-2 top-2 w-4 h-4 bg-halo-cyan rounded-full border-2 border-white"></div>
              <div className="flex items-center gap-2 text-xs text-halo-muted mb-1">
                {new Date(event.ts).toLocaleString()}
                {event.risk_score && event.risk_score > 0.7 && (
                  <span className="ml-2 text-red-500 font-bold">HIGH RISK</span>
                )}
              </div>
              <h5 className="text-lg font-bold">{event.title}</h5>
              <div className="mb-2">{event.summary}</div>
              {event.citations.length > 0 && (
                <div className="text-xs text-halo-cyan">
                  Citations:{" "}
                  {event.citations.map((cite, i) => (
                    <span key={i} className="mr-2">{cite}</span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Contradictions Column */}
      <h4 className="text-xl font-semibold mb-2 flex items-center gap-2">
        <GitCommit /> Contradictions
      </h4>
      
      <div>
        {analyzing ? (
          <div className="text-halo-muted">Analyzing inconsistencies...</div>
        ) : contradictions.length === 0 ? (
          <div className="text-halo-muted">
            No contradictions detected yet.
            <br />
            Click "Detect Contradictions" to analyze.
          </div>
        ) : (
          contradictions.map((item, i) => (
            <div key={i} className="mb-6 p-4 border-l-4 border-yellow-400 bg-yellow-50 rounded">
              <h5 className="text-lg font-bold flex items-center gap-2">
                <AlertTriangle className="text-yellow-500" /> {item.title}
              </h5>
              <div className="text-xs text-halo-muted mb-1">
                {(item.confidence * 100).toFixed(0)}% CONFIDENCE
              </div>
              <div className="mb-2">{item.description}</div>
              <div className="text-xs text-halo-cyan">
                Linked to {item.event_ids.length} event{item.event_ids.length !== 1 ? 's' : ''}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}