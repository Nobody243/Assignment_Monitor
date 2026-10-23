import React, { useEffect, useMemo, useState } from "react";
import { usePageMeta } from "../lib/meta.js";
import { PageHero, Reveal } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";

/* The page the app's "Pair a phone" QR code opens. It asks for notification permission, subscribes this browser to
   push with the public key the PC put in the link, encrypts the subscription with the key from the link and posts it
   to the throw-away ntfy topic the PC is watching. The PC then pushes straight to this phone; no server of ours is
   involved and the topic is never used again. Nothing here works without the link from the app. */
// Public ntfy relays, in order. ntfy rate-limits by public address and mobile networks put thousands of phones behind
// one, so the first relay may answer 429 for a phone that has never used it; the PC watches all of them.
const RELAYS = ["https://ntfy.sh", "https://ntfy.envs.net", "https://ntfy.hostux.net", "https://ntfy.mzte.de"];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* POSTs `body` to the first relay that accepts it. A 429 is retried after the relay's Retry-After (capped at 8 s), a
   couple of times per relay; other failures move straight on to the next relay. */
async function postRelay(topic, body, onStatus, attempts = 3) {
  let lastStatus = 0;
  for (const relay of RELAYS) {
    for (let i = 0; i < attempts; i += 1) {
      let r;
      try { r = await fetch(`${relay}/${encodeURIComponent(topic)}`, { method: "POST", body, headers: { "Content-Type": "text/plain" } }); }
      catch { break; }
      if (r.ok) return relay;
      lastStatus = r.status;
      if (r.status !== 429) break;
      const wait = Math.min(8, Number(r.headers.get("Retry-After")) || 3);
      onStatus?.(`The relay is busy from this network (many phones share its address). Trying again in ${wait} s…`);
      await sleep(wait * 1000);
    }
    onStatus?.("Trying another relay…");
  }
  throw new Error(lastStatus === 429
    ? "Every relay is refusing this network's address right now (too many phones share it). Switch the phone between Wi-Fi and mobile data, or use a hotspot, and press the button again."
    : `The relay answered ${lastStatus || "nothing"}. Check the phone's internet connection and try again.`);
}

function fromB64url(s) {
  const b = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4));
  return Uint8Array.from(b, (c) => c.charCodeAt(0));
}
function toB64url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent);
const standalone = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;

