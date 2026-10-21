import React, { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { SectionHead } from "../Reveal.jsx";
import { FEATURES } from "../../data/content.js";
import { coarsePointer } from "../../lib/scroll.jsx";
import { EASE } from "../../lib/motion.js";

/* Ten features in a carousel instead of a ten-card wall: three cards per view on desktop, two on tablets, one and a
   bit on phones. Native scroll-snap does the swiping; the arrows, dots and keyboard do the rest. */
function Card({ f, i }) {
  const onMove = (e) => {
    if (coarsePointer()) return;
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`); e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
  };
  return (
    <motion.article className="card" onPointerMove={onMove} initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }} transition={{ duration: 0.7, ease: EASE, delay: (i % 3) * 0.07 }}>
      <p className="mono">{f.n} · {f.tag}</p>
      <h3>{f.title}</h3>
      <p>{f.text}</p>
      {f.datestr && <div className="datestr"><span className="now">{f.datestr.now}</span><s>{f.datestr.was}</s></div>}
      {f.list && <ul>{f.list.map(([k, v]) => <li key={k}>{k} <span>{v}</span></li>)}</ul>}
    </motion.article>
  );
}

export default function Features() {
  const track = useRef(null);
  const [page, setPage] = useState(0);
  const [pages, setPages] = useState(1);

  const measure = useCallback(() => {
    const el = track.current; if (!el) return;
    const max = el.scrollWidth - el.clientWidth;
    const n = Math.max(1, Math.ceil(el.scrollWidth / el.clientWidth - 0.02));
    setPages(n);
    setPage(el.scrollLeft >= max - 2 ? n - 1 : Math.min(n - 1, Math.round(el.scrollLeft / el.clientWidth)));
  }, []);
  useEffect(() => {
    measure();
    const el = track.current;
    el.addEventListener("scroll", measure, { passive: true });
    window.addEventListener("resize", measure);
    return () => { el.removeEventListener("scroll", measure); window.removeEventListener("resize", measure); };
  }, [measure]);
  const go = (p) => { const el = track.current; if (!el) return; el.scrollTo({ left: Math.max(0, Math.min(pages - 1, p)) * el.clientWidth, behavior: "smooth" }); };
  const onKey = (e) => { if (e.key === "ArrowRight") { e.preventDefault(); go(page + 1); } if (e.key === "ArrowLeft") { e.preventDefault(); go(page - 1); } };

  return (
    <section id="features">
      <div className="wrap">
        <div className="feat-head">
          <SectionHead kicker="What it does" title={<>Small tool. <span className="heading-accent">Does the boring part.</span></>}
            lede="It does on your PC exactly what you would do by hand in a browser, on a schedule, and tells you only what matters." />
          <div className="feat-nav" aria-hidden={pages <= 1}>
            <button type="button" className="feat-arrow" onClick={() => go(page - 1)} disabled={page === 0} aria-label="Previous features">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6" /></svg>
            </button>
            <button type="button" className="feat-arrow" onClick={() => go(page + 1)} disabled={page >= pages - 1} aria-label="Next features">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6" /></svg>
            </button>
          </div>
        </div>
        <div className="feat-track" ref={track} tabIndex={0} onKeyDown={onKey} role="region" aria-label="Features, swipe or use the arrow keys">
          {FEATURES.map((f, i) => <Card f={f} i={i} key={f.n} />)}
        </div>
        <div className="feat-dots" role="tablist" aria-label="Feature pages">
          {Array.from({ length: pages }, (_, i) => (
            <button key={i} type="button" role="tab" aria-selected={i === page} aria-label={`Page ${i + 1}`} onClick={() => go(i)} />
          ))}
        </div>
      </div>
    </section>
  );
}
