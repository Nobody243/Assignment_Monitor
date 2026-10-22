import React, { useEffect, useRef, useState } from "react";
import { Window } from "../Reveal.jsx";
import { TOUR, shot } from "../../data/content.js";
import { reduceMotion } from "../../lib/scroll.jsx";

/* Phone and tablet tour, the same idea as the desktop one: the whole dashboard stays in view with a spotlight that
   glides to the part each step talks about, and the step captions sit in a swipeable row under it. It walks through
   the steps by itself while it is on screen until you swipe or tap; arrows and dots move it too. */
const DWELL = 5200;
const Arrow = ({ d }) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>;

export default function TourMobile() {
  const section = useRef(null), track = useRef(null);
  const [active, setActive] = useState(0);
  const [auto, setAuto] = useState(() => typeof window === "undefined" || !reduceMotion());
  const visible = useRef(false);

  // which caption is centred in the row
  useEffect(() => {
    const el = track.current; if (!el) return undefined;
    const cards = Array.from(el.children);
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting && e.intersectionRatio > 0.6) setActive(cards.indexOf(e.target)); });
    }, { root: el, threshold: [0.6] });
    cards.forEach((c) => io.observe(c));
    return () => io.disconnect();
  }, []);
  useEffect(() => {
    const el = section.current; if (!el) return undefined;
    const io = new IntersectionObserver(([e]) => { visible.current = e.isIntersecting; }, { threshold: 0.35 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  const go = (i) => {
    // scroll the caption row itself; scrollIntoView would also drag the page sideways for the last card
    const el = track.current, card = el?.children[(i + TOUR.length) % TOUR.length];
    if (!el || !card) return;
    const left = card.offsetLeft - (el.clientWidth - card.offsetWidth) / 2;
    el.scrollTo({ left: Math.max(0, Math.min(left, el.scrollWidth - el.clientWidth)), behavior: "smooth" });
  };
  // auto-advance while on screen, until the first touch
  useEffect(() => {
    if (!auto) return undefined;
    const id = setInterval(() => { if (visible.current && !document.hidden) go(active + 1); }, DWELL);
    return () => clearInterval(id);
  }, [auto, active]);
  const stop = () => setAuto(false);

  const step = TOUR[active];
  const [sx, sy, sw, sh] = step.spot;
  return (
    <section id="story" className="story story-m" ref={section}>
      <div className="wrap">
        <div className="story-head">
          <p className="mono">Tour</p>
          <h2>One screen tells you <span className="heading-accent">what's due.</span></h2>
        </div>
        <Window title="Dashboard" className="tour-m-win">
          <div className="shot-body">
            <img src={shot("dashboard", "light")} alt="The dashboard in the light theme" width="1280" height="840" loading="lazy" />
            <div className="spot" style={{ "--sx": `${sx}%`, "--sy": `${sy}%`, "--sw": `${sw}%`, "--sh": `${sh}%` }} />
            <span className="spot-label" style={{ "--sx": `${sx}%`, "--sy": `${sy}%` }}>{step.label}</span>
          </div>
        </Window>
      </div>
      <div className="tour-m-track" ref={track} role="list" aria-label="Tour steps" onPointerDown={stop} onTouchStart={stop}>
        {TOUR.map((s, i) => (
          <article className={`tour-m-card${i === active ? " is-active" : ""}`} key={s.title} role="listitem">
            <p className="mono">{String(i + 1).padStart(2, "0")} / {String(TOUR.length).padStart(2, "0")} · {s.label}</p>
            <h3>{s.title}</h3>
            <p>{s.text}</p>
          </article>
        ))}
      </div>
      <div className="tour-m-nav">
        <button type="button" className="feat-arrow" onClick={() => { stop(); go(active - 1); }} aria-label="Previous step"><Arrow d="M15 6l-6 6 6 6" /></button>
        <div className="tour-m-dots" role="tablist" aria-label="Tour step">
          {TOUR.map((s, i) => <button key={s.title} type="button" role="tab" aria-selected={i === active} aria-label={`Step ${i + 1}`} onClick={() => { stop(); go(i); }} />)}
        </div>
        <button type="button" className="feat-arrow" onClick={() => { stop(); go(active + 1); }} aria-label="Next step"><Arrow d="M9 6l6 6-6 6" /></button>
      </div>
    </section>
  );
}
