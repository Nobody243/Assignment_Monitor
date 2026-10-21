import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { SectionHead } from "../Reveal.jsx";
import { FEATURES } from "../../data/content.js";

/* Ten features on a wheel that behaves like a fidget spinner. The cards stand on a 3D ring; a small physics loop turns
   it: a slow constant spin when nobody is touching it, the finger's own motion while dragging, and after a flick the
   angular velocity it was thrown with, decaying with friction back to the idle speed. A pointer resting on it brings
   it to a stop on the nearest card so the text can be read; arrows, dots and the keyboard turn it one card at a time.
   Reduced-motion users get a wheel that only moves when they move it. */
const N = FEATURES.length;
const STEP = 360 / N;                       // degrees per card
const IDLE_SECONDS_PER_CARD = 5.2;
const FRICTION_TAU = 1.4;                   // seconds for a flick to decay by 1/e
const MAX_OMEGA = 720;                      // deg/s, two revolutions a second
const GAP = 18;                             // px between neighbouring cards on the ring
const mod = (a, n) => ((a % n) + n) % n;
const reduced = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function Card({ f, i, refFn }) {
  return (
    <article className="card" ref={refFn} style={{ "--a": `${i * STEP}deg` }}>
      <p className="mono">{f.n} · {f.tag}</p>
      <h3>{f.title}</h3>
      <p>{f.text}</p>
      {f.datestr && <div className="datestr"><span className="now">{f.datestr.now}</span><s>{f.datestr.was}</s></div>}
      {f.list && <ul>{f.list.map(([k, v]) => <li key={k}>{k} <span>{v}</span></li>)}</ul>}
    </article>
  );
}

