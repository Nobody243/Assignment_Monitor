import React, { useEffect, useRef, useState } from "react";
import { Button } from "./Button.jsx";
import { CAN_SHARE, SHARE } from "../lib/platform.js";

const ShareIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 3v13m0-13-4 4m4-4 4 4M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" /></svg>
);

/* "Send to your PC": the native share sheet where there is one, otherwise the link goes to the clipboard.
   The link is the download page, not the installer file, so the PC side lands on the guide. */
export function SendToPc({ size = "md", variant = "accent", className, short = false }) {
  const [state, setState] = useState("idle");
  const timer = useRef(0);
  useEffect(() => () => clearTimeout(timer.current), []);
  const flash = (s) => { setState(s); clearTimeout(timer.current); timer.current = setTimeout(() => setState("idle"), 2400); };
  const onClick = async () => {
    if (CAN_SHARE) {
      try { await navigator.share(SHARE); return; } catch (e) { if (e && e.name === "AbortError") return; }
    }
    try { await navigator.clipboard.writeText(SHARE.url); flash("copied"); }
    catch { window.prompt("Copy this link and open it on your PC:", SHARE.url); }
  };
  const label = state === "copied" ? "Link copied" : short ? "Send to PC" : "Send to your PC";
  return (
    <Button variant={variant} size={size} className={className} onClick={onClick} data-send="pc" aria-live="polite">
      <ShareIcon />{label}
    </Button>
  );
}
