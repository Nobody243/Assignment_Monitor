/* Assignment Monitor service worker.
   1. Offline page: pages are always fetched from the network (nothing of the site is cached, so a new deploy is
      never served stale); only when the network fails does a page navigation get /offline.html instead.
   2. Phone alerts: shows the pushes the desktop app sends and opens the right place on tap. */
const CACHE = "am-offline-v1";
const OFFLINE = "/offline.html";
const PRECACHE = [OFFLINE, "/offline.js", "/assets/logo.svg",
  "/assets/fonts/inter-latin-wght-normal.woff2", "/assets/fonts/jetbrains-mono-latin-500-normal.woff2"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match(OFFLINE)));
    return;
  }
  // the offline page's own files come from the cache when the network is gone; everything else is untouched
  const url = new URL(req.url);
  if (url.origin === self.location.origin && url.search === "" && PRECACHE.includes(url.pathname)) {
    e.respondWith(fetch(req).catch(() => caches.match(url.pathname)));
  }
});

self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data ? e.data.json() : {}; } catch { data = { body: e.data ? e.data.text() : "" }; }
  const title = data.title || "Assignment Monitor";
  e.waitUntil(self.registration.showNotification(title, {
    body: data.body || "",
    icon: "/assets/logo-192.png",
    badge: "/assets/logo-192.png",
    tag: data.tag || "assignment-monitor",
    renotify: true,
    data: { url: data.url || "https://lms.bahria.edu.pk/Student/Dashboard.php" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
    for (const c of list) { if (c.url === url && "focus" in c) return c.focus(); }
    return self.clients.openWindow(url);
  }));
});

self.addEventListener("pushsubscriptionchange", (e) => {
  // the browser rotated the subscription; the phone has to be paired again from the app
  e.waitUntil(self.registration.showNotification("Assignment Monitor", {
    body: "Your phone's push address changed. Open the app on your PC and pair the phone again.",
    icon: "/assets/logo-192.png", tag: "am-resubscribe",
  }));
});
