const SHELL = "aip-shell-v1", API = "aip-api-v1";
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(["/", "/manifest.webmanifest", "/icon.svg"])));
  self.skipWaiting();
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== SHELL && k !== API).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (u.pathname.startsWith("/api/") && !u.pathname.includes("/auth/")) {
    // stale-while-revalidate
    e.respondWith(caches.open(API).then(async (c) => {
      const cached = await c.match(e.request);
      const net = fetch(e.request).then((r) => { if (r && r.status === 200) c.put(e.request, r.clone()); return r; }).catch(() => cached);
      return cached || net;
    }));
  } else if (u.origin === location.origin) {
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
  }
});
