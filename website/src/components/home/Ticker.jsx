import React, { useEffect, useRef } from "react";
import { gsap, useScroll, reduceMotion } from "../../lib/scroll.jsx";
import { TICKER } from "../../data/content.js";

/* A slow marquee that speeds up with scroll velocity. */
export default function Ticker() {
  const track = useRef(null);
  const { velocity } = useScroll();
  useEffect(() => {
    if (reduceMotion()) return undefined;
    const tween = gsap.to(track.current, { xPercent: -50, duration: 38, ease: "none", repeat: -1 });
    const speed = gsap.quickTo(tween, "timeScale", { duration: 0.6 });
    const tick = () => speed(1 + Math.min(Math.abs(velocity.current || 0) / 12, 5));
    gsap.ticker.add(tick);
    return () => { gsap.ticker.remove(tick); tween.kill(); };
  }, [velocity]);
  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker-track" ref={track}>
        {[...TICKER, ...TICKER].map((t, i) => <span key={i}>{t}</span>)}
      </div>
    </div>
  );
}
