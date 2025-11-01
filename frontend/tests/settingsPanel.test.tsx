import { describe, expect, it, beforeEach, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SettingsPanel } from '@/components/SettingsPanel';

const mockResolvedModels = {
  chat: {
    providerId: 'gemini',
    model: {
      id: 'gemini-2.5-flash',
      display_name: 'Gemini 2.5 Flash',
      capabilities: ['chat', 'vision'],
      modalities: ['text', 'vision'],
      context_window: 1_000_000,
      availability: 'general-cloud',
    },
  },
  embeddings: {
    providerId: 'gemini',
    model: {
      id: 'text-embedding-004',
      display_name: 'Text Embedding 004',
      capabilities: ['embeddings'],
      modalities: ['text'],
      context_window: 8_192,
      availability: 'general-cloud',
    },
  },
  vision: {
    providerId: 'gemini',
    model: {
      id: 'gemini-2.5-flash',
      display_name: 'Gemini 2.5 Flash',
      capabilities: ['vision', 'chat'],
      modalities: ['text', 'vision'],
      context_window: 1_000_000,
      availability: 'general-cloud',
    },
  },
};

const providerCatalog = [
  {
    id: 'gemini',
    display_name: 'Google Gemini',
    capabilities: ['chat', 'embeddings', 'vision'],
    models: [mockResolvedModels.chat.model, mockResolvedModels.embeddings.model],
  },
  {
    id: 'openai',
    display_name: 'OpenAI',
    capabilities: ['chat', 'embeddings', 'vision'],
    models: [
      {
        id: 'gpt-5.0',
        display_name: 'GPT-5.0',
        capabilities: ['chat', 'vision'],
        modalities: ['text'],
        context_window: 128_000,
        availability: 'general-cloud',
      },
      {
        id: 'text-embedding-3-large',
        display_name: 'Text Embedding 3 Large',
        capabilities: ['embeddings'],
        modalities: ['text'],
        context_window: 8_192,
        availability: 'general-cloud',
      },
    ],
  },
];

let updateSettingsMock: ReturnType<typeof vi.fn>;
let setThemePreferenceMock: ReturnType<typeof vi.fn>;
let contextValue: any;

vi.mock('@/context/SettingsContext', () => ({
  useSettingsContext: () => contextValue,
}));

beforeEach(() => {
  updateSettingsMock = vi.fn(async () => undefined);
  setThemePreferenceMock = vi.fn(async () => undefined);
  contextValue = {
    loading: false,
    saving: false,
    error: undefined,
    settings: {
      providers: {
        primary: 'gemini',
        secondary: null,
        defaults: {
          chat: 'gemini-2.5-flash',
          embeddings: 'text-embedding-004',
          vision: 'gemini-2.5-flash',
        },
        api_base_urls: {},
        local_runtime_paths: {},
        available: providerCatalog,
      },
      credentials: {
        providers: [
          { provider_id: 'gemini', has_api_key: false },
          { provider_id: 'openai', has_api_key: true },
        ],
        services: { courtlistener: false, research_browser: true },
      },
      appearance: { theme: 'system' },
      updated_at: null,
    },
    catalog: providerCatalog,
    resolvedModels: mockResolvedModels,
    themePreference: 'system',
    refresh: vi.fn(),
    updateSettings: updateSettingsMock,
    setThemePreference: setThemePreferenceMock,
  };
});

describe('SettingsPanel', () => {
  it('opens panel and lists current provider selection', () => {
    render(<SettingsPanel />);
    fireEvent.click(screen.getByRole('button', { name: /settings/i }));
    expect(screen.getByLabelText(/Primary provider/i)).toHaveValue('gemini');
    expect(screen.getByLabelText(/Secondary provider/i)).toHaveValue('');
  });

  it('submits provider changes', async () => {
    render(<SettingsPanel />);
    fireEvent.click(screen.getByRole('button', { name: /settings/i }));
    fireEvent.change(screen.getByLabelText(/Primary provider/i), { target: { value: 'openai' } });
    fireEvent.change(screen.getByLabelText(/Chat model/i), { target: { value: 'gpt-5.0' } });
    fireEvent.click(screen.getByRole('button', { name: /Save provider preferences/i }));
    await waitFor(() =>
      expect(updateSettingsMock).toHaveBeenCalledWith(
        expect.objectContaining({
          providers: expect.objectContaining({
            primary: 'openai',
            defaults: expect.objectContaining({ chat: 'gpt-5.0' }),
          }),
        })
      )
    );
  });

  it('updates theme preference from appearance tab', () => {
    render(<SettingsPanel />);
    fireEvent.click(screen.getByRole('button', { name: /settings/i }));
    fireEvent.click(screen.getByRole('button', { name: /Appearance/i }));
    fireEvent.click(screen.getByLabelText(/Light/i));
    expect(setThemePreferenceMock).toHaveBeenCalledWith('light');
  });
});
