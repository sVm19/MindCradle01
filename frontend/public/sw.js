const CACHE_NAME = 'mindcradle-cache-v2';

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll([
        '/',
        '/index.html',
        '/mindcradle-logo.svg',
        '/mindcradle-icon-192.png',
        '/mindcradle-icon-512.png',
        '/favicon.svg',
        '/mindcradle-favicon.svg'
      ]);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  // Only handle GET requests and HTTP/HTTPS protocols
  if (event.request.method !== 'GET' || !event.request.url.startsWith('http')) {
    return;
  }

  // Network-First for navigation (HTML page) to ensure client gets the latest built files
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseClone);
          });
          return response;
        })
        .catch(() => {
          return caches.match(event.request) || caches.match('/index.html');
        })
    );
    return;
  }

  // Cache-First for static assets with fetch fallback
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request).catch(error => {
        console.warn(`[Service Worker] Fetch failed for ${event.request.url}:`, error);
        return new Response('Network error occurred', { status: 408, statusText: 'Network Error' });
      });
    })
  );
});
