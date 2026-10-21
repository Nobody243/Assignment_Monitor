import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useRelease, fmtMB } from "../lib/release.jsx";

const cx = (...a) => a.filter(Boolean).join(" ");

/* One button for links, routes and actions. variant: accent | primary | ghost | quiet. size: md | lg | sm. */
export function Button({ variant = "ghost", size = "md", to, href, external, className, children, ...rest }) {
  const cls = cx("btn", `btn-${variant}`, size !== "md" && `btn-${size}`, className);
  if (to) return <Link to={to} className={cls} {...rest}>{children}</Link>;
  if (href) return <a href={href} className={cls} {...(external ? { target: "_blank", rel: "noopener" } : {})} {...rest}>{children}</a>;
  return <button type="button" className={cls} {...rest}>{children}</button>;
}

const DownloadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 3v12m0 0 4-4m-4 4-4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" /></svg>
);

/* Where each option lives on the download page; every "Download" button on the site goes there first. */
export const DOWNLOAD_PATH = { setup: "/download#installer", zip: "/download#zip" };

/* A download button. By default it only takes you to the download page (nothing is fetched until you choose there),
   which is how the big vendors do it: one explicit click on the file, never a surprise download.
   With `direct`, it points at the release asset itself and guards against double clicks: after a click it reads
   "Download started" and ignores further clicks for a few seconds. */
export function DownloadButton({ kind = "setup", size = "md", variant, showSize = true, label, className, direct = false }) {
  const rel = useRelease();
  const [started, setStarted] = useState(false);
  const timer = useRef(0);
  useEffect(() => () => clearTimeout(timer.current), []);
  const isSetup = kind === "setup";
  const bytes = isSetup ? rel.setupSize : rel.zipSize;
  const v = variant || (isSetup ? "accent" : "ghost");
  const text = label || (isSetup ? "Download for Windows" : "Portable zip");
  const meta = showSize && <small>{isSetup ? `v${rel.version}` : ""}{isSetup && bytes ? " · " : ""}{fmtMB(bytes)}</small>;
  if (!direct) {
    return (
      <Button to={DOWNLOAD_PATH[kind]} variant={v} size={size} className={className} data-download-page={kind}>
        {isSetup && <DownloadIcon />}{text}{meta}
      </Button>
    );
  }
  const onClick = (e) => {
    if (started) { e.preventDefault(); return; }
    setStarted(true);
    clearTimeout(timer.current); timer.current = setTimeout(() => setStarted(false), 6000);
  };
  return (
    <Button href={isSetup ? rel.setupUrl : rel.zipUrl} variant={v} size={size} className={cx(className, started && "is-started")}
      data-download={kind} aria-live="polite" aria-disabled={started || undefined} onClick={onClick}>
      {isSetup && <DownloadIcon />}{started ? "Download started" : text}{!started && meta}
    </Button>
  );
}
