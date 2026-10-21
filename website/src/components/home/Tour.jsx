import React, { useEffect, useRef, useState } from "react";
import { gsap, ScrollTrigger, useScroll, reduceMotion } from "../../lib/scroll.jsx";
import { useScene } from "../../lib/scene.jsx";
import { Window } from "../Reveal.jsx";
import { TOUR } from "../../data/content.js";

/* Pinned walkthrough: the dashboard stays put while four short scroll steps move a spotlight over it and swap the
   caption. Desktop only; on narrow screens the steps simply stack under the screenshot. */
export default function Tour() {
  const section = useRef(null), pin = useRef(null);
  const [active, setActive] = useState(0);
  const triggerRef = useRef(null);
  const { scrollTo } = useScroll();
  const { introDone } = useScene();
  const desktop = typeof window !== "undefined" && window.matchMedia("(min-width: 901px)").matches;

  useEffect(() => {
    if (!desktop || reduceMotion()) return undefined;
    const perStep = () => Math.round(window.innerHeight * 0.42);
    const st = ScrollTrigger.create({
      trigger: section.current, start: "top top", end: () => "+=" + perStep() * TOUR.length, pin: pin.current, pinSpacing: true,
      anticipatePin: 1, scrub: 0.35,
      onUpdate: (self) => setActive(Math.min(TOUR.length - 1, Math.floor(self.progress * TOUR.length))),
    });
    triggerRef.current = st;
    const img = section.current.querySelector("img");
    const refresh = () => ScrollTrigger.refresh();
    if (img && !img.complete) img.addEventListener("load", refresh, { once: true });
    return () => { st.kill(); triggerRef.current = null; };
  }, [desktop]);
  useEffect(() => { if (introDone) setTimeout(() => ScrollTrigger.refresh(), 80); }, [introDone]);

  const go = (i) => {
    const st = triggerRef.current; if (!st) return;
    const perStep = Math.round(window.innerHeight * 0.42);
    scrollTo(st.start + perStep * i + perStep * 0.5, { offset: 0, duration: 1 });
  };
  const step = TOUR[active];
  const [sx, sy, sw, sh] = step.spot;
  return (
    <section id="story" className="story" ref={section}>
      <div className="story-pin" ref={pin}>
        <div className="wrap">
          <div className="story-head">
            <span className="mono">Tour</span>
            <h2>Back on the ground: <span className="serif accent">what's next?</span></h2>
          </div>
          <div className="story-grid">
            <div className="story-visual">
              <Window title="Dashboard" className="shot">
                <img src="/assets/shot-dashboard-light.png" alt="The dashboard in the light theme" width="1280" height="840" loading="lazy" />
                <div className="spot" style={{ "--sx": `${sx}%`, "--sy": `${sy}%`, "--sw": `${sw}%`, "--sh": `${sh}%` }} />
                <div className="spot-label" style={{ "--sx": `${sx}%`, "--sy": `${sy}%` }}>{step.label}</div>
              </Window>
            </div>
            <div className="story-side">
              <ol className="story-rail" aria-label="Tour steps">
                {TOUR.map((_, i) => (
                  <li key={i} className={i === active ? "is-active" : i < active ? "is-past" : ""}>
                    <button type="button" onClick={() => go(i)} aria-label={`Step ${i + 1}`} aria-current={i === active ? "step" : undefined}>{String(i + 1).padStart(2, "0")}</button>
                  </li>
                ))}
              </ol>
              <div className="story-track">
                {TOUR.map((s, i) => (
                  <article key={s.title} className={`story-step${i === active ? " is-active" : i < active ? " is-past" : ""}`} aria-hidden={desktop && i !== active}>
                    <span className="mono">{String(i + 1).padStart(2, "0")} / {String(TOUR.length).padStart(2, "0")}</span>
                    <h3>{s.title}</h3><p>{s.text}</p>
                  </article>
                ))}
              </div>
              <p className={`story-hint mono${active === TOUR.length - 1 ? " is-done" : ""}`}>Scroll to continue</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
