import React from "react";
import { Link } from "react-router-dom";
import { Reveal } from "../Reveal.jsx";
import { Button } from "../Button.jsx";
import { DownloadActions, PlatformNote } from "../DownloadActions.jsx";
import { useRelease, fmtDate } from "../../lib/release.jsx";

export default function Cta() {
  const rel = useRelease();
  return (
    <section className="cta">
      <Reveal className="wrap cta-card">
        <p className="mono">v{rel.version} · released {fmtDate(rel.publishedAt)}</p>
        <h2>Stop orbiting the LMS. <span className="heading-accent">Start being told.</span></h2>
        <p className="lede">Free, open source, three minutes to set up.</p>
        <div className="hero-cta">
          <DownloadActions size="lg" secondary="guide" showSize={false} />
          <Button href={rel.pageUrl} external size="lg" variant="quiet">Release notes</Button>
        </div>
        <PlatformNote />
      </Reveal>
    </section>
  );
}
