import React, { useEffect, useRef, useState } from "react";
import { useScene } from "../lib/scene.jsx";
import { useScroll, reduceMotion, gsap, ScrollTrigger } from "../lib/scroll.jsx";
import { useRelease } from "../lib/release.jsx";

const STAGES = [[0, "Warming up the renderer"], [12, "Loading the planet"], [48, "Painting city lights"], [78, "Placing campuses"], [100, "Ready"]];
const MARKS = [["0", "01", "Renderer"], ["30", "02", "Planet"], ["65", "03", "City lights"], ["88", "04", "Campuses"]];
const CIRC = 2 * Math.PI * 100;
const TICKS = Array.from({ length: 60 }, (_, i) => {
  const major = i % 15 === 0, r1 = major ? 86 : 90, r2 = 94, ang = (i / 60) * Math.PI * 2 - Math.PI / 2;
  return { x1: 110 + Math.cos(ang) * r1, y1: 110 + Math.sin(ang) * r1, x2: 110 + Math.cos(ang) * r2, y2: 110 + Math.sin(ang) * r2 };
});

/* Loading screen on every full page load. It holds the page while the planet, its textures and the fonts load so the
   hero appears finished. A dial sweeps with real progress; on "ready" the screen opens like an iris while the planet
   floats up underneath. The counter only starts once the scene's shaders are compiled, and it never moves faster
   than 60 %/s, so nothing it does can read as a jump. Capped at 6.5 s; skipped entirely for reduced motion. */
