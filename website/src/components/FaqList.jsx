import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { EASE } from "../lib/motion.js";

/* Accordion: one item open at a time, height animated, keyboard and screen-reader friendly. */
export default function FaqList({ items, className = "" }) {
  const [openIdx, setOpenIdx] = useState(-1);
  return (
    <div className={`faq ${className}`}>
      {items.map((it, i) => {
        const open = openIdx === i;
        const id = `faq-${i}`;
        return (
          <div className={`faq-item${open ? " is-open" : ""}`} key={it.q}>
            <button type="button" className="faq-q" aria-expanded={open} aria-controls={id} onClick={() => setOpenIdx(open ? -1 : i)}>
              <span>{it.q}</span><i aria-hidden="true" />
            </button>
            <AnimatePresence initial={false}>
              {open && (
                <motion.div id={id} className="faq-a" key="a" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.45, ease: EASE }}>
                  <p>{it.a}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
