/* Jarvis service worker — makes the dashboard installable + offline-tolerant.
 *
 * Strategy (deliberately conservative to avoid the classic "why am I seeing old
 * data" PWA footgun):
 *   - Static shell (HTML/CSS/JS/icons): NETWORK-FIRST. Always fresh when online;
 *     falls back to the cached copy only when the network is unreachable.
 *   - /api/* : NEVER cached. Always network. Data is never served stale.
 *
 * Bump SHELL_CACHE when the shell files change to evict the old cache.
 */
const SHELL_CACHE = "jarvis-shell-v3";
const SHELL_ASSETS = [
  "/",
  "/static/style.css",
  "/static/app.js",
  "/manifest.webmanifest",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((c) => c.addAll(SHELL_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL_CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Only handle our own origin; ignore everything else.
  if (url.origin !== self.location.origin) return;

  // Never touch API calls — always live, never cached.
  if (url.pathname.startsWith("/api/")) return;

  // Only GETs are cacheable.
  if (req.method !== "GET") return;

  // Network-first for the shell; cache is the offline fallback only.
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match("/")))
  );
});
