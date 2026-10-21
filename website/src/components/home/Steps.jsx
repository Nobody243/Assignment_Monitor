import React, { useLayoutEffect, useRef, useState } from "react";
import { motion, useScroll as useFmScroll, useSpring, useMotionValueEvent } from "framer-motion";
import { SectionHead } from "../Reveal.jsx";
import { STEPS } from "../../data/content.js";

/* Setup as a timeline. The accent line draws itself as the section scrolls into view, a faint current keeps flowing
   along it, and each node lights up as the line reaches it. Horizontal on wide screens, vertical on narrow ones. */
const H = "M200 20 H1000";
const V = "M20 0 V1200";

export default function Steps() {
  const tl = useRef(null), list = useRef(null);
  const { scrollYProgress } = useFmScroll({ target: tl, offset: ["start 80%", "end 60%"] });
  const draw = useSpring(scrollYProgress, { stiffness: 70, damping: 22, mass: 0.6 });
  const [lit, setLit] = useState(0);
  const n = STEPS.length;
  useMotionValueEvent(draw, "change", (v) => setLit(Math.min(n, Math.floor(v * (n - 1) + 0.6) + 1)));

  // the vertical line runs from the first node's centre to the last node's centre
  useLayoutEffect(() => {
    const measure = () => {
      const nodes = list.current?.querySelectorAll(".tl-node");
      if (!nodes || nodes.length < 2) return;
      const first = nodes[0].getBoundingClientRect(), last = nodes[nodes.length - 1].getBoundingClientRect();
      tl.current.style.setProperty("--tl-v-h", `${last.top - first.top}px`);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  const lines = (d) => (
    <>
      <path className="tl-base" d={d} pathLength="1" />
      <motion.path className="tl-draw" d={d} pathLength="1" style={{ pathLength: draw }} />
      <path className="tl-flow" d={d} pathLength="1" />
    </>
  );

  return (
    <section id="how">
      <div className="wrap">
        <SectionHead kicker="Setup" title={<>Three minutes, then <span className="heading-accent">forget about it.</span></>} />
        <div className="tl" ref={tl}>
          <svg className="tl-line tl-line-h" viewBox="0 0 1200 40" preserveAspectRatio="none" aria-hidden="true">{lines(H)}</svg>
          <svg className="tl-line tl-line-v" viewBox="0 0 40 1200" preserveAspectRatio="none" aria-hidden="true">{lines(V)}</svg>
          <ol className="tl-steps" ref={list}>
            {STEPS.map((s, i) => (
              <li key={s.title} className={`tl-step${i < lit ? " is-on" : ""}`}>
                <span className="tl-node" aria-hidden="true"><b>{String(i + 1).padStart(2, "0")}</b></span>
                <div className="tl-card"><h3>{s.title}</h3><p>{s.text}</p></div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
