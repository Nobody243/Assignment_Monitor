import React from "react";
import { usePageMeta } from "../lib/meta.js";
import { PageHero, Stagger, Item } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";
import { CHANGELOG } from "../lib/changelog.js";
import { LINKS } from "../data/content.js";

export default function Changelog() {
  usePageMeta("Changelog", "Every Assignment Monitor release and what changed.");
  return (
    <>
      <PageHero kicker="Changelog" title={<>Every release, <span className="serif accent">in plain words.</span></>} lede="Numbered releases are built by GitHub Actions from the tagged source. The app's update check only looks at these.">
        <Button href={LINKS.releases} external>Releases on GitHub</Button>
      </PageHero>
      <section className="changelog">
        <div className="wrap">
          <Stagger className="timeline" step={0.1}>
            {CHANGELOG.map((v, i) => (
              <Item as="article" className="release" key={v.version}>
                <div className="release-meta">
                  <h2>v{v.version}{i === 0 && <span className="pill">Latest</span>}</h2>
                  <span className="mono">{v.date}</span>
                </div>
                <ul>{v.items.map((it) => <li key={it}>{it}</li>)}</ul>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>
    </>
  );
}
