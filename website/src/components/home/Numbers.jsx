import React, { useEffect, useRef, useState } from "react";
import { useInView, animate } from "framer-motion";
import { Stagger, Item } from "../Reveal.jsx";
import { NUMBERS } from "../../data/content.js";
import { reduceMotion } from "../../lib/scroll.jsx";

function Counter({ value }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "0px 0px -15% 0px" });
  const [n, setN] = useState(reduceMotion() ? value : 0);
  useEffect(() => {
    if (!inView || reduceMotion()) return undefined;
    const c = animate(0, value, { duration: 1.4, ease: [0.16, 1, 0.3, 1], onUpdate: (v) => setN(Math.round(v)) });
    return () => c.stop();
  }, [inView, value]);
  return <span className="n" ref={ref}>{n}</span>;
}

export default function Numbers() {
  return (
    <section className="numbers" aria-label="At a glance">
      <div className="wrap">
        <Stagger className="numbers-grid" step={0.1}>
          {NUMBERS.map((x) => (
            <Item as="article" className="num" key={x.text}><p className="num-v"><Counter value={x.value} />{x.suffix}</p><p className="num-t">{x.text}</p></Item>
          ))}
        </Stagger>
      </div>
    </section>
  );
}
