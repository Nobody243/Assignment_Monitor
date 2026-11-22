import React from "react";
import { usePageMeta } from "../lib/meta.js";
import { metaFor } from "../data/pages.js";
import { fmtMB, fmtDate } from "../lib/release.jsx";
import { usePhoneRelease } from "../lib/phoneRelease.js";
import { PageHero, Stagger, Item, Reveal } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";

export default function PhoneApp() {
  usePageMeta(...metaFor("/phone-app"));
  const rel = usePhoneRelease();
  return (
    <>
      <PageHero kicker="Android app" title={<>Your deadlines, <span className="heading-accent">in your pocket.</span></>}
        lede={<>The phone app reads a small summary of your assignments, attendance, exams, results and announcements, and reminds you before things are due. It only reads: it never signs in to the university portal and never holds your portal password.</>}>
        <Button href={rel.apkUrl} variant="accent" size="lg">Download for Android <small>v{rel.version}{rel.size ? ` · ${fmtMB(rel.size)}` : ""}</small></Button>
        <Button href={rel.pageUrl} external variant="quiet" size="lg">Release notes</Button>
      </PageHero>

      <section className="cloud-how">
        <div className="wrap">
          <h2 className="sr-only">What you get</h2>
          <Stagger className="cloud-cards" step={0.1}>
            <Item as="article" className="cloud-card"><p className="mono">Never miss a deadline</p><h3>Countdowns and reminders</h3><p>Every assignment counts down, with reminders a day, three hours or an hour before. Quiet at night, with Snooze and Done on the notification.</p></Item>
            <Item as="article" className="cloud-card"><p className="mono">Everything in one place</p><h3>Attendance, exams, results</h3><p>How many classes you can still miss, your exam seat and room, announcements, the timetable, and results with CGPA and a GPA what-if calculator.</p></Item>
            <Item as="article" className="cloud-card"><p className="mono">Read-only and private</p><h3>Your data stays yours</h3><p>The phone reads one summary file from your own private GitHub repository. No server of ours, no account, no analytics. The app can be locked with your fingerprint, face or PIN.</p></Item>
          </Stagger>
        </div>
      </section>

      <section className="cloud-notes">
        <div className="wrap two-col">
          <Reveal>
            <p className="mono">Setting it up</p>
            <h2 className="h-md">Four steps, a few minutes.</h2>
            <ol className="plain-list">
              <li><b>01</b><span>Download the APK above and open it. Android asks you to allow installs from your browser or files app once; allow it for this install.</span></li>
              <li><b>02</b><span>Turn on <a href="/cloud">Cloud checks</a> in the desktop app. That makes a private repository in your own GitHub account which checks the portal for you and keeps the summary file the phone reads.</span></li>
              <li><b>03</b><span>In the phone app choose <i>Sign in with a read-only token</i> (the safer one: it can read that one repository and nothing else) or <i>Sign in with a GitHub code</i> (easier: type a short code on github.com).</span></li>
              <li><b>04</b><span>Allow notifications when asked. The app checks for new data about every two hours, even when it is closed.</span></li>
            </ol>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mono">Good to know</p>
            <h2 className="h-md">What it does and does not do.</h2>
            <ol className="plain-list">
              <li><b>Read-only</b><span>It cannot submit work, change anything on the portal, or download lecture files. For those use the desktop app.</span></li>
              <li><b>Android only</b><span>It is a signed APK from GitHub, not on Google Play. {rel.publishedAt ? `The latest version came out on ${fmtDate(rel.publishedAt)}. ` : ""}Updates are a new download, installed over the old one.</span></li>
              <li><b>Battery savers</b><span>Some phones stop background work to save power. If reminders arrive late, set the app to "No restrictions" in the phone's battery settings.</span></li>
              <li><b>Your PC is not needed</b><span>Once cloud checks are on, the checks run on GitHub's machines, so the phone keeps getting data with the PC off.</span></li>
            </ol>
          </Reveal>
        </div>
      </section>
    </>
  );
}
