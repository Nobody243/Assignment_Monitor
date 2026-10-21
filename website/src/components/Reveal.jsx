import React from "react";
import { motion } from "framer-motion";
import { fadeUp, stagger, viewport } from "../lib/motion.js";

/* Reveal-on-scroll primitives. <Reveal> animates one block; <Stagger> staggers its <Reveal> children. */
export function Reveal({ as = "div", className, children, delay = 0, ...rest }) {
  const M = motion[as] || motion.div;
  return (
    <M className={className} variants={fadeUp} initial="hidden" whileInView="show" viewport={viewport} transition={{ delay }} {...rest}>
      {children}
    </M>
  );
}
export function Stagger({ as = "div", className, children, delay = 0, step = 0.08, ...rest }) {
  const M = motion[as] || motion.div;
  return (
    <M className={className} variants={stagger(delay, step)} initial="hidden" whileInView="show" viewport={viewport} {...rest}>
      {children}
    </M>
  );
}
export function Item({ as = "div", className, children, ...rest }) {
  const M = motion[as] || motion.div;
  return <M className={className} variants={fadeUp} {...rest}>{children}</M>;
}

export function SectionHead({ kicker, title, lede, className = "" }) {
  return (
    <Reveal className={`section-head ${className}`}>
      {kicker && <p className="mono">{kicker}</p>}
      <h2>{title}</h2>
      {lede && <p className="lede">{lede}</p>}
    </Reveal>
  );
}

export function PageHero({ kicker, title, lede, notice, children }) {
  return (
    <section className="page-hero">
      <div className="wrap">
        <Stagger>
          {kicker && <Item as="p" className="eyebrow mono">{kicker}</Item>}
          <Item as="h1">{title}</Item>
          {lede && <Item as="p" className="lede">{lede}</Item>}
          {notice && <Item>{notice}</Item>}
          {children && <Item className="page-hero-actions">{children}</Item>}
        </Stagger>
      </div>
    </section>
  );
}

export function Window({ title, children, className = "" }) {
  return (
    <div className={`win ${className}`}>
      <div className="win-bar"><i /><i /><i /><b>{title}</b></div>
      {children}
    </div>
  );
}
