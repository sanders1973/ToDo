self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open('shiny-app-cache').then(function(cache) {
      return cache.addAll([
        '/',
        '/index.html',
        '/shinylive/style-resets.css',
        '/shinylive/shinylive.css',
        '/shinylive/load-shinylive-sw.js',
        '/shinylive/shinylive.js',
        'icons/icon-192x192.png',
        'icons/icon-512x512.png'
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
