import React from "react";
import { usePageMeta } from "../lib/meta.js";
import { PageHero, SectionHead, Stagger, Item, Reveal } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";
import { LINKS, PRIVACY_CARDS } from "../data/content.js";

const DATA = [
  ["Portal password", "settings.env in the app's local data folder", "Encrypted with Windows DPAPI for your user account. Another user or another PC cannot decrypt it. Never written to the log."],
  ["Enrollment number, campus, preferences", "same file", "Plain text; not secret."],
  ["Assignment list, sync metadata, log", "data\\ in the app's local data folder", "Local files, readable only by your Windows account by default."],
  ["Browser profile (portal session cookies)", "chrome_profile\\ in the same folder", "Local. Deleted on uninstall."],
];
const NETWORK = [
  ["cms.bahria.edu.pk and lms.bahria.edu.pk", "Over HTTPS, to do exactly what you would do by hand: sign in, open the LMS, open each course's assignments page."],
  ["Playwright's browser CDN (once, optional)", "Only if Google Chrome is not installed: a browser engine is downloaded once from Microsoft's Playwright CDN."],
  ["api.github.com (optional, switchable)", "On start and when you click \"Check for updates\" it reads the newest release number. The installer is downloaded from GitHub only if you click Install. Switch it off in Settings → Running in the background."],
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
          <SectionHead kicker="What it stores" title="Four things, all in one folder." lede="%LOCALAPPDATA%\Assignment Monitor on your PC. Running from source, the same files live in the project folder and are git-ignored." />
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
            <h2 className="h-md">Two hosts, plus two optional ones.</h2>
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
