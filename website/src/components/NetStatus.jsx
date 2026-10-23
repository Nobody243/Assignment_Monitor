import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

/* A small pill at the foot of the window while the browser is offline, and a brief "back online" when it returns.
   Pages that are already open keep working; downloads and the release lookup simply wait. */
export default function NetStatus() {
  const [state, setState] = useState(() => (typeof navigator !== "undefined" && navigator.onLine === false ? "off" : "on"));
  const [flash, setFlash] = useState(false);
  useEffect(() => {
    let t = 0;
    const off = () => { clearTimeout(t); setFlash(false); setState("off"); };
    const on = () => { setState("on"); setFlash(true); clearTimeout(t); t = setTimeout(() => setFlash(false), 2600); };
    window.addEventListener("offline", off); window.addEventListener("online", on);
    return () => { window.removeEventListener("offline", off); window.removeEventListener("online", on); clearTimeout(t); };
  }, []);
  const show = state === "off" || flash;
  return (
    <AnimatePresence>
      {show && (
        <motion.div key={state} className={`net ${state === "off" ? "is-off" : "is-on"}`} role="status" aria-live="polite"
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}>
          <i aria-hidden="true" />
          {state === "off" ? <span>You're offline. This page still works; downloads will wait.</span> : <span>Back online.</span>}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
