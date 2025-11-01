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
  const personaDirective = voice.detail?.persona_directive ?? voice.session?.persona_directive;
  const sentimentArc = voice.detail?.sentiment_arc ?? voice.session?.sentiment_arc ?? [];
  const personaShifts = voice.detail?.persona_shifts ?? voice.session?.persona_shifts ?? [];
  const translation = voice.detail?.translation ?? voice.session?.translation;
  const glossaryEntries = useMemo(() => {
    const entries = Object.entries(personaDirective?.glossary ?? translation?.glossary ?? {});
    return entries.slice(0, 6);
  }, [personaDirective?.glossary, translation?.glossary]);

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
      {personaDirective && (
        <section className="voice-console__persona-directive" aria-label="Adaptive persona summary">
          <header>
            <h3>Adaptive Persona</h3>
            <p>
              Tone <strong>{personaDirective.tone}</strong> · Language{' '}
              <strong>{personaDirective.language.toUpperCase()}</strong> · Pace{' '}
              <strong>{personaDirective.pace.toFixed(2)}x</strong>
            </p>
          </header>
          <p className="voice-console__persona-rationale">{personaDirective.rationale}</p>
          {glossaryEntries.length > 0 && (
            <dl className="voice-console__glossary">
              {glossaryEntries.map(([term, value]) => (
                <div key={term}>
                  <dt>{term}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      )}
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
      {translation && (
        <section className="voice-console__translation" aria-label="Bilingual response">
          <header>
            <h3>Bilingual Response</h3>
            <p>
              {translation.source_language.toUpperCase()} → {translation.target_language.toUpperCase()}
            </p>
          </header>
          <p className="voice-console__translation-text">{translation.bilingual_text}</p>
        </section>
      )}
      {sentimentArc.length > 0 && (
        <section className="voice-console__sentiment-arc" aria-label="Sentiment arc visualization">
          <header>
            <h3>Sentiment Arc</h3>
          </header>
          <ol>
            {sentimentArc.map((point) => (
              <li key={point.offset}>
                <span className="voice-console__arc-offset">{point.offset.toFixed(1)}s</span>
                <span className={`voice-console__arc-score voice-console__arc-score--${point.label}`} style={{ width: `${point.score * 100}%` }} />
                <span className="voice-console__arc-label">{point.label}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
      {personaShifts.length > 0 && (
        <section className="voice-console__persona-shifts" aria-label="Persona shifts">
          <header>
            <h3>Persona Shifts</h3>
          </header>
          <ol>
            {personaShifts.map((shift, index) => (
              <li key={`${shift.at}-${index}`}>
                <span className="voice-console__shift-time">{shift.at.toFixed(1)}s</span>
                <span className="voice-console__shift-tone">{shift.tone}</span>
                <span className="voice-console__shift-language">{shift.language.toUpperCase()}</span>
                <span className="voice-console__shift-trigger">{shift.trigger}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
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
