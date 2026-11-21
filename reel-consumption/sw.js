// Reel Consumption — minimal service worker (no caching; data always live from Supabase).
// Needed only so the app can be installed on the phone home screen.
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;           // RPC POST calls go straight to the network
  e.respondWith(fetch(e.request));
});
