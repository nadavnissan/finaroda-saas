/* FINARODA minimal service worker (Stage 8 PWA baseline).
 *
 * Scope: a graceful offline fallback for top-level navigations ONLY. It precaches
 * one static page (/offline.html) and serves it when a navigation request fails
 * (device offline). It does NOT cache app HTML/JS/CSS/API responses, so it can never
 * serve a stale version of the app — every real request goes to the network. No push,
 * no background sync, no offline data. "Installable app", not an offline product.
 */
const OFFLINE_URL = "/offline.html";
const CACHE = "finaroda-offline-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.add(OFFLINE_URL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  // Only intercept top-level navigations; all other requests hit the network directly.
  if (request.mode !== "navigate") return;
  event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
});
