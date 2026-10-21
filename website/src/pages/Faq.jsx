import React from "react";
import { usePageMeta } from "../lib/meta.js";
import { PageHero, Reveal } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";
import FaqList from "../components/FaqList.jsx";
import { FAQ, LINKS } from "../data/content.js";

export default function Faq() {
  usePageMeta("FAQ", "Answers about SmartScreen, accounts, Chrome, schedules, uninstalling and running Assignment Monitor from source.");
  return (
    <>
      <PageHero kicker="FAQ" title={<>Questions, <span className="heading-accent">answered.</span></>} lede="Short answers. For anything else, open an issue on GitHub and include the app version from Settings → About." />
      <section className="faq-page">
        <div className="wrap">
          <Reveal><FaqList items={FAQ} /></Reveal>
          <Reveal className="cta-card compact">
            <h2 className="h-md">Still stuck?</h2>
            <p className="lede">Report a problem with the log excerpt from the Activity tab, personal details removed.</p>
            <div className="hero-cta"><Button href={LINKS.issues} external>Open an issue</Button><Button to="/download" variant="quiet">Download guide</Button></div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
