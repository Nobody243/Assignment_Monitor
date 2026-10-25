import React, { useState } from "react";
import { motion } from "framer-motion";
import { usePageMeta } from "../lib/meta.js";
import { metaFor } from "../data/pages.js";
import { PageHero, SectionHead, Stagger, Item, Reveal, Window } from "../components/Reveal.jsx";
import { Button, DownloadButton } from "../components/Button.jsx";
import { LINKS, shot } from "../data/content.js";

const THEMES = [{ id: "light", label: "Light" }, { id: "dark", label: "Dark" }];

function ThemeSeg({ value, onChange }) {
  return (
    <div className="seg" role="tablist" aria-label="Screenshot theme">
      {THEMES.map((o) => (
        <button key={o.id} role="tab" aria-selected={o.id === value} onClick={() => onChange(o.id)} type="button">
          {o.id === value && <motion.i layoutId="seg-cloud-theme" className="seg-pill" transition={{ type: "spring", stiffness: 420, damping: 36 }} />}
          <span>{o.label}</span>
        </button>
      ))}
    </div>
  );
}

/* The walkthrough: one row per step, text beside the screenshot of that moment. Dialog shots are portrait and
   sit in a narrower window; Settings shots are the full app window. */
const STEPS = [
  { n: "01", id: "cloud-off", kind: "app", title: "Settings → Cloud checks → Set up",
    text: "Below Automatic checks. The section says what will happen and who does what: GitHub takes the phone and email alerts, your PC keeps the desktop and voice ones." },
  { n: "02", id: "cloud-consent", kind: "dialog", title: "Read what goes where, then continue",
    text: "A private repository in your own GitHub account, your login and channel keys stored there as encrypted secrets, and a copy of what the PC has already seen. Nothing passes through a server of ours. You need a free GitHub account." },
  { n: "03", id: "cloud-code", kind: "dialog", title: "Sign in with a one-time code",
    text: "The code is copied for you. Press Open GitHub, paste it, press Authorize. The window notices by itself and carries on; no password is typed into the app." },
  { n: "04", id: "cloud-done", kind: "dialog", title: "Done. A first check is already running",
    text: "Within a few minutes a test alert arrives on your phone and in your mailbox, and the result shows in Settings. From here on it runs at 07:43 and 18:37 Pakistan time." },
  { n: "05", id: "cloud-on", kind: "app", title: "Afterwards",
    text: "Settings shows the last run and its result, with Run now and Open on GitHub beside it. Changing your password, phone, email or what to track on the PC updates the cloud automatically, and so does an app update. Turn off removes the secrets and the workflow." },
];

export default function Cloud() {
  usePageMeta(...metaFor("/cloud"));
  const [theme, setTheme] = useState("light");
  return (
    <>
      <PageHero kicker="Cloud checks" title={<>Alerts with the <span className="heading-accent">PC off.</span></>}
        lede={<>Optional, free, and in your own GitHub account: the same check the PC runs, done twice a day on GitHub's machines, so your phone and mailbox hear about a new deadline whether your laptop is open or in a bag. Off until you turn it on, from Settings.</>}>
        <DownloadButton kind="setup" size="lg" direct />
        <Button to="/faq" variant="quiet" size="lg">FAQ</Button>
      </PageHero>

      <section className="cloud-how">
        <div className="wrap">
          <h2 className="sr-only">How it works</h2>
          <Stagger className="cloud-cards" step={0.1}>
            <Item as="article" className="cloud-card"><p className="mono">Where it runs</p><h3>GitHub Actions, in your account</h3><p>The app creates a private repository named assignment-monitor-cloud and installs one workflow. GitHub's free plan gives 2,000 minutes a month; a check uses two or three. Nothing of ours is involved.</p></Item>
            <Item as="article" className="cloud-card"><p className="mono">What goes there</p><h3>Your login and channel keys, sealed</h3><p>Enrollment, portal password, phone subscription and mail password become GitHub Actions secrets: encrypted with the repository's key before they leave the PC, readable only by the check while it runs, masked in logs. Plus the cache of what was last seen.</p></Item>
            <Item as="article" className="cloud-card"><p className="mono">What you give up</p><h3>One extra place for the password</h3><p>Until now it never left your PC. With cloud checks it also lives in GitHub's encrypted secrets, under GitHub's terms. The app says so before you agree, and turning it off removes it again. GitHub's permission covers your whole account; the app touches one repository.</p></Item>
          </Stagger>
        </div>
      </section>

      <section className="cloud-steps">
        <div className="wrap">
          <SectionHead kicker="Setting it up" title={<>Four taps and a <span className="heading-accent">code.</span></>}
            lede="Every screen you will see, on demo data. Pick the theme the shots use." />
          <Reveal className="cloud-seg"><ThemeSeg value={theme} onChange={setTheme} /></Reveal>
          <div className="cloud-list">
            {STEPS.map((s, i) => (
              <Reveal key={s.id} className={`cloud-step is-${s.kind}${i % 2 ? " is-flip" : ""}`} delay={0.05}>
                <div className="cloud-step-text">
                  <p className="mono">{s.n}</p>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                </div>
                <Window title={s.kind === "dialog" ? "Cloud checks" : "Assignment Monitor — Settings"} className="cloud-win">
                  <div className="shot-body"><img src={shot(s.id, theme)} alt={`${s.title} (${theme} theme)`} width={s.kind === "dialog" ? 560 : 1278} height={s.kind === "dialog" ? 540 : 830} loading="lazy" /></div>
                </Window>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="cloud-notes">
        <div className="wrap two-col">
          <Reveal>
            <p className="mono">Good to know</p>
            <h2 className="h-md">What it does and does not promise.</h2>
            <ol className="plain-list">
              <li><b>Times are nominal</b><span>GitHub starts scheduled runs when it has room; at busy hours a check can land late, which is why the times sit off the hour. The PC's own 7 PM check is unaffected.</span></li>
              <li><b>Two runs a day, not hourly</b><span>The hourly due-today voice reminder stays on the PC. The cloud sends the after-check summaries, the attendance, exam and announcement alerts, and calendar invites if enabled.</span></li>
              <li><b>Nothing arrives twice</b><span>While cloud checks are on, the PC leaves phone and email to the cloud and keeps its desktop and voice alerts.</span></li>
              <li><b>Failures are reported</b><span>If three cloud checks in a row fail, the PC shows one notification pointing at the Actions page; the run log on GitHub says why.</span></li>
            </ol>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mono">Turning it off</p>
            <h2 className="h-md">Settings → Cloud checks → Turn off.</h2>
            <ol className="plain-list">
              <li><b>01</b><span>The secrets are deleted from the repository and the workflow file removed, so nothing runs again.</span></li>
              <li><b>02</b><span>This PC forgets the GitHub sign-in. The phone stays paired to the PC as before.</span></li>
              <li><b>03</b><span>The empty repository is yours; the app offers to open its settings page so you can delete it. Revoke the app's permission any time at github.com/settings/applications.</span></li>
            </ol>
          </Reveal>
        </div>
      </section>

      <section className="cloud-foot">
        <div className="wrap">
          <Reveal className="cta-card compact">
            <h2 className="h-md">The long version is in the privacy notes.</h2>
            <p className="lede">Exactly what is stored, where, with which permission, and what the workflow file contains.</p>
            <div className="hero-cta"><Button to="/privacy">Privacy &amp; security</Button><Button href={LINKS.privacy} external variant="quiet">PRIVACY.md on GitHub</Button><Button to="/phone" variant="quiet">Pair a phone first</Button></div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
