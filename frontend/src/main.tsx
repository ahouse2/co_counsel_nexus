import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { SettingsProvider } from './context/SettingsContext';
import { QueryProvider } from './context/QueryContext';
import { ScenarioProvider } from './context/ScenarioContext';
import { DevTeamProvider } from './context/DevTeamContext';
import './styles/index.css';
import { registerServiceWorker } from './utils/serviceWorkerRegistration';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <SettingsProvider>
      <QueryProvider>
        <ScenarioProvider>
          <DevTeamProvider>
            <App />
          </DevTeamProvider>
        </ScenarioProvider>
      </QueryProvider>
    </SettingsProvider>
  </React.StrictMode>
);

registerServiceWorker();
