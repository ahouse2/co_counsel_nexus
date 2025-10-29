import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { QueryProvider } from './context/QueryContext';
import './styles/index.css';
import { registerServiceWorker } from './utils/serviceWorkerRegistration';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <QueryProvider>
      <App />
    </QueryProvider>
  </React.StrictMode>
);

registerServiceWorker();
