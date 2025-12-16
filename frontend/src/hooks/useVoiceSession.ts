import { useState, useRef, useEffect, useCallback } from 'react';
import { endpoints } from '../services/api';

export interface VoiceSessionState {
    status: 'idle' | 'listening' | 'processing' | 'speaking' | 'error';
    error?: string;
    transcript?: string;
    audioLevel: number; // 0-100 for visualization
}

export function useVoiceSession(caseId: string, personaId: string = 'default') {
    const [state, setState] = useState<VoiceSessionState>({
        status: 'idle',
        audioLevel: 0
    });
    const [sessionId, setSessionId] = useState<string | null>(null);

    const mediaRecorder = useRef<MediaRecorder | null>(null);
    const audioContext = useRef<AudioContext | null>(null);
    const analyser = useRef<AnalyserNode | null>(null);
    const audioChunks = useRef<Blob[]>([]);
    const animationFrame = useRef<number>();

    const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
    const [audioSource, setAudioSource] = useState<AudioNode | null>(null);

    // Initialize Audio Context
    const initAudioContext = async () => {
        if (!audioContext.current) {
            audioContext.current = new (window.AudioContext || (window as any).webkitAudioContext)();
            analyser.current = audioContext.current.createAnalyser();
            analyser.current.fftSize = 512;
        }
        if (audioContext.current.state === 'suspended') {
            await audioContext.current.resume();
        }
    };

    const updateAudioLevel = () => {
        if (!analyser.current) return;

        const dataArray = new Uint8Array(analyser.current.frequencyBinCount);
        analyser.current.getByteFrequencyData(dataArray);

        // Calculate average volume
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setState(prev => ({ ...prev, audioLevel: average }));

        animationFrame.current = requestAnimationFrame(updateAudioLevel);
    };

    const startListening = useCallback(async () => {
        try {
            await initAudioContext();
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setAudioStream(stream);

            // Connect mic stream to analyser
            const source = audioContext.current!.createMediaStreamSource(stream);
            // Disconnect previous source if any
            if (audioSource) {
                // audioSource.disconnect(); // Logic to handle disconnection might be needed
            }
            source.connect(analyser.current!);
            setAudioSource(source);

            mediaRecorder.current = new MediaRecorder(stream);
            audioChunks.current = [];

            mediaRecorder.current.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.current.push(event.data);
                }
            };

            mediaRecorder.current.onstop = async () => {
                const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
                await processAudio(audioBlob);

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
                setAudioStream(null);
            };

            mediaRecorder.current.start();
            setState(prev => ({ ...prev, status: 'listening', error: undefined }));
            updateAudioLevel();

        } catch (err) {
            console.error("Microphone access denied:", err);
            setState(prev => ({ ...prev, status: 'error', error: "Microphone access denied" }));
        }
    }, [caseId, personaId]);

    const stopListening = useCallback(() => {
        if (mediaRecorder.current && mediaRecorder.current.state !== 'inactive') {
            mediaRecorder.current.stop();
            if (animationFrame.current) cancelAnimationFrame(animationFrame.current);
            setState(prev => ({ ...prev, status: 'processing', audioLevel: 0 }));
        }
    }, []);

    const processAudio = async (audioBlob: Blob) => {
        try {
            // Ensure session exists
            let currentSessionId = sessionId;
            if (!currentSessionId) {
                const res = await endpoints.voice.createSession(caseId, personaId);
                currentSessionId = res.data.session_id;
                setSessionId(currentSessionId);
            }

            if (!currentSessionId) throw new Error("Failed to create session");

            // Send audio
            const response = await endpoints.voice.processTurn(currentSessionId, audioBlob);

            // Play response using Web Audio API
            await playResponse(response.data);

        } catch (err) {
            console.error("Voice processing failed:", err);
            setState(prev => ({ ...prev, status: 'error', error: "Failed to process voice" }));
        }
    };

    const playResponse = async (audioData: Blob) => {
        if (!audioContext.current) await initAudioContext();

        const arrayBuffer = await audioData.arrayBuffer();
        const audioBuffer = await audioContext.current!.decodeAudioData(arrayBuffer);

        const source = audioContext.current!.createBufferSource();
        source.buffer = audioBuffer;

        // Connect to analyser for lip sync
        source.connect(analyser.current!);
        // Connect to destination (speakers)
        analyser.current!.connect(audioContext.current!.destination);

        source.onended = () => {
            setState(prev => ({ ...prev, status: 'idle' }));
            if (animationFrame.current) cancelAnimationFrame(animationFrame.current);
        };

        source.start(0);
        setState(prev => ({ ...prev, status: 'speaking' }));
        updateAudioLevel(); // Restart visualization for playback
    };

    const cancel = useCallback(() => {
        if (audioContext.current) {
            audioContext.current.suspend();
        }
        if (mediaRecorder.current && mediaRecorder.current.state !== 'inactive') {
            mediaRecorder.current.stop();
        }
        setState(prev => ({ ...prev, status: 'idle', error: undefined }));
    }, []);

    useEffect(() => {
        return () => {
            if (animationFrame.current) cancelAnimationFrame(animationFrame.current);
            if (audioContext.current) audioContext.current.close();
        };
    }, []);

    return {
        state,
        startListening,
        stopListening,
        cancel,
        audioContext: audioContext.current, // Expose context if needed
        analyser: analyser.current // Expose analyser for Avatar
    };
}
