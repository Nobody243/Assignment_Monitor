import React, { useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import { usePageMeta } from "../lib/meta.js";
import { motion } from "framer-motion";
import { PageHero, SectionHead, Stagger, Reveal } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";
import { LINKS } from "../data/content.js";
import { fadeUp } from "../lib/motion.js";

const MLink = motion(Link);

/* Everywhere a visitor can go, with the words people type when they guess a URL. */
const PLACES = [
  { to: "/", name: "Home", line: "What the app watches and how it tells you.", words: ["home", "index", "start", "app", "about"] },
  { to: "/download", name: "Download", line: "The installer or the portable zip, free.", words: ["download", "downloads", "install", "installer", "setup", "get", "exe", "zip", "portable", "release", "releases", "latest", "update", "win", "windows"] },
  { to: "/cloud", name: "Cloud checks", line: "Alerts on your phone with the PC off.", words: ["cloud", "clouds", "cloud-checks", "actions", "github-actions", "server", "online"] },
  { to: "/phone", name: "Phone alerts", line: "Pair a phone from the app's Settings.", words: ["phone", "mobile", "pair", "pairing", "push", "notifications", "alerts", "android", "ios", "iphone"] },
  { to: "/privacy", name: "Privacy & security", line: "What is stored, where, and what never leaves.", words: ["privacy", "privacy-policy", "policy", "security", "data", "terms", "legal", "gdpr"] },
  { to: "/faq", name: "FAQ", line: "Short answers to the usual questions.", words: ["faq", "faqs", "help", "support", "questions", "docs", "documentation", "guide", "how", "howto", "troubleshooting"] },
  { to: "/#features", name: "Features", line: "Every page of the app, one by one.", words: ["features", "feature", "what", "tour", "story", "screens", "screenshots", "gallery", "channels", "attendance", "exams", "timetable"] },
  { href: LINKS.repo, name: "Source on GitHub", line: "Read the code, open an issue, build it yourself.", words: ["github", "source", "code", "repo", "git", "issues", "issue", "changelog", "license", "licence"] },
];

/* Edit distance, for "downlaod" and friends. */
function lev(a, b) {
  const m = a.length, n = b.length;
  if (!m || !n) return m || n;
  let prev = Array.from({ length: n + 1 }, (_, j) => j);
  for (let i = 1; i <= m; i++) {
    const cur = [i];
    for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    prev = cur;
  }
  return prev[n];
}

/* The most likely intended page for a wrong path: an exact word first, then a near miss on the first segment. */
export function guess(pathname) {
  const clean = decodeURIComponent(pathname).toLowerCase().replace(/\.(html?|php|aspx?)$/, "").replace(/\/+$/, "");
  const parts = clean.split("/").filter(Boolean);
  if (!parts.length) return null;
  const tokens = parts.join("-").split(/[-_.\s]+/).filter(Boolean);
  for (const p of PLACES) if (parts.some((seg) => p.words.includes(seg)) || p.words.includes(parts.join("-"))) return p;
  for (const p of PLACES) if (tokens.some((t) => p.words.includes(t))) return p;
  let best = null, bestD = 3;
  for (const p of PLACES) for (const w of p.words) {
    const d = lev(parts[0], w);
    if (d < bestD && parts[0].length > 3) { bestD = d; best = p; }
  }
  return best;
}

export default function NotFound() {
  usePageMeta("Page not found", "That page does not exist.", { noindex: true });
  const { pathname } = useLocation();
  // test builds only (vite build --mode test): a route that throws, to exercise the crash page
  if (import.meta.env.MODE === "test" && pathname === "/__crash") throw new Error("Test crash: a page threw while rendering");
  const hit = useMemo(() => guess(pathname), [pathname]);
  const shown = pathname.length > 48 ? `${pathname.slice(0, 45)}…` : pathname;
  const referrer = typeof document !== "undefined" ? document.referrer : "";
  const report = `${LINKS.issues}/new?title=${encodeURIComponent(`Broken link: ${pathname}`)}&body=${encodeURIComponent(
    `**Address:** ${pathname}\n**Came from:** ${referrer || "(typed or unknown)"}\n\nWhere I found the link:\n`)}`;
  const notice = hit ? (
    <p className="nf-guess">
      Did you mean {hit.to
        ? <Link to={hit.to} className="nf-guess-link">{hit.name}</Link>
        : <a href={hit.href} className="nf-guess-link" target="_blank" rel="noopener">{hit.name}</a>}?
    </p>
  ) : null;
  return (
    <>
      <PageHero kicker="404" title={<>Lost in <span className="heading-accent">orbit.</span></>}
        lede={<>There is nothing at <code className="nf-path">{shown}</code>. The planet, however, is right where you left it.</>}
        notice={notice}>
        {hit && hit.to && <Button to={hit.to} variant="accent" size="lg">Go to {hit.name}</Button>}
        {hit && hit.href && <Button href={hit.href} external variant="accent" size="lg">Open {hit.name}</Button>}
        <Button to="/" variant={hit ? "ghost" : "accent"} size="lg">Back home</Button>
        {!hit && <Button to="/download" size="lg">Download</Button>}
      </PageHero>

      <section className="nf-places">
        <div className="wrap">
          <SectionHead kicker="Where to go instead" title={<>Everything on this site, <span className="heading-accent">one tap away.</span></>} />
          <Stagger className="nf-grid" step={0.06}>
            {PLACES.map((p) => {
              const inner = <><span className="mono">{p.to || "github.com"}</span><b>{p.name}</b><span className="nf-line">{p.line}</span></>;
              return p.to
                ? <MLink key={p.name} to={p.to} className="nf-card" variants={fadeUp}>{inner}</MLink>
                : <motion.a key={p.name} href={p.href} className="nf-card" variants={fadeUp} target="_blank" rel="noopener">{inner}</motion.a>;
            })}
          </Stagger>
        </div>
      </section>

      <section className="nf-foot">
        <div className="wrap">
          <Reveal className="cta-card compact">
            <h2 className="h-md">Followed a link to get here?</h2>
            <p className="lede">Say where you found it and the link gets fixed. The report opens a pre-filled issue with the address of this page and the page that sent you, nothing else.</p>
            <div className="hero-cta"><Button href={report} external>Report the broken link</Button><Button to="/faq" variant="quiet">Read the FAQ</Button></div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
