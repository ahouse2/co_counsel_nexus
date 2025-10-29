import { useEffect, useState } from 'react';

export function OfflineIndicator(): JSX.Element {
  const [online, setOnline] = useState(() => navigator.onLine);

  useEffect((): (() => void) => {
    const update = (): void => setOnline(navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  return (
    <span className={`offline-indicator ${online ? 'online' : 'offline'}`} role="status" aria-live="polite">
      {online ? 'Online' : 'Offline — responses will queue'}
    </span>
  );
}
