import React from "react";
import { Link } from "react-router-dom";
import { Reveal } from "../Reveal.jsx";
import { Button, DownloadButton } from "../Button.jsx";
import { useRelease, fmtDate } from "../../lib/release.jsx";

export default function Cta() {
  const rel = useRelease();
  return (
    <section className="cta">
      <Reveal className="wrap cta-card">
        <span className="mono">v{rel.version} · released {fmtDate(rel.publishedAt)}</span>
        <h2>Stop orbiting the LMS. <span className="serif accent">Start being told.</span></h2>
        <p className="lede">Free, open source, three minutes to set up.</p>
        <div className="hero-cta">
          <DownloadButton kind="setup" size="lg" showSize={false} />
          <Button to="/download" size="lg">Download guide</Button>
          <Button href={rel.pageUrl} external size="lg" variant="quiet">Release notes</Button>
        </div>
      </Reveal>
    </section>
  );
}
