import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import Lenis from "lenis";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
export const coarsePointer = () => window.matchMedia("(hover: none), (pointer: coarse)").matches;

const Ctx = createContext({ lenis: null, scrollTo: () => {}, stop: () => {}, start: () => {}, velocity: { current: 0 } });

/* One Lenis instance for the whole app, driven by GSAP's ticker so ScrollTrigger and smooth scrolling share a clock. */
export function ScrollProvider({ children }) {
  const [lenis, setLenis] = useState(null);
  const velocity = useRef(0);
  useEffect(() => {
    if (reduceMotion()) return undefined;
    const l = new Lenis({ lerp: 0.085, smoothWheel: true, wheelMultiplier: 0.9, touchMultiplier: 1.2 });
    l.on("scroll", (e) => { velocity.current = e.velocity; ScrollTrigger.update(); });
    const tick = (t) => l.raf(t * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    setLenis(l); window.__lenis = l;
    return () => { gsap.ticker.remove(tick); l.destroy(); setLenis(null); };
  }, []);
  const api = useMemo(() => ({
    lenis,
    velocity,
    scrollTo: (target, opts = {}) => {
      if (lenis) lenis.scrollTo(target, { offset: -72, ...opts });
      else if (typeof target === "number") window.scrollTo({ top: target, behavior: opts.immediate ? "auto" : "smooth" });
      else { const el = typeof target === "string" ? document.querySelector(target) : target; if (el) el.scrollIntoView({ behavior: opts.immediate ? "auto" : "smooth", block: "start" }); }
    },
    stop: () => { if (lenis) lenis.stop(); },
    start: () => { if (lenis) lenis.start(); },
  }), [lenis]);
  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
}

export const useScroll = () => useContext(Ctx);
export { gsap, ScrollTrigger };
