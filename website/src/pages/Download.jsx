import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useScroll } from "../lib/scroll.jsx";
import { usePageMeta } from "../lib/meta.js";
import { useRelease, fmtMB, fmtDate } from "../lib/release.jsx";
import { PageHero, SectionHead, Stagger, Item, Reveal } from "../components/Reveal.jsx";
import { Button, DownloadButton } from "../components/Button.jsx";
import { SendToPc } from "../components/SendToPc.jsx";
import { IS_WINDOWS, PLATFORM_NOTE } from "../lib/platform.js";
import { LINKS, WHAT_INSTALLER_DOES, UNINSTALL_STEPS } from "../data/content.js";

export default function Download() {
  usePageMeta("Download", "Download Assignment Monitor for Windows: installer or portable zip, what the installer does, SmartScreen, requirements and uninstall.");
  const rel = useRelease();
  const { hash } = useLocation();
  const { scrollTo } = useScroll();
  /* /download#installer and /download#zip (from the nav chooser and every Download button) land on that card */
  useEffect(() => {
    if (!hash) return undefined;
    const go = () => { const el = document.querySelector(hash); if (el) scrollTo(el, { offset: -96 }); };
    const a = setTimeout(go, 150), b = setTimeout(go, 700);
    return () => { clearTimeout(a); clearTimeout(b); };
  }, [hash, scrollTo]);
  const banner = IS_WINDOWS ? null : <div className="platform-banner"><p>{PLATFORM_NOTE}</p><SendToPc size="sm" variant="ghost" /></div>;
  return (
    <>
      <PageHero kicker="Download" title={<>Get Assignment Monitor <span className="heading-accent">v{rel.version}</span></>}
        lede={<>Windows 10 or 11, 64-bit. No administrator rights, no account.<span className="dl-when">{rel.publishedAt ? `Released ${fmtDate(rel.publishedAt)}.` : "Checking the latest release…"}</span></>} notice={banner}>
        <DownloadButton kind="setup" size="lg" direct />
        <DownloadButton kind="zip" size="lg" direct />
      </PageHero>

      <section className="dl-options">
        <div className="wrap">
          <Stagger className="option-grid" step={0.12}>
            <Item as="article" className="option is-recommended" id="installer">
              <p className="mono">Recommended</p>
              <h2>Installer</h2>
              <p className="option-size">AssignmentMonitor-Setup.exe{rel.setupSize ? ` · ${fmtMB(rel.setupSize)}` : ""}</p>
              <ul>
                <li>Installs for your user account only; no administrator password</li>
                <li>Start Menu entry and an optional Desktop icon</li>
                <li>In-app updates: one click installs new versions and keeps your sign-in</li>
                <li>Clean uninstall from Windows Settings</li>
              </ul>
              <DownloadButton kind="setup" showSize={false} label="Download installer" direct />
            </Item>
            <Item as="article" className="option" id="zip">
              <p className="mono">No installer</p>
              <h2>Portable zip</h2>
              <p className="option-size">AssignmentMonitor-portable.zip{rel.zipSize ? ` · ${fmtMB(rel.zipSize)}` : ""}</p>
              <ul>
                <li>Unzip anywhere and run AssignmentMonitor.exe</li>
                <li>Same app, same features, same data folder</li>
                <li>Background tasks are still created when you tick "Check automatically"</li>
                <li>Updates: download the new zip and replace the folder</li>
              </ul>
              <DownloadButton kind="zip" showSize={false} label="Download zip" direct />
            </Item>
          </Stagger>
          <Reveal as="p" className="dl-hint">One click starts the file. Your browser saves it to its Downloads folder unless you have set it to ask where to save each file (a browser setting, under Downloads).</Reveal>
        </div>
      </section>

      <section className="dl-smartscreen">
        <div className="wrap">
          <SectionHead kicker="First run" title={<>Windows may say <span className="heading-accent">"protected your PC".</span></>}
            lede="The installer is not yet code-signed (the project is applying for a free open-source certificate), so SmartScreen shows a warning the first time. The file itself is built by GitHub Actions from the public source." />
          <Stagger className="steps" step={0.1}>
            <Item className="step" data-n="1"><h3>More info</h3><p>On the blue SmartScreen dialog, click the small "More info" link under the message.</p></Item>
            <Item className="step" data-n="2"><h3>Run anyway</h3><p>A "Run anyway" button appears. Click it; the normal setup wizard opens.</p></Item>
            <Item className="step" data-n="3"><h3>Or build it yourself</h3><p>Clone the repository and run the build command. You get the same installer, built from code you can read.</p></Item>
          </Stagger>
        </div>
      </section>

      <section className="dl-details">
        <div className="wrap two-col">
          <Reveal>
            <p className="mono">What the installer does</p>
            <h2 className="h-md">Four things, all under your account.</h2>
            <ol className="plain-list">
              {WHAT_INSTALLER_DOES.map(([t, d]) => <li key={t}><b>{t}</b><span>{d}</span></li>)}
            </ol>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mono">Uninstalling</p>
            <h2 className="h-md">Settings → Apps → Assignment Monitor → Uninstall.</h2>
            <ol className="plain-list">
              {UNINSTALL_STEPS.map((s, i) => <li key={i}><b>{String(i + 1).padStart(2, "0")}</b><span>{s}</span></li>)}
            </ol>
          </Reveal>
        </div>
      </section>

      <section className="dl-foot">
        <div className="wrap">
          <Reveal className="cta-card compact">
            <h2 className="h-md">Questions before you install?</h2>
            <p className="lede">What it does with your account, where it keeps data, what it connects to.</p>
            <div className="hero-cta"><Button to="/privacy">Privacy &amp; security</Button><Button to="/faq" variant="quiet">FAQ</Button><Link className="btn btn-quiet" to="/#story">Take the tour</Link><Button href={LINKS.releases} external variant="quiet">Release notes on GitHub</Button></div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
