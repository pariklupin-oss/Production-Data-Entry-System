// Starish Production — minimal service worker (no caching; data always live from SQL)
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;           // POST / RPC calls go straight to the network
  e.respondWith(fetch(e.request));
});
