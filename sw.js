/* CruiseNight service worker.
   BUMP CACHE ON EVERY DEPLOY or installed phones keep serving the old app.
   POSTERS is deliberately never bumped, so posters survive a deploy. */
const CACHE = 'cn-v5';
const POSTERS = 'cn-posters-v1';

const SHELL = [
  './',
  './index.html',
  './config.js',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png'
];
// Pinned, integrity-checked libraries: safe to keep forever under this cache name.
const LIB_HOSTS = ['unpkg.com', 'cdn.jsdelivr.net'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => Promise.all(SHELL.map(url =>
      cache.add(new Request(url, { cache: 'reload' })).catch(err => console.warn('[sw] could not precache', url, err))
    )))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(n => n !== CACHE && n !== POSTERS).map(n => caches.delete(n)));
    await self.clients.claim();
  })());
});

self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

async function cacheFirst(cacheName, req) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  if (hit) return hit;
  try {
    const res = await fetch(req);
    if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone());
    return res;
  } catch (err) {
    return Response.error();
  }
}

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Posters from Supabase Storage: cache-first. A path is never overwritten
  // (replacements get a new name), so a cached copy is never stale.
  if (url.pathname.includes('/storage/v1/object/public/posters/')) {
    event.respondWith(cacheFirst(POSTERS, req));
    return;
  }

  if (LIB_HOSTS.includes(url.hostname)) {
    event.respondWith(cacheFirst(CACHE, req));
    return;
  }

  // Navigations and config.js: network-first so a deploy or a key change is
  // picked up, falling back to the cached copy offline.
  if (req.mode === 'navigate' || (url.origin === self.location.origin && url.pathname.endsWith('/config.js'))) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      try {
        // no-cache: revalidate with the server, so the browser's HTTP cache
        // (10 min on GitHub Pages) can't hand back a stale page or config.
        const res = await fetch(req.url, { cache: 'no-cache', credentials: 'same-origin' });
        if (res.ok) cache.put(req.mode === 'navigate' ? './index.html' : req, res.clone());
        return res;
      } catch (err) {
        return (await cache.match(req.mode === 'navigate' ? './index.html' : req)) ||
               (await cache.match('./')) ||
               new Response('Offline and no cached copy of STLCruiseNight.', { status: 503, headers: { 'Content-Type': 'text/plain' } });
      }
    })());
    return;
  }

  if (url.origin === self.location.origin) {
    event.respondWith(cacheFirst(CACHE, req));
  }
  // Everything else (Supabase API, map tiles, geocoding) goes to the network untouched.
});
