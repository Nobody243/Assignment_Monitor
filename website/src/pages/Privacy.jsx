import React from "react";
import { usePageMeta } from "../lib/meta.js";
import { PageHero, SectionHead, Stagger, Item, Reveal } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";
import { LINKS, PRIVACY_CARDS } from "../data/content.js";

const DATA = [
  ["Portal password, mail app password, phone push keys", "settings.env in the app's local data folder", "Encrypted with Windows DPAPI for your user account. Another user or another PC cannot decrypt them. Never written to the log."],
  ["Enrollment number, campus, preferences", "same file", "Plain text; not secret."],
  ["Assignments, attendance, exam plan, announcements, lecture list, timetable, log", "data\\ in the same folder", "Local files, readable only by your Windows account by default."],
  ["Browser profile (portal session cookies)", "chrome_profile\\ in the same folder", "Local. Deleted on uninstall."],
  ["With cloud checks on: the same login and keys, plus the cache", "a private repository in your own GitHub account", "Sealed on your PC with the repository's key and kept as GitHub Actions secrets; the cache is files in the private repository. Only if you turn it on."],
];
const NETWORK = [
  ["The portal", "cms.bahria.edu.pk and lms.bahria.edu.pk over HTTPS, to do exactly what you would do by hand: sign in and open your own pages. It only ever reads."],
  ["Your channels", "Only if you turn them on: your own mail server over TLS, and your phone's browser push service. Pairing a phone uses a public ntfy relay for ten minutes, carrying ciphertext only."],
  ["GitHub", "The optional update check reads the newest release number from api.github.com. With cloud checks on, the app also manages your private repository there."],
  ["Browser engine", "Only if Google Chrome is not installed: downloaded once from Microsoft's Playwright CDN."],
];
const NOT = [
  "It does not send your credentials or your data to the author or to any third party.",
  "It does not access anyone else's account or data.",
  "It does not change anything on the portal: it never submits, uploads, or posts.",
  "It does not collect analytics, crash reports, or usage statistics.",
];

export default function Privacy() {
  usePageMeta("Privacy & security", "What Assignment Monitor stores, where, how it is protected, and the only hosts it talks to.");
  return (
    <>
      <PageHero kicker="Privacy & security" title={<>No server. No account. <span className="heading-accent">Nothing leaves your PC.</span></>}
        lede="Assignment Monitor is an independent, open-source student project. It is not affiliated with, endorsed by, or supported by Bahria University. Here is exactly what it keeps and who it talks to.">
        <Button href={LINKS.privacy} external>Full privacy &amp; terms</Button>
        <Button href={LINKS.security} external variant="quiet">Security notes</Button>
      </PageHero>

      <section>
        <div className="wrap">
          <h2 className="sr-only">In short</h2>
          <Stagger className="privacy-grid" step={0.1}>
            {PRIVACY_CARDS.map((c) => <Item as="article" key={c.title}><p className="mono">{c.tag}</p><h3>{c.title}</h3><p>{c.text}</p></Item>)}
          </Stagger>
        </div>
      </section>

      <section>
        <div className="wrap">
          <SectionHead kicker="What it stores" title="Everything in one folder on your PC." lede="%LOCALAPPDATA%\Assignment Monitor. Running from source, the same files live in the project folder and are git-ignored. The last row applies only if you turn on cloud checks." />
          <Reveal className="table-card">
            <table className="data-table">
              <thead><tr><th>Data</th><th>Where it lives</th><th>Protection</th></tr></thead>
              <tbody>{DATA.map((r) => <tr key={r[0]}><td data-label="Data">{r[0]}</td><td data-label="Where it lives"><code>{r[1]}</code></td><td data-label="Protection">{r[2]}</td></tr>)}</tbody>
            </table>
          </Reveal>
        </div>
      </section>

      <section>
        <div className="wrap two-col">
          <Reveal>
            <p className="mono">Network</p>
            <h2 className="h-md">The portal, and what you switch on.</h2>
            <ol className="plain-list">{NETWORK.map(([t, d]) => <li key={t}><b>{t}</b><span>{d}</span></li>)}</ol>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mono">What it does not do</p>
            <h2 className="h-md">Read-only, by design.</h2>
            <ul className="plain-list ticks">{NOT.map((t) => <li key={t}><span>{t}</span></li>)}</ul>
            <p className="mono">Your side</p>
            <ul className="plain-list ticks">
              <li><span>Use it only with your own account.</span></li>
              <li><span>Anyone who can sign in to your Windows account can open the app, so keep your PC secure.</span></li>
              <li><span>The university's own terms apply to your portal account. If it asks you not to use automated tools, stop using the app.</span></li>
            </ul>
          </Reveal>
        </div>
      </section>

      <section>
        <div className="wrap">
          <Reveal className="cta-card compact">
            <p className="mono">Deleting your data</p>
            <h2 className="h-md">Uninstall asks you.</h2>
            <p className="lede">Uninstalling closes the app, removes the background tasks and the program, and asks whether to delete your saved sign-in and cached data as well. Say yes and nothing remains.</p>
            <div className="hero-cta"><Button to="/download">Download guide</Button><Button href={LINKS.repo} external variant="quiet">Read the source</Button></div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
