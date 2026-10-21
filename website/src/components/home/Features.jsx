import React, { useState } from "react";
import { useIsMobile } from "../../lib/useMedia.js";
import { Button } from "../Button.jsx";
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
  const mobile = useIsMobile();
  const [all, setAll] = useState(false);
  const shown = mobile && !all ? FEATURES.slice(0, 3) : FEATURES;   // phones start with three cards; the rest are one tap away
  return (
    <section id="features">
      <div className="wrap">
        <SectionHead kicker="What it does" title={<>Small tool. <span className="serif accent">Does the boring part.</span></>}
          lede="It does on your PC exactly what you would do by hand in a browser, on a schedule, and tells you only what matters." />
        <Stagger className="cards" step={0.06}>
          {shown.map((f) => <Card f={f} key={f.n} />)}
        </Stagger>
        {mobile && !all && <Button className="show-more" onClick={() => setAll(true)}>Show {FEATURES.length - 3} more</Button>}
      </div>
    </section>
  );
}
