import React, { useEffect, useState } from "react";
import { LINKS } from "../data/content.js";

/* The crash page. Static markup on purpose: it must draw even when the motion library, the router or the planet is
   what failed. Reload and Home are full page loads so nothing of the broken state survives. */
const describe = (error) => {
  if (!error) return "Unknown error";
  const msg = error.message || String(error);
  const stack = (error.stack || "").split("\n").slice(0, 6).join("\n");
  return stack && !stack.startsWith(msg) ? `${msg}\n${stack}` : stack || msg;
};

export default function Broken({ error, bare = false }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => { document.title = "Something went wrong · Assignment Monitor"; }, []);
  const details = describe(error);
  const where = typeof window !== "undefined" ? window.location.pathname + window.location.search : "";
  const stale = /dynamically imported module|Loading chunk|import\(\)|Failed to fetch/i.test(details);
  const report = `${LINKS.issues}/new?title=${encodeURIComponent(`Website: page crashed on ${where || "/"}`)}&body=${encodeURIComponent(
    `**Page:** ${where}\n**Site version:** ${__APP_VERSION__}\n**Browser:** ${typeof navigator !== "undefined" ? navigator.userAgent : ""}\n\n\`\`\`\n${details}\n\`\`\`\n\nWhat I was doing:\n`)}`;
  const copy = () => {
    navigator.clipboard?.writeText(`${where}\n${details}`).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); }).catch(() => {});
  };
  return (
    <div className={`err${bare ? " err-bare" : ""}`}>
      <section className="page-hero err-hero">
        <div className="wrap">
          <div>
            <p className="eyebrow mono">Something went wrong</p>
            <h1>This page <span className="heading-accent">crashed.</span></h1>
            <p className="lede">
              {stale
                ? "The site was updated while this tab was open, and the old page tried to load a file that no longer exists. A reload fixes it."
                : "An error stopped the page from drawing. Nothing of yours was affected; this site keeps no account and stores nothing."}
            </p>
            <div className="page-hero-actions">
              <button type="button" className="btn btn-accent btn-lg" onClick={() => window.location.reload()}>Reload the page</button>
              <a href="/" className="btn btn-ghost btn-lg">Back home</a>
            </div>
          </div>
        </div>
      </section>
      <section className="err-body">
        <div className="wrap">
          <div className="err-card">
            <div className="err-card-head">
              <div>
                <p className="mono">What the browser said</p>
                <h2 className="h-md">Still broken after a reload? Send this.</h2>
              </div>
              <div className="err-actions">
                <button type="button" className="btn btn-quiet btn-sm" onClick={copy} aria-live="polite">{copied ? "Copied" : "Copy details"}</button>
                <a className="btn btn-ghost btn-sm" href={report} target="_blank" rel="noopener">Report on GitHub</a>
              </div>
            </div>
            <pre className="err-pre" tabIndex={0}>{details}</pre>
            <p className="err-note">The report opens a pre-filled issue in the public repository: the page address, the site version, your browser name and the lines above. Nothing else.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
