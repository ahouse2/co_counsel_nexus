import { FormEvent, useEffect, useMemo, useState } from 'react';

import { useMicrophone } from '@/hooks/useMicrophone';
import { useVoiceSession } from '@/hooks/useVoiceSession';

export function VoiceConsole(): JSX.Element {
  const microphone = useMicrophone();
  const voice = useVoiceSession();
  const [caseId, setCaseId] = useState('VOICE-SESSION');
  const [threadId, setThreadId] = useState<string | undefined>();

  const busy = microphone.processing || voice.loading;
  const recordLabel = useMemo(() => {
    if (microphone.processing) return 'Processing…';
    if (microphone.recording) return 'Stop & Send';
    return 'Record Question';
  }, [microphone.processing, microphone.recording]);

  const handleRecord = async (): Promise<void> => {
    if (microphone.recording) {
      const blob = await microphone.stop();
      if (blob) {
        await voice.submit({ caseId, audio: blob, threadId });
        microphone.reset();
      }
      return;
    }
    await microphone.start();
  };

  const handleRefresh = async (): Promise<void> => {
    if (voice.session) {
      await voice.refresh(voice.session.session_id);
    }
  };

  const sessionId = voice.session?.session_id;
  const { refresh } = voice;

  useEffect(() => {
    if (!sessionId) {
      return undefined;
    }
    const interval = window.setInterval(() => {
      void refresh(sessionId);
    }, 5000);
    return () => {
      window.clearInterval(interval);
    };
  }, [refresh, sessionId]);

  const transcriptSegments = useMemo(() => voice.detail?.segments ?? voice.session?.segments ?? [], [voice.detail, voice.session]);
  const fullTranscript = voice.detail?.transcript ?? voice.session?.transcript;

  const handleCaseSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const nextCase = (data.get('caseId') as string).trim();
    const nextThread = (data.get('threadId') as string).trim();
    if (nextCase) {
      setCaseId(nextCase);
    }
    setThreadId(nextThread || undefined);
  };

  return (
    <section className="voice-console" aria-label="Voice console">
      <header className="voice-console__header">
        <h2>Voice Interface</h2>
        <form className="voice-console__case" onSubmit={handleCaseSubmit}>
          <label htmlFor="voice-case">Case ID</label>
          <input id="voice-case" name="caseId" defaultValue={caseId} aria-label="Case identifier" />
          <label htmlFor="voice-thread">Thread ID (optional)</label>
          <input
            id="voice-thread"
            name="threadId"
            defaultValue={threadId ?? ''}
            aria-label="Existing thread identifier"
          />
          <button type="submit">Apply</button>
        </form>
      </header>
      <div className="voice-console__persona">
        <label htmlFor="voice-persona">Voice Persona</label>
        <select
          id="voice-persona"
          value={voice.selectedPersona ?? ''}
          onChange={(event) => voice.setSelectedPersona(event.target.value)}
          disabled={voice.personas.length === 0 || busy}
        >
          {voice.personas.map((persona) => (
            <option key={persona.persona_id} value={persona.persona_id}>
              {persona.label}
            </option>
          ))}
        </select>
        {voice.selectedPersona && (
          <span className="voice-console__persona-description">
            {voice.personas.find((item) => item.persona_id === voice.selectedPersona)?.description ?? ''}
          </span>
        )}
      </div>
      <div className="voice-console__controls">
        <button type="button" onClick={() => void handleRecord()} disabled={busy} className={microphone.recording ? 'recording' : ''}>
          {recordLabel}
        </button>
        <button
          type="button"
          onClick={() => (voice.playing ? voice.stop() : voice.play())}
          disabled={!voice.session || voice.loading}
        >
          {voice.playing ? 'Stop Playback' : 'Play Response'}
        </button>
        <button type="button" onClick={() => void handleRefresh()} disabled={!voice.session || voice.loading}>
          Refresh Sentiment
        </button>
      </div>
      <div className="voice-console__waveform" aria-hidden="true">
        {microphone.waveform.map((value, index) => (
          <span key={index} style={{ height: `${Math.min(1, value) * 100}%` }} />
        ))}
      </div>
      <section className="voice-console__transcript" aria-live="polite" aria-label="Live transcription">
        <header>
          <h3>Live Transcription</h3>
          {fullTranscript && <p className="voice-console__transcript-summary">{fullTranscript}</p>}
        </header>
        <ol>
          {transcriptSegments.length > 0 ? (
            transcriptSegments.map((segment) => (
              <li key={`${segment.start}-${segment.end}`}>
                <span className="voice-console__transcript-time">
                  {segment.start.toFixed(1)}s – {segment.end.toFixed(1)}s
                </span>
                <span>{segment.text}</span>
                <span className="confidence">{(segment.confidence * 100).toFixed(0)}%</span>
              </li>
            ))
          ) : (
            <li className="voice-console__transcript-empty">No transcription available yet.</li>
          )}
        </ol>
      </section>
      <footer className="voice-console__status">
        {microphone.error && (
          <p role="alert" className="voice-console__error">
            {microphone.error}
          </p>
        )}
        {voice.error && (
          <p role="alert" className="voice-console__error">
            {voice.error}
          </p>
        )}
        {voice.sentimentHint && !voice.error && !microphone.error && (
          <p className="voice-console__sentiment">{voice.sentimentHint}</p>
        )}
        {voice.session && (
          <p className="voice-console__meta">
            Session {voice.session.session_id} · Persona {voice.session.persona_id}
          </p>
        )}
      </footer>
    </section>
  );
}
