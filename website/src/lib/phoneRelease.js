import { useEffect, useState } from "react";
import { REPO, REPO_URL } from "./release.jsx";

/* The newest phone app release (tags phone-vX.Y.Z share this repository with the desktop ones). The page works with
   the fallback below even when GitHub's API cannot be reached; the API only brings the version and size up to date. */
const FALLBACK = {
  version: "1.0.13",
  apkUrl: `${REPO_URL}/releases/download/phone-v1.0.13/AssignmentMonitor-phone.apk`,
  pageUrl: `${REPO_URL}/releases/tag/phone-v1.0.13`,
  size: null, publishedAt: null,
};

export function usePhoneRelease() {
  const [rel, setRel] = useState(FALLBACK);
  useEffect(() => {
    let alive = true;
    fetch(`https://api.github.com/repos/${REPO}/releases?per_page=20`, { headers: { Accept: "application/vnd.github+json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((list) => {
        const num = (x) => x.tag_name.replace(/^phone-v/, "").split(".").reduce((n, p) => n * 1000 + (parseInt(p, 10) || 0), 0);
        // the list is not always newest first, so take the highest version number
        const j = (list || []).filter((x) => /^phone-v\d/.test(x.tag_name) && !x.prerelease && !x.draft).sort((a, b) => num(b) - num(a))[0];
        const apk = j && (j.assets || []).find((a) => /\.apk$/i.test(a.name));
        if (alive && j && apk) setRel({ version: j.tag_name.replace(/^phone-v/, ""), apkUrl: apk.browser_download_url, pageUrl: j.html_url, size: apk.size, publishedAt: j.published_at });
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);
  return rel;
}
