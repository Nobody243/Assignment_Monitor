import React from "react";
import { Link } from "react-router-dom";
import { SectionHead, Stagger, Item, Reveal } from "../Reveal.jsx";
import { PRIVACY_CARDS, LINKS } from "../../data/content.js";

export default function PrivacySection() {
  return (
    <section id="privacy">
      <div className="wrap">
        <SectionHead kicker="Privacy & security" title={<>Your password stays <span className="serif accent">on your PC.</span></>} lede="There is no server behind this app and no account to create." />
        <Stagger className="privacy-grid" step={0.1}>
          {PRIVACY_CARDS.map((c) => (
            <Item as="article" key={c.title}><span className="mono">{c.tag}</span><h3>{c.title}</h3><p>{c.text}</p></Item>
          ))}
        </Stagger>
        <Reveal className="links">
          <Link to="/privacy">What it stores, in detail</Link>
          <a href={LINKS.security} target="_blank" rel="noopener">Security notes</a>
          <a href={LINKS.signing} target="_blank" rel="noopener">Code signing policy</a>
          <a href={LINKS.repo} target="_blank" rel="noopener">Source code</a>
        </Reveal>
      </div>
    </section>
  );
}