export default function Phone() {
  usePageMeta("Phone alerts", "Pair your phone with Assignment Monitor on your PC so alerts arrive as notifications here.");
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => { const on = () => setHash(window.location.hash); window.addEventListener("hashchange", on); return () => window.removeEventListener("hashchange", on); }, []);
  const params = useMemo(() => new URLSearchParams(hash.slice(1)), [hash]);
  const topic = params.get("t"), key = params.get("k"), pub = params.get("p");
  const linked = Boolean(topic && key && pub);
  const [state, setState] = useState("idle");   // idle | working | done | error | unsupported | ios
  const [msg, setMsg] = useState("");
  const supported = typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

  useEffect(() => {
    if (!supported) setState("unsupported");
    else if (isIOS() && !standalone()) setState("ios");
  }, [supported]);
  // tell the PC the link was opened, so its dialog can say "now tap Allow"; carries nothing but the word
  useEffect(() => {
    if (linked) postRelay(topic, "opened", null, 1).catch(() => {});
  }, [linked, topic]);

  const pair = async () => {
    setState("working"); setMsg("Asking for permission…");
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") throw new Error("Notifications were not allowed. Allow them in the browser's site settings and try again.");
      setMsg("Setting up…");
      const reg = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;
      let sub = await reg.pushManager.getSubscription();
      if (sub) await sub.unsubscribe();
      sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: fromB64url(pub) });
      setMsg("Handing the key to your PC…");
      const aes = await crypto.subtle.importKey("raw", fromB64url(key), "AES-GCM", false, ["encrypt"]);
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const plain = new TextEncoder().encode(JSON.stringify(sub.toJSON()));
      const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, aes, plain);
      const blob = new Uint8Array(iv.length + ct.byteLength); blob.set(iv, 0); blob.set(new Uint8Array(ct), iv.length);
      await postRelay(topic, toB64url(blob), setMsg);
      try { localStorage.setItem("am-paired", new Date().toISOString()); } catch { /* private mode */ }
      setState("done"); setMsg("");
    } catch (e) {
      setState("error"); setMsg(e.message || String(e));
    }
  };

  return (
    <>
      <PageHero kicker="Phone alerts" title={<>Alerts, <span className="heading-accent">on your phone.</span></>}
        lede="Assignment Monitor on your PC can push its alerts here: deadlines, attendance, exam seats, announcements, new notes. No app to install, no account, nothing stored anywhere but this phone and your PC." />
      <section className="phone-page">
        <div className="wrap">
          <Reveal className="cta-card compact phone-card">
            {!linked && (
              <>
                <h2 className="h-md">Open this page from the app</h2>
                <p className="lede">In Assignment Monitor on your PC go to Settings, then Phone, email and calendar, and press Pair a phone. Scan the code it shows with this phone's camera; the link it opens carries the keys this page needs.</p>
                <div className="hero-cta"><Button to="/download">Get the app</Button><Button to="/" variant="quiet">Home</Button></div>
              </>
            )}
            {linked && state === "unsupported" && (
              <>
                <h2 className="h-md">This browser cannot receive pushes</h2>
                <p className="lede">Open the same link in Chrome, Samsung Internet or Firefox on Android, or in Safari on iPhone with iOS 16.4 or newer.</p>
              </>
            )}
            {linked && state === "ios" && (
              <>
                <h2 className="h-md">One step first on iPhone</h2>
                <p className="lede">Tap the Share button in Safari, choose Add to Home Screen, then open Assignment Monitor from the Home Screen and press Pair there. iPhones only deliver web notifications to pages installed that way.</p>
                <div className="hero-cta"><Button onClick={() => setState("idle")} variant="quiet">I have added it, continue</Button></div>
              </>
            )}
            {linked && (state === "idle" || state === "working" || state === "error") && (
              <>
                <h2 className="h-md">Pair this phone</h2>
                <p className="mono phone-code">Code {topic.slice(3, 9).toUpperCase()}</p>
                <p className="lede">Your PC is waiting and shows the same code. Press the button, allow notifications, and a test alert arrives within a few seconds.</p>
                <div className="hero-cta">
                  <Button variant="primary" onClick={pair} disabled={state === "working"}>{state === "working" ? "Pairing…" : "Allow notifications and pair"}</Button>
                </div>
                {msg && <p className={`phone-msg${state === "error" ? " is-error" : ""}`} role="status">{msg}</p>}
              </>
            )}
            {linked && state === "done" && (
              <>
                <h2 className="h-md">Paired.</h2>
                <p className="lede">Your PC has the key and is sending a test. From now on its alerts arrive here as notifications, with the app on the PC doing all the checking. To stop them, press Unpair in the app's settings or remove this site's permission in the browser.</p>
                <p className="phone-note">Keep this page bookmarked or on the Home Screen; the phone's browser keeps the subscription alive in the background.</p>
              </>
            )}
          </Reveal>
          <Reveal className="phone-how">
            <h3>How it stays private</h3>
            <ul>
              <li>The push keys are made on your PC. Alerts travel from your PC to the phone's push service, encrypted so even that service cannot read them.</li>
              <li>This page hands your PC a one-time address for the phone, encrypted with a key that only the QR code carried, through a throw-away relay topic that is never used again.</li>
              <li>The website has no accounts and no database; it cannot see who paired or what is sent.</li>
            </ul>
          </Reveal>
        </div>
      </section>
    </>
  );
}
