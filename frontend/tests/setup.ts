import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

if (typeof globalThis.Worker === 'undefined') {
  class MockWorker {
    onmessage: ((this: Worker, ev: MessageEvent) => void) | null = null;
    onerror: ((this: Worker, ev: ErrorEvent) => void) | null = null;
    constructor() {}
    postMessage(): void {}
    terminate(): void {}
    addEventListener(): void {}
    removeEventListener(): void {}
    dispatchEvent(): boolean {
      return true;
    }
  }
  vi.stubGlobal('Worker', MockWorker as unknown as typeof Worker);
}
