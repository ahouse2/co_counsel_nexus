const CORE_VERSION = 'v1.0.0';
const CORE_CACHE = `cocounsel-core-${CORE_VERSION}`;
const DATA_CACHE = `cocounsel-data-${CORE_VERSION}`;
const CORE_ASSETS = ['/', '/index.html', '/manifest.webmanifest'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CORE_CACHE).then((cache) => cache.addAll(CORE_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith('cocounsel-') && key !== CORE_CACHE && key !== DATA_CACHE)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);
  if (url.origin === self.location.origin && (url.pathname === '/' || url.pathname.startsWith('/assets'))){
    event.respondWith(cacheFirst(request));
    return;
  }

  if (url.pathname.startsWith('/timeline') || url.pathname.startsWith('/query')) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }
});

async function cacheFirst(request) {
  const cache = await caches.open(CORE_CACHE);
  const cached = await cache.match(request, { ignoreVary: true, ignoreSearch: true });
  if (cached) {
    return cached;
  }
  const response = await fetch(request);
  cache.put(request, response.clone());
  return response;
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(DATA_CACHE);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request)
    .then((response) => {
      if (response && response.status === 200) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);
  return cached ? Promise.resolve(cached) : fetchPromise;
}
