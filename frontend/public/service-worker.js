/* Sage PWA service worker — app-shell caching + offline fallback.
 *
 * Strategy:
 *   - navigations: network-first, fall back to cached index.html when offline.
 *   - same-origin static GETs (JS/CSS/img/font): stale-while-revalidate.
 *   - API calls live on a different origin and non-GETs are never cached.
 */
const CACHE = "sage-v1";
const SHELL = [
  "/", "/index.html", "/manifest.json",
  "/favicon.ico", "/logo192.png", "/logo512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // don't touch the API origin

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put("/index.html", copy));
          return resp;
        })
        .catch(() => caches.match("/index.html"))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((resp) => {
          if (resp && resp.status === 200) {
            const copy = resp.clone();
            caches.open(CACHE).then((c) => c.put(request, copy));
          }
          return resp;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});

/* Web push is wired in a later step; the listener is here so the SW is ready. */
self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = {}; }
  const title = data.title || "Sage";
  const options = {
    body: data.body || "",
    icon: "/logo192.png",
    badge: "/logo192.png",
    data: data.url || "/",
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow(event.notification.data || "/"));
});
