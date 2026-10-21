import React from "react";
import { SectionHead, Stagger, Item } from "../Reveal.jsx";
import { STEPS } from "../../data/content.js";

export default function Steps() {
  return (
    <section id="how">
      <div className="wrap">
        <SectionHead kicker="Setup" title={<>Three minutes, then <span className="serif accent">forget about it.</span></>} />
        <Stagger className="steps" step={0.1}>
          {STEPS.map((s, i) => (
            <Item className="step" key={s.title} data-n={i + 1}><h3>{s.title}</h3><p>{s.text}</p></Item>
          ))}
        </Stagger>
      </div>
    </section>
  );
}
