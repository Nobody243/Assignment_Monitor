import React, { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useScene } from "../../lib/scene.jsx";
import { gsap, ScrollTrigger, reduceMotion } from "../../lib/scroll.jsx";
import { DownloadActions, PlatformNote } from "../DownloadActions.jsx";
import { EASE } from "../../lib/motion.js";

const WORDS = ["Never", "miss", "an", "LMS", "deadline"];
const word = { hidden: { y: "110%", opacity: 0 }, show: { y: "0%", opacity: 1, transition: { duration: 1.3, ease: [0.19, 1, 0.22, 1] } } };
const rise = { hidden: { y: 22, opacity: 0 }, show: { y: 0, opacity: 1, transition: { duration: 1.1, ease: EASE } } };

export default function Hero() {
  const { introDone } = useScene();
  const copy = useRef(null);
  useEffect(() => {
    if (reduceMotion()) return undefined;
    const tw = gsap.to(copy.current, { yPercent: -14, opacity: 0, ease: "none", scrollTrigger: { trigger: ".hero", start: "12% top", end: "70% top", scrub: 0.6 } });
    return () => { tw.scrollTrigger?.kill(); tw.kill(); };
  }, []);
  const state = introDone ? "show" : "hidden";
  return (
    <section className="hero">
      <motion.div className="wrap hero-copy" ref={copy} initial={{ scale: 1.04 }} animate={introDone ? { scale: 1 } : {}} transition={{ duration: 2.2, ease: EASE }}>
        <motion.div initial="hidden" animate={state} variants={{ hidden: {}, show: { transition: { delayChildren: 0.45, staggerChildren: 0.055 } } }} className="hero-stack">
          <motion.p className="eyebrow mono" variants={rise}>For Bahria University students · Windows · free</motion.p>
          <h1 aria-label="Never miss an LMS deadline again.">
            {WORDS.map((w) => <span className="w" key={w} aria-hidden="true"><motion.span variants={word}>{w}</motion.span></span>)}
            <span className="w" aria-hidden="true"><motion.span className="heading-accent hero-accent" variants={word}>again.</motion.span></span>
          </h1>
          <motion.p className="lede" variants={rise}>Assignment Monitor signs in to the portal for you and keeps watch on what matters: every course's assignments, with the extended deadlines the LMS hides; your attendance margin; your exam room and seat; course announcements; and the lecture notes, ready to download in one go. It reminds you out loud on the day something is due.</motion.p>
          <motion.div className="hero-cta" variants={rise}>
            <DownloadActions size="lg" />
          </motion.div>
          <PlatformNote as={motion.p} variants={rise} />
          <motion.ul className="hero-meta" variants={rise}><li>No account</li><li>No server</li><li>Password never leaves your PC</li><li>MIT</li></motion.ul>
          <motion.ul className="hero-pins mono" variants={rise} aria-hidden="true"><li>Islamabad</li><li>Lahore</li><li>Karachi</li></motion.ul>
        </motion.div>
      </motion.div>
    </section>
  );
}
