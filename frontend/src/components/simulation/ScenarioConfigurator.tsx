import { FormEvent, useMemo, useState } from 'react';
import { useScenario } from '@/context/ScenarioContext';

export function ScenarioConfigurator(): JSX.Element {
  const {
    state,
    selectScenario,
    updateParticipant,
    updateVariable,
    updateEvidence,
    toggleTTS,
    updateCaseId,
    runScenario,
    previewVoice,
  } = useScenario();
  const [voiceSample, setVoiceSample] = useState('The court is now in session.');

  const selectedScenario = state.scenario;
  const participantLookup = useMemo(() => {
    const byId: Record<string, string> = {};
    const byVoice: Record<string, string> = {};
    state.scenario?.participants.forEach((participant) => {
      byId[participant.id] = participant.name;
      if (participant.voice) {
        byVoice[participant.voice] = participant.name;
      }
    });
    return { byId, byVoice };
  }, [state.scenario]);

  const handleScenarioChange = async (event: FormEvent<HTMLSelectElement>): Promise<void> => {
    const value = event.currentTarget.value;
    if (!value) {
      return;
    }
    await selectScenario(value);
  };

  const handleRun = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    await runScenario();
  };

  const handlePreview = async (participantId: string): Promise<void> => {
    await previewVoice(participantId, voiceSample);
  };

  const metadataMessage = useMemo(() => {
    switch (state.metadataStatus) {
      case 'loading':
        return 'Loading scenarios…';
      case 'error':
        return state.metadataError ?? 'Unable to load scenarios.';
      case 'loaded':
        return `${state.metadata.length} scenario${state.metadata.length === 1 ? '' : 's'} available.`;
      default:
        return 'Browse scenarios to begin.';
    }
  }, [state.metadataStatus, state.metadataError, state.metadata.length]);

  return (
    <form className="scenario-config" onSubmit={handleRun} aria-live="polite">
      <header className="scenario-config__header">
        <div>
          <h2>Simulation Configuration</h2>
          <p>{metadataMessage}</p>
        </div>
        <div className="scenario-config__tts">
          <label>
            <input
              type="checkbox"
              checked={state.configuration.enableTTS}
              onChange={(event) => toggleTTS(event.currentTarget.checked)}
            />
            Enable voice synthesis
          </label>
          <label className="scenario-config__case">
            Case ID
            <input
              type="text"
              value={state.configuration.caseId}
              onChange={(event) => updateCaseId(event.currentTarget.value)}
              placeholder="Enter case identifier"
            />
          </label>
        </div>
      </header>

      <section className="scenario-config__section">
        <h3>Scenario</h3>
        <label className="scenario-config__select">
          <span className="sr-only">Select scenario</span>
          <select
            value={selectedScenario?.scenario_id ?? ''}
            onChange={handleScenarioChange}
            disabled={state.metadataStatus !== 'loaded'}
          >
            <option value="" disabled>
              {state.metadataStatus === 'loading' ? 'Loading scenarios…' : 'Choose a scenario'}
            </option>
            {state.metadata.map((scenario) => (
              <option key={scenario.scenario_id} value={scenario.scenario_id}>
                {scenario.title} — {scenario.difficulty}
              </option>
            ))}
          </select>
        </label>
        {selectedScenario ? (
          <div className="scenario-config__summary">
            <p>{selectedScenario.description}</p>
            <ul className="scenario-config__tags">
              {selectedScenario.tags.map((tag) => (
                <li key={tag}>{tag}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {state.scenarioStatus === 'error' ? (
          <p className="scenario-config__error">{state.scenarioError}</p>
        ) : null}
      </section>

      {selectedScenario ? (
        <>
          <section className="scenario-config__section">
            <h3>Participants</h3>
            <div className="scenario-config__grid">
              {selectedScenario.participants.map((participant) => (
                <label key={participant.id} className="scenario-config__card">
                  <span className="scenario-config__card-header">
                    <input
                      type="checkbox"
                      checked={state.configuration.participants[participant.id] ?? false}
                      onChange={(event) => updateParticipant(participant.id, event.currentTarget.checked)}
                    />
                    <strong>{participant.name}</strong>
                  </span>
                  <small>{participant.role}</small>
                  <p>{participant.description}</p>
                  <div className="scenario-config__card-actions">
                    <button
                      type="button"
                      onClick={() => handlePreview(participant.id)}
                      disabled={!participant.voice}
                    >
                      Preview voice
                    </button>
                    <span className="scenario-config__accent" style={{ backgroundColor: participant.accent_color }} />
                  </div>
                </label>
              ))}
            </div>
          </section>

          <section className="scenario-config__section">
            <h3>Variables</h3>
            <div className="scenario-config__stack">
              {Object.entries(selectedScenario.variables).map(([key, variable]) => (
                <label key={key}>
                  <span>
                    {variable.name} {variable.required ? <span className="required">*</span> : null}
                  </span>
                  <input
                    type="text"
                    value={state.configuration.variables[key] ?? ''}
                    onChange={(event) => updateVariable(key, event.currentTarget.value)}
                    placeholder={variable.description}
                    required={variable.required}
                  />
                </label>
              ))}
            </div>
          </section>

          <section className="scenario-config__section">
            <h3>Evidence</h3>
            <div className="scenario-config__stack">
              {selectedScenario.evidence.map((spec) => (
                <div key={spec.id} className="scenario-config__evidence">
                  <label>
                    <span>
                      {spec.label} {spec.required ? <span className="required">*</span> : null}
                    </span>
                    <input
                      type="text"
                      value={state.configuration.evidence[spec.id]?.value ?? ''}
                      onChange={(event) =>
                        updateEvidence(
                          spec.id,
                          event.currentTarget.value,
                          state.configuration.evidence[spec.id]?.document_id ?? spec.document_id ?? undefined
                        )
                      }
                      placeholder={spec.description ?? 'Reference or exhibit'}
                      required={spec.required}
                    />
                  </label>
                  <label>
                    <span>Document ID (optional)</span>
                    <input
                      type="text"
                      value={state.configuration.evidence[spec.id]?.document_id ?? ''}
                      onChange={(event) =>
                        updateEvidence(spec.id, state.configuration.evidence[spec.id]?.value ?? '', event.currentTarget.value)
                      }
                      placeholder="doc-123"
                    />
                  </label>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : null}

      <section className="scenario-config__section">
        <h3>Voice Preview</h3>
        <div className="scenario-config__preview">
          <label>
            <span>Sample text</span>
            <input type="text" value={voiceSample} onChange={(event) => setVoiceSample(event.currentTarget.value)} />
          </label>
          {state.voicePreview ? (
            <audio
              controls
              src={`data:${state.voicePreview.mime_type};base64,${state.voicePreview.base64}`}
              aria-label={`Preview voice for ${
                participantLookup.byVoice[state.voicePreview.voice] ?? participantLookup.byId[state.voicePreview.voice] ?? state.voicePreview.voice
              }`}
            />
          ) : (
            <p className="scenario-config__preview-hint">Generate a preview to audit the selected voice.</p>
          )}
        </div>
      </section>

      <footer className="scenario-config__footer">
        {state.runError ? <p className="scenario-config__error">{state.runError}</p> : null}
        <button type="submit" disabled={state.running || !selectedScenario}>
          {state.running ? 'Running simulation…' : 'Run simulation'}
        </button>
      </footer>
    </form>
  );
}
