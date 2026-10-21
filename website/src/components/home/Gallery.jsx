import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence, useMotionValue, useSpring } from "framer-motion";
import { SectionHead, Reveal, Window } from "../Reveal.jsx";
import { SCREENS, shot } from "../../data/content.js";
import { coarsePointer, reduceMotion } from "../../lib/scroll.jsx";

/* Screens: the window tilts a few degrees toward the pointer with a soft glare, screens slide in from the side you
   moved toward, and until you pick one yourself it walks through all eight on its own with a progress line under
   the active tab. It rests while the pointer is on it, off-screen, or in a background tab. */
const DWELL = 6000;

function Seg({ label, options, value, onChange, progress }) {
  return (
    <div className="seg" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} role="tab" aria-selected={o.id === value} onClick={() => onChange(o.id)} type="button">
          {o.id === value && <motion.i layoutId={`seg-${label}`} className="seg-pill" transition={{ type: "spring", stiffness: 420, damping: 36 }} />}
          {o.id === value && progress != null && <i className="seg-progress" style={{ transform: `scaleX(${progress})` }} aria-hidden="true" />}
          <span>{o.label}</span>
        </button>
      ))}
    </div>
  );
}

export default function Gallery() {
  const [screen, setScreen] = useState("dashboard");
  const [theme, setTheme] = useState("dark");
  const [dir, setDir] = useState(1);
  const [auto, setAuto] = useState(() => typeof window === "undefined" || !reduceMotion());
  const [progress, setProgress] = useState(0);
  const rest = useRef({ hover: false, visible: true });
  const stage = useRef(null);
  const src = shot(screen, theme);
  const index = SCREENS.findIndex((s) => s.id === screen);
  const current = SCREENS[index];

  const pick = (id) => { setDir(SCREENS.findIndex((s) => s.id === id) >= index ? 1 : -1); setScreen(id); };

  // auto-advance with a progress line; pauses while hovered, hidden or scrolled away
  useEffect(() => {
    if (!auto) return undefined;
    let raf = 0, elapsed = 0, last = performance.now();
    const tick = (now) => {
      const dt = now - last; last = now;
      if (!rest.current.hover && rest.current.visible && !document.hidden) elapsed += dt;
      if (elapsed >= DWELL) { setDir(1); setScreen(SCREENS[(index + 1) % SCREENS.length].id); return; }
      setProgress(elapsed / DWELL);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [auto, index]);
  useEffect(() => {
    const el = stage.current; if (!el) return undefined;
    const io = new IntersectionObserver(([e]) => { rest.current.visible = e.isIntersecting; }, { threshold: 0.3 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  // have the next screen ready before it is shown
  useEffect(() => { const img = new Image(); img.src = shot(SCREENS[(index + 1) % SCREENS.length].id, theme); }, [index, theme]);

  // tilt toward the pointer
  const rx = useMotionValue(0), ry = useMotionValue(0);
  const srx = useSpring(rx, { stiffness: 110, damping: 18 }), sry = useSpring(ry, { stiffness: 110, damping: 18 });
  const onMove = (e) => {
    if (coarsePointer() || reduceMotion()) return;
    const r = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5, py = (e.clientY - r.top) / r.height - 0.5;
    rx.set(-py * 6); ry.set(px * 8);
    e.currentTarget.style.setProperty("--gx", `${(px + 0.5) * 100}%`); e.currentTarget.style.setProperty("--gy", `${(py + 0.5) * 100}%`);
  };
  const onEnter = () => { rest.current.hover = true; };
  const onLeave = () => { rest.current.hover = false; rx.set(0); ry.set(0); };

  return (
    <section id="screens">
      <div className="wrap gallery">
        <SectionHead kicker="Screens" title="Calm by design." lede="Nothing blinks, nothing nags. What you need is a glance away; the rest stays out of the way." />
        <Reveal className="gallery-controls">
          <Seg label="Screen" options={SCREENS} value={screen} onChange={(id) => { setAuto(false); pick(id); }} progress={auto ? progress : null} />
          <Seg label="Theme" options={[{ id: "dark", label: "Dark" }, { id: "light", label: "Light" }]} value={theme} onChange={setTheme} />
        </Reveal>
        <Reveal>
          <div className="gallery-persp">
            <i className="gallery-floor" aria-hidden="true" />
            <motion.div className="gallery-stage" ref={stage} style={{ rotateX: srx, rotateY: sry }} onPointerMove={onMove} onPointerEnter={onEnter} onPointerLeave={onLeave}>
              <Window title="Assignment Monitor" className="gallery-win">
                <div className="gallery-frame">
                  <AnimatePresence mode="popLayout" initial={false} custom={dir}>
                    <motion.img key={src} src={src} alt={`${current.label} screen, ${theme} theme`} width="1280" height="840" loading="lazy" custom={dir}
                      initial={{ opacity: 0, x: dir * 28, scale: 1.01 }} animate={{ opacity: 1, x: 0, scale: 1 }} exit={{ opacity: 0, x: dir * -20 }}
                      transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }} />
                  </AnimatePresence>
                </div>
              </Window>
              <i className="gallery-glare" aria-hidden="true" />
            </motion.div>
          </div>
          <p className="gallery-caption" aria-live="polite">
            <AnimatePresence mode="wait" initial={false}>
              <motion.span key={screen} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.3 }} style={{ display: "block" }}>
                {current.caption}
              </motion.span>
            </AnimatePresence>
          </p>
        </Reveal>
      </div>
    </section>
  );
}
