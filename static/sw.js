/* Offline shell for Spotify Stats.

   Static assets are cached and served cache-first. Pages are always fetched
   from the network — listening stats must be live — with a cached offline
   notice as the fallback when the network is unavailable. */

var CACHE = 'spotifystats-v2';
var PRECACHE = [
  '/static/css/app.css',
  '/static/js/app.js',
  '/static/icons/icon.svg',
  '/static/manifest.webmanifest',
  '/offline'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE)
      .then(function (cache) { return cache.addAll(PRECACHE); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.map(function (key) {
          return key === CACHE ? null : caches.delete(key);
        }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  var request = event.request;
  if (request.method !== 'GET') return;

  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // Never cache API responses or the OAuth round trip.
  if (url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/callback') ||
      url.pathname.startsWith('/login')) return;

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then(function (hit) {
        return hit || fetch(request).then(function (response) {
          if (response.ok) {
            var copy = response.clone();
            caches.open(CACHE).then(function (c) { c.put(request, copy); });
          }
          return response;
        });
      })
    );
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(function () {
        return caches.match('/offline');
      })
    );
  }
});
