import React from "react";
import { SectionHead, Stagger, Item } from "../Reveal.jsx";
import { FEATURES } from "../../data/content.js";
import { coarsePointer } from "../../lib/scroll.jsx";

function Card({ f }) {
  const onMove = (e) => {
    if (coarsePointer()) return;
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`); e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
  };
  return (
    <Item as="article" className="card" onPointerMove={onMove}>
      <span className="mono">{f.n} · {f.tag}</span>
      <h3>{f.title}</h3>
      <p>{f.text}</p>
      {f.datestr && <div className="datestr"><em>{f.datestr.now}</em><s>{f.datestr.was}</s></div>}
      {f.list && <ul>{f.list.map(([k, v]) => <li key={k}>{k} <span>{v}</span></li>)}</ul>}
    </Item>
  );
}

export default function Features() {
  return (
    <section id="features">
      <div className="wrap">
        <SectionHead kicker="What it does" title={<>Small tool. <span className="serif accent">Does the boring part.</span></>}
          lede="It does on your PC exactly what you would do by hand in a browser, on a schedule, and tells you only what matters." />
        <Stagger className="cards" step={0.06}>
          {FEATURES.map((f) => <Card f={f} key={f.n} />)}
        </Stagger>
      </div>
    </section>
  );
}
