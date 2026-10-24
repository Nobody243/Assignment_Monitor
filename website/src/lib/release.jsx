import React, { createContext, useContext, useEffect, useState } from "react";

export const REPO = "Nobody243/Assignment_Monitor";
export const REPO_URL = `https://github.com/${REPO}`;
const FALLBACK = {
  version: __APP_VERSION__,
  setupUrl: `${REPO_URL}/releases/latest/download/AssignmentMonitor-Setup.exe`,
  zipUrl: `${REPO_URL}/releases/latest/download/AssignmentMonitor-portable.zip`,
  setupSize: null, zipSize: null, publishedAt: null,
  pageUrl: `${REPO_URL}/releases/latest`,
  loaded: false,
};

const Ctx = createContext(FALLBACK);
export const fmtMB = (b) => (b ? `${Math.round(b / 1048576)} MB` : "");
export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "recently");

/* The newest numbered release: version, asset links and sizes. The release build writes /latest.json into the site
   itself, so the normal path makes no request to anyone but this site. GitHub's API is only the fallback (it allows
   60 unauthenticated requests an hour per address), and below that the "latest" download URLs, which GitHub
   redirects to the same files, so every button works whatever happens. */
export function ReleaseProvider({ children }) {
  const [rel, setRel] = useState(FALLBACK);
  useEffect(() => {
    let alive = true;
    const apply = (next) => { if (alive) setRel({ ...FALLBACK, ...next, loaded: true }); };
    const fromApi = () => fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((j) => {
        const setup = (j.assets || []).find((a) => /-setup\.exe$/i.test(a.name));
        const zip = (j.assets || []).find((a) => /-portable\.zip$/i.test(a.name));
        apply({
          version: (j.tag_name || "").replace(/^v/i, "") || FALLBACK.version,
          setupUrl: setup ? setup.browser_download_url : FALLBACK.setupUrl,
          zipUrl: zip ? zip.browser_download_url : FALLBACK.zipUrl,
          setupSize: setup ? setup.size : null, zipSize: zip ? zip.size : null,
          publishedAt: j.published_at || null, pageUrl: j.html_url || FALLBACK.pageUrl,
        });
      });
    fetch("/latest.json", { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((j) => {
        if (!j || !j.version) throw new Error("empty");
        apply({
          version: j.version, setupUrl: j.setup_url || FALLBACK.setupUrl, zipUrl: j.zip_url || FALLBACK.zipUrl,
          setupSize: j.setup_size || null, zipSize: j.zip_size || null,
          publishedAt: j.published_at || null, pageUrl: j.page_url || FALLBACK.pageUrl,
        });
      })
      .catch(() => fromApi().catch(() => {}));
    return () => { alive = false; };
  }, []);
  return <Ctx.Provider value={rel}>{children}</Ctx.Provider>;
}

export const useRelease = () => useContext(Ctx);
