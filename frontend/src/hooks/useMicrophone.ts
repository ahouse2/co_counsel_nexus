import { useCallback, useEffect, useRef, useState } from 'react';

import { audioBufferToWav } from '@/utils/audio';

export type MicrophonePermission = 'idle' | 'granted' | 'denied';

export interface MicrophoneState {
  permission: MicrophonePermission;
  recording: boolean;
  processing: boolean;
  waveform: number[];
  error?: string;
  start: () => Promise<void>;
  stop: () => Promise<Blob | null>;
  reset: () => void;
}

export function useMicrophone(sampleRate = 16000): MicrophoneState {
  const [permission, setPermission] = useState<MicrophonePermission>('idle');
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [waveform, setWaveform] = useState<number[]>([]);
  const [error, setError] = useState<string | undefined>();
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const teardown = useCallback(() => {
    if (animationRef.current !== null) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    analyserRef.current?.disconnect();
    analyserRef.current = null;
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => undefined);
      audioContextRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    chunksRef.current = [];
  }, []);

  useEffect(() => () => teardown(), [teardown]);

  const updateWaveform = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteTimeDomainData(data);
    const normalised = Array.from({ length: 64 }, (_, index) => {
      const bucket = Math.floor((index / 64) * data.length);
      return Math.abs(data[bucket] - 128) / 128;
    });
    setWaveform(normalised);
    animationRef.current = requestAnimationFrame(updateWaveform);
  }, []);

  const start = useCallback(async () => {
    setError(undefined);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone access is not supported in this browser.');
      setPermission('denied');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      setPermission('granted');
      const audioContext = new AudioContext({ sampleRate });
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      analyserRef.current = analyser;
      updateWaveform();
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.start();
      setRecording(true);
    } catch (err) {
      setPermission('denied');
      setError(err instanceof Error ? err.message : 'Unable to access microphone');
      teardown();
    }
  }, [sampleRate, teardown, updateWaveform]);

  const stop = useCallback(async (): Promise<Blob | null> => {
    if (!recorderRef.current) {
      return null;
    }
    setProcessing(true);
    const recorder = recorderRef.current;
    const audioContext = audioContextRef.current;
      return await new Promise<Blob | null>((resolve) => {
        const handleStop = async (): Promise<void> => {
        recorder.removeEventListener('stop', handleStop);
        setRecording(false);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        chunksRef.current = [];
        if (!audioContext) {
          teardown();
          setProcessing(false);
          resolve(blob);
          return;
        }
        try {
          const arrayBuffer = await blob.arrayBuffer();
          const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
          const wavBlob = audioBufferToWav(audioBuffer);
          teardown();
          setProcessing(false);
          resolve(wavBlob);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unable to process audio');
          teardown();
          setProcessing(false);
          resolve(null);
        }
      };
      recorder.addEventListener('stop', handleStop, { once: true });
      recorder.stop();
    });
  }, [teardown]);

  const reset = useCallback((): void => {
    teardown();
    setRecording(false);
    setProcessing(false);
    setWaveform([]);
    setError(undefined);
    setPermission('idle');
  }, [teardown]);

  return {
    permission,
    recording,
    processing,
    waveform,
    error,
    start,
    stop,
    reset,
  };
}
