import { useEffect } from "react";

const BASE = "Assignment Monitor";
const SITE = "https://assignment-monitor.saaddev.top";

function setMeta(selector, attr, value) {
  let el = document.head.querySelector(selector);
  if (!el) {
    el = document.createElement(selector.startsWith("link") ? "link" : "meta");
    const m = selector.match(/\[(\w+(?::\w+)?)="([^"]+)"\]/);
    if (m) el.setAttribute(m[1], m[2]);
    document.head.appendChild(el);
  }
  el.setAttribute(attr, value);
}

/* Per-page title, description, canonical and the social tags that mirror them. The static tags in index.html
   are what link previews see (they do not run scripts); these keep rendered crawlers and the address bar right.
   options.noindex marks a page (the 404) as not worth indexing. */
export function usePageMeta(title, description, options = {}) {
  useEffect(() => {
    const full = title ? `${title} · ${BASE}` : `${BASE} — never miss a Bahria LMS deadline`;
    document.title = full;
    const path = window.location.pathname.replace(/\/+$/, "") || "/";
    const url = SITE + (path === "/" ? "/" : path);
    if (description) setMeta('meta[name="description"]', "content", description);
    setMeta('link[rel="canonical"]', "href", url);
    setMeta('meta[property="og:url"]', "content", url);
    setMeta('meta[property="og:title"]', "content", full);
    setMeta('meta[name="twitter:title"]', "content", full);
    if (description) {
      setMeta('meta[property="og:description"]', "content", description);
      setMeta('meta[name="twitter:description"]', "content", description);
    }
    setMeta('meta[name="robots"]', "content", options.noindex ? "noindex, follow" : "index, follow, max-image-preview:large");
  }, [title, description, options.noindex]);
}
