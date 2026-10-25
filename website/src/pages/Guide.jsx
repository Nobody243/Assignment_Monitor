import React from "react";
import { Link, useParams } from "react-router-dom";
import { usePageMeta } from "../lib/meta.js";
import { PageHero, Reveal } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";
import { GUIDES } from "../data/guides.js";
import { metaFor } from "../data/pages.js";
import NotFound from "./NotFound.jsx";

function fmt(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

/* A guide: plain reading, one column, the same hero and type as the other pages. Content lives in data/guides.js
   so the build-time prerender can write the same words into the static page. */
export default function Guide() {
  const { slug } = useParams();
  const g = GUIDES[slug];
  if (!g) return <NotFound />;
  return <GuideBody slug={slug} g={g} />;
}

function GuideBody({ slug, g }) {
  usePageMeta(...metaFor(`/guide/${slug}`));
  return (
    <>
      <PageHero kicker={g.kicker} title={g.title} lede={g.lede} />
      <section className="guide">
        <div className="wrap guide-wrap">
          <article className="guide-body">
            {g.sections.map((s) => (
              <Reveal as="section" key={s.h}>
                <h2 className="h-md">{s.h}</h2>
                {s.p?.map((t) => <p key={t}>{t}</p>)}
                {s.list && <ul className="plain-list guide-list">{s.list.map(([b, t]) => <li key={b}><b>{b}</b><span>{t}</span></li>)}</ul>}
                {s.after && <p>{s.after}</p>}
              </Reveal>
            ))}
            <Reveal className="guide-foot">
              <p className="mono">Updated {fmt(g.updated)}. Assignment Monitor is an independent student project, not affiliated with Bahria University.</p>
            </Reveal>
          </article>
          <Reveal as="aside" className="guide-aside">
            <p className="mono">Read next</p>
            <ul className="plain-list">{g.related.map(([to, label]) => <li key={to}><Link to={to}>{label}</Link></li>)}</ul>
            <div className="hero-cta"><Button to="/download">Download the app</Button></div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
