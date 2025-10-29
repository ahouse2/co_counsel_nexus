import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export interface SimulationManifestCharacter {
  sprite: string;
  accentColor: string;
}

export interface SimulationManifestStage {
  width: number;
  height: number;
  background: string;
  characterPositions: Record<string, { x: number; y: number }>;
}

export interface SimulationManifest {
  version: number;
  stage: SimulationManifestStage;
  characters: Record<string, SimulationManifestCharacter>;
}

interface SimulationAssetState {
  manifest: SimulationManifest | null;
  status: 'idle' | 'loading' | 'loaded' | 'error';
  error?: string;
}

export function useSimulationAssets(): SimulationAssetState & { reload: () => void } {
  const [state, setState] = useState<SimulationAssetState>({ manifest: null, status: 'idle' });
  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    if (typeof window === 'undefined') {
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ manifest: null, status: 'loading' });
    try {
      const response = await fetch('/simulations/manifest.json', { signal: controller.signal });
      if (!response.ok) {
        throw new Error(`Manifest fetch failed (${response.status})`);
      }
      const payload = (await response.json()) as SimulationManifest;
      setState({ manifest: payload, status: 'loaded' });
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        return;
      }
      setState({ manifest: null, status: 'error', error: (error as Error).message });
    }
  }, []);

  useEffect(() => {
    if (state.status === 'idle') {
      load();
    }
    return () => {
      abortRef.current?.abort();
    };
  }, [load, state.status]);

  const reload = useCallback(() => {
    setState((current) => ({ ...current, status: 'idle' }));
  }, []);

  return useMemo(
    () => ({
      manifest: state.manifest,
      status: state.status,
      error: state.error,
      reload,
    }),
    [state.error, state.manifest, state.status, reload]
  );
}
