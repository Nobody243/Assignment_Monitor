import React from "react";
import { SectionHead, Stagger, Item, Reveal } from "../Reveal.jsx";
import { Button } from "../Button.jsx";
import { usePhoneRelease } from "../../lib/phoneRelease.js";
import { IS_ANDROID } from "../../lib/platform.js";

const SHOTS = [
  ["today", "Today: the next deadline with a countdown"],
  ["attendance", "Attendance: hours you can still miss"],
  ["results", "Results: CGPA and a GPA calculator"],
];

/* Home: the phone app in three screens, with the two ways in (the page, and the APK itself on an Android phone). */
export default function PhoneShowcase() {
  const phone = usePhoneRelease();
  return (
    <section id="phone" className="home-phone">
      <div className="wrap">
        <SectionHead kicker="On your phone" title="And in your pocket." lede="A free Android app that only reads: deadlines with reminders, attendance, exam seats, results and announcements, from a summary in your own private GitHub repository. It never signs in to the portal." />
        <Stagger className="shot-row three" step={0.1}>
          {SHOTS.map(([name, alt]) => (
            <Item as="figure" className="shot" key={name}>
              <div className="shot-frame"><img src={`/assets/phone/${name}.webp`} alt={alt} width="540" height="1080" loading="lazy" decoding="async" /></div>
              <figcaption>{alt.split(":")[0]}</figcaption>
            </Item>
          ))}
        </Stagger>
        <Reveal className="home-phone-cta">
          {IS_ANDROID
            ? <Button href={phone.apkUrl} variant="accent" size="lg">Download for Android <small>v{phone.version}</small></Button>
            : <Button to="/phone-app" variant="accent" size="lg">See the Android app</Button>}
          <Button to="/phone-app" variant="quiet" size="lg">How it works</Button>
        </Reveal>
      </div>
    </section>
  );
}
