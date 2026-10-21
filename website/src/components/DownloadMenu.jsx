import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useRelease, fmtMB } from "../lib/release.jsx";
import { IS_WINDOWS } from "../lib/platform.js";
import { SendToPc } from "./SendToPc.jsx";
import { DOWNLOAD_PATH } from "./Button.jsx";
import { EASE } from "../lib/motion.js";

const Chevron = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
);

/* The nav's Download button. On Windows it opens a small chooser: installer (recommended), portable zip, and a link
   to the guide for the difference. Elsewhere it becomes "Send to PC". */
export default function DownloadMenu() {
  const rel = useRelease();
  const [open, setOpen] = useState(false);
  const root = useRef(null);
  const { pathname } = useLocation();
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => { if (root.current && !root.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", onDoc); document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("pointerdown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  if (!IS_WINDOWS) return <SendToPc size="md" variant="primary" className="nav-send" short />;

  const close = () => setOpen(false);
  return (
    <div className="dl-menu" ref={root}>
      <button type="button" className="btn btn-primary" aria-haspopup="menu" aria-expanded={open} aria-controls="dl-menu-list" onClick={() => setOpen((v) => !v)}>
        Download <small>v{rel.version}</small><Chevron />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div id="dl-menu-list" className="dl-pop" role="menu" aria-label="Download options"
            initial={{ opacity: 0, y: -6, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6, scale: 0.98 }} transition={{ duration: 0.22, ease: EASE }}>
            <Link role="menuitem" className="dl-row is-rec" to={DOWNLOAD_PATH.setup} data-download-page="setup" onClick={close}>
              <span className="dl-row-t">Installer <span className="pill">Recommended</span></span>
              <span className="dl-row-m mono">v{rel.version}{rel.setupSize ? ` · ${fmtMB(rel.setupSize)}` : ""} · Setup.exe</span>
            </Link>
            <Link role="menuitem" className="dl-row" to={DOWNLOAD_PATH.zip} data-download-page="zip" onClick={close}>
              <span className="dl-row-t">Portable zip</span>
              <span className="dl-row-m mono">{rel.zipSize ? `${fmtMB(rel.zipSize)} · ` : ""}no installer</span>
            </Link>
            <Link role="menuitem" className="dl-row dl-row-link" to="/download" onClick={close}>What is the difference?</Link>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
