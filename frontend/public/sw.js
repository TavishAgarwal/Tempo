// Cache-first map tile cache so the demo zone works offline after one online visit.
const CACHE = "tiles-v1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.hostname !== "tile.openstreetmap.org") return;
  e.respondWith(
    caches.open(CACHE).then(async (c) => {
      const hit = await c.match(e.request);
      if (hit) return hit;
      try {
        const r = await fetch(e.request);
        if (r.ok) c.put(e.request, r.clone());
        return r;
      } catch {
        return hit ?? Response.error();
      }
    }),
  );
});
