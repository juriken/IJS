/**
 * IdolJapan.store — Progressive Web App Service Worker
 * Strategy: Cache-First for static assets, Stale-While-Revalidate for catalog payloads, Offline UI Fallback
 */

const CACHE_NAME = 'idoljapan-cache-v20261108104353';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/css/custom.css',
  '/js/config.js',
  '/js/drawers.js',
  '/js/mega-menu.js',
  '/js/search.js',
  '/js/app.js',
  '/js/analytics.js',
  '/js/db.js',
  '/js/geo_currency.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Guard: Let all third-party CDNs and cross-origin APIs bypass the Service Worker completely
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  const url = new URL(event.request.url);

  // Stale-While-Revalidate for dynamic JSON catalog and rate payloads
  if (url.pathname.endsWith('catalog-index.json') || url.pathname.endsWith('products.json') || url.pathname.endsWith('rates.json')) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cachedResponse = await cache.match(event.request);
        const fetchPromise = fetch(event.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            cache.put(event.request, networkResponse.clone());
          }
          return networkResponse;
        }).catch(() => cachedResponse);

        return cachedResponse || fetchPromise;
      })
    );
    return;
  }

  // HTML page navigation fallback for offline mode
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(async () => {
        const cache = await caches.open(CACHE_NAME);
        return await cache.match('/index.html');
      })
    );
    return;
  }

  // Cache-first strategy for local static styles and scripts
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
          return networkResponse;
        }
        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        return networkResponse;
      });
    })
  );
});