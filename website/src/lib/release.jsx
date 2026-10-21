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

/* The newest numbered GitHub release: version, asset links and sizes. Falls back to the "latest" download URLs,
   which GitHub redirects to the same files, so every button works even if the API is rate-limited. */
export function ReleaseProvider({ children }) {
  const [rel, setRel] = useState(FALLBACK);
  useEffect(() => {
    let alive = true;
    fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((j) => {
        if (!alive) return;
        const setup = (j.assets || []).find((a) => /-setup\.exe$/i.test(a.name));
        const zip = (j.assets || []).find((a) => /-portable\.zip$/i.test(a.name));
        setRel({
          version: (j.tag_name || "").replace(/^v/i, "") || FALLBACK.version,
          setupUrl: setup ? setup.browser_download_url : FALLBACK.setupUrl,
          zipUrl: zip ? zip.browser_download_url : FALLBACK.zipUrl,
          setupSize: setup ? setup.size : null, zipSize: zip ? zip.size : null,
          publishedAt: j.published_at || null, pageUrl: j.html_url || FALLBACK.pageUrl, loaded: true,
        });
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);
  return <Ctx.Provider value={rel}>{children}</Ctx.Provider>;
}

export const useRelease = () => useContext(Ctx);
