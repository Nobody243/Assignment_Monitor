import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { SectionHead, Reveal, Window } from "../Reveal.jsx";
import { SCREENS, shot } from "../../data/content.js";

function Seg({ label, options, value, onChange }) {
  return (
    <div className="seg" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} role="tab" aria-selected={o.id === value} onClick={() => onChange(o.id)} type="button">
          {o.id === value && <motion.i layoutId={`seg-${label}`} className="seg-pill" transition={{ type: "spring", stiffness: 420, damping: 36 }} />}
          <span>{o.label}</span>
        </button>
      ))}
    </div>
  );
}

export default function Gallery() {
  const [screen, setScreen] = useState("dashboard");
  const [theme, setTheme] = useState("dark");
  const src = shot(screen, theme);
  const current = SCREENS.find((s) => s.id === screen);
  return (
    <section id="screens">
      <div className="wrap gallery">
        <SectionHead kicker="Screens" title="Calm by design." lede="Nothing blinks, nothing nags. What you need is a glance away; the rest stays out of the way." />
        <Reveal className="gallery-controls">
          <Seg label="Screen" options={SCREENS} value={screen} onChange={setScreen} />
          <Seg label="Theme" options={[{ id: "dark", label: "Dark" }, { id: "light", label: "Light" }]} value={theme} onChange={setTheme} />
        </Reveal>
        <Reveal>
          <Window title="Assignment Monitor" className="gallery-win">
            <div className="gallery-frame">
              <AnimatePresence mode="popLayout" initial={false}>
                <motion.img key={src} src={src} alt={`${current.label} screen, ${theme} theme`} width="1280" height="840" loading="lazy"
                  initial={{ opacity: 0, scale: 1.015 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }} />
              </AnimatePresence>
            </div>
          </Window>
          <p className="gallery-caption" aria-live="polite">{current.caption}</p>
        </Reveal>
      </div>
    </section>
  );
}