export default function Features() {
  const wheel = useRef(null), ring = useRef(null);
  const cards = useRef([]);
  const [idx, setIdx] = useState(0);
  const s = useRef({ theta: 0, omega: 0, base: 0, target: null, hold: 0, hover: false, drag: null,
                     R: 600, degPerPx: 0.09, raf: 0, last: 0, shown: 0, thrownUntil: 0 }).current;

  // ring radius from the card width (neighbours just touch), equal card heights, exposed as CSS variables
  useLayoutEffect(() => {
    const measure = () => {
      const el = ring.current; if (!el) return;
      el.style.setProperty("--card-h", "auto");
      const w = cards.current[0]?.offsetWidth || 392;
      const h = Math.max(...cards.current.map((c) => (c ? c.offsetHeight : 0)));
      s.R = (w / 2 + GAP / 2) / Math.tan(Math.PI / N);
      s.degPerPx = STEP / (w + GAP);
      el.style.setProperty("--ring-r", `${s.R}px`);
      el.style.setProperty("--card-h", `${h}px`);
      el.style.setProperty("--ring-h", `${h}px`);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [s]);

  // the physics loop
  useEffect(() => {
    s.base = reduced() ? 0 : -STEP / IDLE_SECONDS_PER_CARD;
    s.omega = s.base;
    const render = () => {
      const el = ring.current; if (!el) return;
      el.style.transform = `translateZ(calc(-1 * var(--ring-r))) rotateY(${s.theta}deg)`;
      cards.current.forEach((c, i) => {
        if (!c) return;
        const a = Math.abs(mod(i * STEP + s.theta + 180, 360) - 180);     // 0 = facing the viewer
        c.style.opacity = a < 18 ? 1 : Math.max(0, 1 - (a - 18) / 64).toFixed(3);
        c.style.visibility = a > 84 ? "hidden" : "visible";
      });
      const front = mod(Math.round(-s.theta / STEP), N);
      if (front !== s.shown) { s.shown = front; setIdx(front); }
      if (wheel.current) wheel.current.dataset.theta = s.theta.toFixed(2);
    };
    const tick = (now) => {
      const dt = Math.min(0.25, (now - (s.last || now)) / 1000); s.last = now;
      if (!s.drag) {
        if (s.target !== null) {                                   // stepping to a chosen card
          const d = s.target - s.theta;
          s.theta += d * Math.min(1, dt * 9); s.omega = 0;
          if (Math.abs(d) < 0.05) { s.theta = s.target; s.target = null; s.hold = 1.2; }
        } else if (s.hold > 0) {                                   // a short rest after a step
          s.hold -= dt;
        } else {
          const want = s.hover && now > s.thrownUntil ? 0 : s.base;   // a thrown wheel keeps going under the cursor
          s.omega += (want - s.omega) * (1 - Math.exp(-dt / FRICTION_TAU));
          s.theta += s.omega * dt;
          if (want === 0 && Math.abs(s.omega) < 6) {               // at rest: settle on the nearest card
            const near = Math.round(s.theta / STEP) * STEP;
            s.theta += (near - s.theta) * Math.min(1, dt * 6);
            if (Math.abs(near - s.theta) < 0.02) { s.theta = near; s.omega = 0; }
          }
        }
      }
      render();
      s.raf = requestAnimationFrame(tick);
    };
    s.raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(s.raf);
  }, [s]);

  // pointer: drag turns the ring directly; the release velocity becomes the spin
  const onDown = (e) => {
    if (e.button !== undefined && e.button !== 0) return;
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* synthetic or already-released pointer */ }
    const t = performance.now();
    s.drag = { x: e.clientX, t0: t, th0: s.theta, samples: [[t, s.theta]] };
    s.target = null; s.hold = 0; s.omega = 0;
    e.currentTarget.classList.add("is-dragging");
  };
  const onMove = (e) => {
    if (!s.drag) return;
    const dx = e.clientX - s.drag.x; s.drag.x = e.clientX;
    s.theta += dx * s.degPerPx;
    const now = performance.now();
    s.drag.samples.push([now, s.theta]);
    if (s.drag.samples.length > 2) s.drag.samples = s.drag.samples.filter(([t], k, arr) => k === arr.length - 1 || now - t < 160);
  };
  const onUp = (e) => {
    if (!s.drag) return;
    const now = performance.now();
    // release velocity from the last ~160 ms of movement, or the whole drag when events were coalesced
    let [t0, th0] = s.drag.samples[0];
    if (now - t0 < 16) { t0 = s.drag.t0; th0 = s.drag.th0; }
    const v = now - t0 > 16 ? ((s.theta - th0) / (now - t0)) * 1000 : 0;
    s.omega = Math.max(-MAX_OMEGA, Math.min(MAX_OMEGA, v));
    if (Math.abs(s.omega) > 40) s.thrownUntil = now + 2600;
    s.drag = null;
    if (e.pointerType !== "mouse") s.hover = false;
    e.currentTarget.classList.remove("is-dragging");
  };
  const onEnter = (e) => { if (e.pointerType === "mouse") s.hover = true; };
  const onLeave = (e) => { if (e.pointerType === "mouse") s.hover = false; };

  const step = useCallback((d) => { s.target = Math.round(s.theta / STEP) * STEP - d * STEP; s.hold = 0; }, [s]);
  const goTo = useCallback((i) => {
    const front = mod(Math.round(-s.theta / STEP), N);
    const d = mod(i - front + N / 2, N) - N / 2;                     // shortest way round
    s.target = Math.round(s.theta / STEP) * STEP - d * STEP; s.hold = 0;
  }, [s]);
  const onKey = (e) => { if (e.key === "ArrowRight") { e.preventDefault(); step(1); } if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); } };

  return (
    <section id="features">
      <div className="wrap">
        <div className="feat-head">
          <SectionHead kicker="What it does" title={<>Small tool. <span className="heading-accent">Does the boring part.</span></>}
            lede="It does on your PC exactly what you would do by hand in a browser, on a schedule, and tells you only what matters." />
          <div className="feat-nav">
            <button type="button" className="feat-arrow" onClick={() => step(-1)} aria-label="Previous feature">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6" /></svg>
            </button>
            <button type="button" className="feat-arrow" onClick={() => step(1)} aria-label="Next feature">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6" /></svg>
            </button>
          </div>
        </div>
      </div>
      <div className="feat-wheel" ref={wheel} role="region" aria-roledescription="carousel" aria-label="Features, drag to spin or use the arrow keys" tabIndex={0}
        onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp} onPointerEnter={onEnter} onPointerLeave={onLeave} onKeyDown={onKey}>
        <div className="feat-ring" ref={ring}>
          {FEATURES.map((f, i) => <Card f={f} i={i} key={f.n} refFn={(el) => { cards.current[i] = el; }} />)}
        </div>
      </div>
      <div className="wrap">
        <div className="feat-dots" role="tablist" aria-label="Feature">
          {FEATURES.map((f, i) => (
            <button key={f.n} type="button" role="tab" aria-selected={i === idx} aria-label={f.title} onClick={() => goTo(i)} />
          ))}
        </div>
      </div>
    </section>
  );
}
