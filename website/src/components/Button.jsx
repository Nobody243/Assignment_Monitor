import React from "react";
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

/* The download buttons always point straight at the release asset, so a click starts the file, nothing else. */
export function DownloadButton({ kind = "setup", size = "md", variant, showSize = true, label, className }) {
  const rel = useRelease();
  const isSetup = kind === "setup";
  const href = isSetup ? rel.setupUrl : rel.zipUrl;
  const bytes = isSetup ? rel.setupSize : rel.zipSize;
  return (
    <Button href={href} variant={variant || (isSetup ? "accent" : "ghost")} size={size} className={className} data-download={kind}>
      {isSetup && <DownloadIcon />}
      {label || (isSetup ? "Download for Windows" : "Portable zip")}
      {showSize && <small>{isSetup ? `v${rel.version}` : ""}{isSetup && bytes ? " · " : ""}{fmtMB(bytes)}</small>}
    </Button>
  );
}
