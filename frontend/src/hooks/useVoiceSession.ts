import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { createVoiceSession, fetchVoicePersonas, fetchVoiceSession } from '@/utils/apiClient';
import { VoicePersona, VoiceSession, VoiceSessionResponse } from '@/types';

export interface VoiceSessionController {
  personas: VoicePersona[];
  selectedPersona: string | null;
  setSelectedPersona: (personaId: string) => void;
  loading: boolean;
  error?: string;
  session?: VoiceSessionResponse;
  detail?: VoiceSession;
  playing: boolean;
  submit: (input: { caseId: string; audio: Blob; threadId?: string | null }) => Promise<void>;
  refresh: (sessionId?: string) => Promise<void>;
  play: () => void;
  stop: () => void;
  sentimentHint?: string;
}

export function useVoiceSession(): VoiceSessionController {
  const [personas, setPersonas] = useState<VoicePersona[]>([]);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [session, setSession] = useState<VoiceSessionResponse | undefined>();
  const [detail, setDetail] = useState<VoiceSession | undefined>();
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchVoicePersonas()
      .then((items) => {
        if (cancelled) return;
        setPersonas(items);
        if (!selectedPersona && items.length > 0) {
          setSelectedPersona(items[0].persona_id);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load voice personas');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPersona]);

  const teardownAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    setPlaying(false);
  }, []);

  const refresh = useCallback(async (explicitId?: string) => {
    const targetId = explicitId ?? session?.session_id;
    if (!targetId) return;
    try {
      const payload = await fetchVoiceSession(targetId);
      setDetail(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to refresh voice session');
    }
  }, [session]);

  const submit = useCallback(
    async ({ caseId, audio, threadId }: { caseId: string; audio: Blob; threadId?: string | null }) => {
      if (!selectedPersona) {
        setError('Select a voice persona');
        return;
      }
      setLoading(true);
      setError(undefined);
      try {
        const form = new FormData();
        form.append('case_id', caseId);
        form.append('persona_id', selectedPersona);
        if (threadId) {
          form.append('thread_id', threadId);
        }
        form.append('audio', audio, 'voice.wav');
        const response = await createVoiceSession(form);
        setSession(response);
        setDetail(undefined);
        teardownAudio();
        const audioElement = new Audio(response.audio_url);
        audioElement.addEventListener('ended', () => setPlaying(false));
        audioRef.current = audioElement;
        setLoading(false);
        await refresh(response.session_id);
      } catch (err) {
        setLoading(false);
        setError(err instanceof Error ? err.message : 'Unable to create voice session');
      }
    },
    [refresh, selectedPersona, teardownAudio]
  );

  const play = useCallback(() => {
    const element = audioRef.current;
    if (!element) return;
    element.play().then(() => setPlaying(true)).catch((err) => {
      setError(err instanceof Error ? err.message : 'Unable to play audio');
    });
  }, []);

  const stop = useCallback(() => {
    const element = audioRef.current;
    if (!element) return;
    element.pause();
    element.currentTime = 0;
    setPlaying(false);
  }, []);

  useEffect(() => () => teardownAudio(), [teardownAudio]);

  const sentimentHint = useMemo(() => {
    const target = detail?.sentiment ?? session?.sentiment;
    if (!target) return undefined;
    const label = target.label.charAt(0).toUpperCase() + target.label.slice(1);
    return `${label} sentiment • pace ${target.pace.toFixed(2)}x`;
  }, [detail, session]);

  return {
    personas,
    selectedPersona,
    setSelectedPersona,
    loading,
    error,
    session,
    detail,
    playing,
    submit,
    refresh,
    play,
    stop,
    sentimentHint,
  };
}
