/* Assignment Monitor phone alerts: shows the pushes the desktop app sends and opens the right place on tap. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

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
