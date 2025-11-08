import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useVoiceSession } from '@/hooks/useVoiceSession';
import type { VoiceSessionResponse } from '@/types';
import { createVoiceSession, fetchVoicePersonas, fetchVoiceSession } from '@/utils/apiClient';

vi.mock('@/utils/apiClient', () => ({
  fetchVoicePersonas: vi.fn(),
  createVoiceSession: vi.fn(),
  fetchVoiceSession: vi.fn(),
}));

class MockAudio {
  public static playSpy = vi.fn();
  public static pauseSpy = vi.fn();
  public static lastInstance: MockAudio | null = null;

  public src = '';
  public currentTime = 0;
  private listeners: Record<string, () => void> = {};
  constructor(src?: string) {
    if (src) {
      this.src = src;
    }
    MockAudio.lastInstance = this;
  }

  async play(): Promise<void> {
    MockAudio.playSpy();
    return Promise.resolve();
  }

  pause(): void {
    MockAudio.pauseSpy();
  }

  addEventListener(event: string, handler: () => void): void {
    this.listeners[event] = handler;
  }

  removeEventListener(event: string): void {
    delete this.listeners[event];
  }

  trigger(event: string): void {
    this.listeners[event]?.();
  }
}
  describe('useVoiceSession', () => {
  beforeEach(() => {
    vi.mocked(fetchVoicePersonas).mockResolvedValue([
      { persona_id: 'aurora', label: 'Aurora', description: 'Warm', speaker_id: 'p1' },
      { persona_id: 'atlas', label: 'Atlas', description: 'Calm', speaker_id: 'p2' },
    ]);
    vi.mocked(createVoiceSession).mockReset();
    vi.mocked(fetchVoiceSession).mockReset();
    MockAudio.playSpy.mockReset();
    MockAudio.pauseSpy.mockReset();
    MockAudio.lastInstance = null;
    globalThis.Audio = MockAudio as unknown as typeof globalThis.Audio;
  });

  it('loads personas and submits a session', async () => {
    const response = {
      
      
      
      
      translation: "",persona_shifts: [],sentiment_arc: [],persona_directive: "",session_id: 'session-1',
      thread_id: 'thread-1',
      case_id: 'CASE-1',
      persona_id: 'aurora',
      transcript: 'Question?',
      assistant_text: 'Answer',
      audio_url: '/voice/sessions/session-1/response',
      sentiment: { label: 'neutral', score: 0.5, pace: 1.0 },
      segments: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as unknown as VoiceSessionResponse;vi.mocked(createVoiceSession).mockResolvedValue(response);
    vi.mocked(fetchVoiceSession).mockResolvedValue({ ...response, voice_memory: {} });

    const { result } = renderHook(() => useVoiceSession());

    await waitFor(() => expect(result.current.personas).toHaveLength(2));
    expect(result.current.selectedPersona).toBe('aurora');

    const blob = new Blob(['abc'], { type: 'audio/wav' });
    await act(async () => {
      await result.current.submit({ caseId: 'CASE-1', audio: blob });
    });

    expect(createVoiceSession).toHaveBeenCalledTimes(1);
    const [[formData]] = vi.mocked(createVoiceSession).mock.calls as [[FormData]];
    const entries = Array.from((formData as any).entries()) as [string, any][];
    expect(entries).toEqual(
      expect.arrayContaining([
        ['case_id', 'CASE-1'],
        ['persona_id', 'aurora'],
      ])
    );
    const audioEntry = entries.find(([key]) => key === 'audio') as [string, any] | undefined;
expect(audioEntry?.[1]).toBeInstanceOf(Blob);
    expect(result.current.session?.assistant_text).toBe('Answer');
    expect(fetchVoiceSession).toHaveBeenCalledWith('session-1');
    expect(MockAudio.lastInstance?.src).toBe('/voice/sessions/session-1/response');

    await act(async () => {
      result.current.play();
    });
    expect(MockAudio.playSpy).toHaveBeenCalled();
    expect(result.current.playing).toBe(true);

    act(() => {
      result.current.stop();
    });
    expect(MockAudio.pauseSpy).toHaveBeenCalled();
    expect(result.current.playing).toBe(false);
  });
});