export default function Intro() {
  const scene = useScene();
  const scrollApi = useScroll(); const scrollRef = useRef(scrollApi); scrollRef.current = scrollApi;
  const rel = useRelease();
  const [gone, setGone] = useState(false);
  const root = useRef(null), pctEl = useRef(null), statusEl = useRef(null), arc = useRef(null), tip = useRef(null), ticksG = useRef(null), stagesEl = useRef(null);

  useEffect(() => {
    if (reduceMotion()) { setGone(true); scene.finishIntro(); return undefined; }
    document.documentElement.classList.add("is-intro"); window.scrollTo(0, 0); scrollRef.current.stop();
    const el = root.current;
    const ticks = Array.from(ticksG.current.querySelectorAll("line"));
    const stageEls = Array.from(stagesEl.current.querySelectorAll("li"));
    const tStart = performance.now();
    let t0 = tStart, real = 0, shown = 0, ready = false, fontsOk = false, closing = false, warm = false, last = tStart, raf = 0, released = false;
    const onWarm = () => { if (!warm) { warm = true; t0 = performance.now(); last = t0; } };
    const offs = [scene.on("warm", onWarm), scene.on("progress", (p) => { real = Math.max(real, p || 0); }), scene.on("ready", () => { ready = true; })];
    const warmTimer = setTimeout(onWarm, 1500);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { fontsOk = true; }); else fontsOk = true;
    const setStatus = (txt) => { const s = statusEl.current; if (!s || s.textContent === txt) return; s.textContent = txt; s.classList.remove("is-swap"); void s.offsetWidth; s.classList.add("is-swap"); };
    gsap.from(el.querySelectorAll(".intro-dial, .intro-word, .intro-status-wrap, .intro-stages, .intro-corner"), { opacity: 0, y: 14, duration: 0.7, ease: "power3.out", stagger: 0.07 });
    const paint = (p) => {
      const pct = Math.round(p * 100);
      pctEl.current.textContent = String(pct).padStart(2, "0");
      arc.current.style.strokeDashoffset = String(CIRC * (1 - p));
      tip.current.style.transform = `rotate(${p * 360}deg)`;
      ticks.forEach((t, i) => t.classList.toggle("is-lit", i / 60 <= p));
      stageEls.forEach((li) => li.classList.toggle("is-on", pct >= Number(li.dataset.at)));
      const stage = STAGES.filter((st) => pct >= st[0]).pop(); if (stage) setStatus(stage[1]);
    };
    const release = () => {
      if (released) return; released = true;
      document.documentElement.classList.remove("is-intro"); scrollRef.current.start(); scene.finishIntro();
      setTimeout(() => ScrollTrigger.refresh(), 50);
    };
    const close = () => {
      closing = true; paint(1); el.classList.add("is-ready"); el.setAttribute("aria-busy", "false");
      const R = Math.hypot(window.innerWidth, window.innerHeight) * 0.62 + 80;
      gsap.timeline({ defaults: { overwrite: "auto" } })
        .to(".intro-num", { scale: 1.06, duration: 0.3, ease: "power2.out" }, 0)
        .to(".intro-num", { scale: 1, duration: 0.5, ease: "power2.inOut" }, 0.3)
        .to(".intro-word, .intro-status-wrap, .intro-stages, .intro-corner", { opacity: 0, y: -10, duration: 0.5, ease: "power2.inOut", stagger: 0.04 }, 0.4)
        .to(".intro-num", { opacity: 0, scale: 0.9, duration: 0.6, ease: "power2.inOut" }, 0.7)
        .to(".intro-dial svg", { scale: 1.1, opacity: 0, duration: 0.8, ease: "power2.inOut" }, 0.7)
        .add(release, 0.85)
        .to(el, { "--r": R + "px", duration: 1.6, ease: "expo.inOut" }, 0.85)
        .add(() => setGone(true));
    };
    const tick = () => {
      if (closing) return;
      if (!warm) { raf = requestAnimationFrame(tick); return; }
      const now = performance.now(), dt = Math.min(0.05, (now - last) / 1000); last = now;
      const elapsed = (now - t0) / 1000;
      const floor = Math.min(0.9, elapsed / 5);
      const done = ready && fontsOk;
      const target = done ? 1 : Math.min(0.96, Math.max(real, floor));
      const eased = shown + (target - shown) * (1 - Math.exp(-dt * (done ? 7 : 4)));
      shown = Math.min(eased, shown + dt * (done ? 1.0 : 0.6));
      paint(shown);
      if ((done && elapsed > 1.6 && shown > 0.992) || (now - tStart) / 1000 > 6.5) { close(); return; }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    const cap = setTimeout(() => { if (!closing) close(); }, 6500);
    return () => { offs.forEach((off) => off()); clearTimeout(warmTimer); clearTimeout(cap); cancelAnimationFrame(raf); if (!released) release(); };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  if (gone) return null;
  return (
    <div className="intro" ref={root} aria-busy="true" role="status" aria-label="Loading">
      <div className="intro-grid" aria-hidden="true" />
      <div className="intro-center">
        <div className="intro-dial" aria-hidden="true">
          <svg viewBox="0 0 220 220">
            <circle className="intro-track" cx="110" cy="110" r="100" />
            <circle className="intro-arc" ref={arc} cx="110" cy="110" r="100" />
            <g className="intro-tip" ref={tip}><circle cx="110" cy="10" r="3.2" /><circle className="intro-tip-halo" cx="110" cy="10" r="9" /></g>
            <g className="intro-ticks" ref={ticksG}>{TICKS.map((t, i) => <line key={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} />)}</g>
          </svg>
          <div className="intro-num"><span className="intro-pct" ref={pctEl}>00</span><sup>%</sup></div>
          <div className="intro-ring" />
        </div>
        <div className="intro-word"><img src="/assets/logo.svg" alt="" width="22" height="22" />Assignment Monitor</div>
        <div className="intro-status-wrap mono"><span className="intro-status" ref={statusEl} aria-live="polite">Warming up</span><i className="intro-caret" /></div>
        <ol className="intro-stages mono" ref={stagesEl} aria-hidden="true">
          {MARKS.map(([at, n, label]) => <li key={n} data-at={at}><b>{n}</b>{label}</li>)}
        </ol>
      </div>
      <div className="intro-corner intro-corner-l mono">For Bahria University LMS</div>
      <div className="intro-corner intro-corner-c mono">Islamabad · Lahore · Karachi</div>
      <div className="intro-corner intro-corner-r mono">v{rel.version} · Windows · free</div>
    </div>
  );
}
