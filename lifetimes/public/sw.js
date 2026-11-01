// Lifetimes service worker: makes the game installable and playable offline.
// The game shell is cached; /api calls (store, unlocks, chat) always go to the network
// and are never cached, so chat and purchases are never served stale.
// Bump VERSION on every release so players pick up the new files.
const VERSION = 'lt-v4';
const SHELL = [
  '/', '/index.html', '/style.css', '/sfx.js', '/content.js', '/game.js', '/manifest.webmanifest',
  '/icons/icon-192.png', '/icons/icon-512.png', '/icons/apple-touch-icon.png',
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  // Pages: network first so an online player always gets the newest build; cache when offline.
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).then((r) => { const copy = r.clone(); caches.open(VERSION).then((c) => c.put('/', copy)); return r; })
      .catch(() => caches.match('/')));
    return;
  }
  // Static files: cache first, refreshed in the background.
  e.respondWith(caches.match(e.request).then((hit) => {
    const net = fetch(e.request).then((r) => { if (r.ok) { const copy = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, copy)); } return r; });
    return hit || net;
  }));
});
