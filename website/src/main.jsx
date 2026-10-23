import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import "lenis/dist/lenis.css";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";
import "./styles/sections.css";
import "./styles/pages.css";
import "./styles/states.css";
import "./styles/intro.css";

/* A deploy while a tab is open leaves it pointing at bundle names that no longer exist; Vite reports the failed
   lazy import as vite:preloadError. One reload per minute fixes it; if that also fails, the crash page says why. */
window.addEventListener("vite:preloadError", (e) => {
  let last = 0;
  try { last = Number(sessionStorage.getItem("am-reload") || 0); } catch { /* storage blocked */ }
  if (Date.now() - last < 60000) return;
  try { sessionStorage.setItem("am-reload", String(Date.now())); } catch { /* storage blocked */ }
  e.preventDefault();
  window.location.reload();
});

/* The service worker serves /offline.html when a page cannot be fetched (and shows phone pushes). It caches
   nothing of the site itself, so every visit still gets the current deploy. */
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => { navigator.serviceWorker.register("/sw.js").catch(() => {}); });
}

createRoot(document.getElementById("root")).render(
  <ErrorBoundary bare>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </ErrorBoundary>,
);
