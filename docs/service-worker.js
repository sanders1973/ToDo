self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open('shiny-app-cache').then(function(cache) {
      return cache.addAll([
        '/docs/',
        '/docs/index.html',
        '/docs/shinylive/style-resets.css',
        '/docs/shinylive/shinylive.css',
        '/docs/shinylive/load-shinylive-sw.js',
        '/docs/shinylive/shinylive.js',
        '/docs/icons/icon-192x192.png',
        '/docs/icons/icon-512x512.png'
      ]);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    })
  );
});
