import { useEffect, useState } from "react";
import { REPO, REPO_URL } from "./release.jsx";

/* The newest phone app release (tags phone-vX.Y.Z share this repository with the desktop ones). The page works with
   the fallback below even when GitHub's API cannot be reached; the API only brings the version and size up to date. */
const FALLBACK = {
  version: "1.0.13",
  apkUrl: `${REPO_URL}/releases/download/phone-v1.0.13/AssignmentMonitor-phone.apk`,
  pageUrl: `${REPO_URL}/releases/tag/phone-v1.0.13`,
  size: null, publishedAt: null, shaUrl: null,
};

export function usePhoneRelease() {
  const [rel, setRel] = useState(FALLBACK);
  useEffect(() => {
    let alive = true;
    const apply = (next) => { if (alive) setRel({ ...FALLBACK, ...next }); };
    // GitHub's API allows 60 requests an hour per address, which a campus network can use up; it is only the fallback
    const fromApi = () => fetch(`https://api.github.com/repos/${REPO}/releases?per_page=20`, { headers: { Accept: "application/vnd.github+json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((list) => {
        const num = (x) => x.tag_name.replace(/^phone-v/, "").split(".").reduce((n, p) => n * 1000 + (parseInt(p, 10) || 0), 0);
        // the list is not always newest first, so take the highest version number
        const j = (list || []).filter((x) => /^phone-v\d/.test(x.tag_name) && !x.prerelease && !x.draft).sort((a, b) => num(b) - num(a))[0];
        const apk = j && (j.assets || []).find((a) => /\.apk$/i.test(a.name));
        const sha = j && (j.assets || []).find((a) => /\.sha256$/i.test(a.name));
        if (j && apk) apply({ version: j.tag_name.replace(/^phone-v/, ""), apkUrl: apk.browser_download_url, pageUrl: j.html_url, size: apk.size, publishedAt: j.published_at, shaUrl: sha ? sha.browser_download_url : null });
      });
    // the release build writes /phone.json into the site itself, so the normal path asks nobody but this site
    fetch("/phone.json", { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((j) => {
        if (!j || !j.version || !j.apk_url) throw new Error("empty");
        apply({ version: j.version, apkUrl: j.apk_url, pageUrl: j.page_url || FALLBACK.pageUrl, size: j.apk_size || null, publishedAt: j.published_at || null, shaUrl: j.sha_url || null });
      })
      .catch(() => fromApi().catch(() => {}));
    return () => { alive = false; };
  }, []);
  return rel;
}
