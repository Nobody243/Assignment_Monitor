import React, { useEffect, useRef, useState } from "react";
import { TOUR } from "../../data/content.js";

const SHOT = { w: 1280, h: 840 };
const BOX = 1.6;   // the crop window's aspect ratio (width / height)

/* A zoomed crop of the dashboard screenshot showing exactly the region a tour step talks about. The image is
   positioned with percentage transforms, so it needs no measurement and stays crisp at any width. */
function Crop({ spot }) {
  const [x, y, w, h] = spot;
  const spotAspect = (w * SHOT.w) / (h * SHOT.h);
  const widthPct = spotAspect >= BOX ? 9000 / w : (9000 * SHOT.w) / (SHOT.h * BOX * h);   // 10 % breathing room
  return (
    <div className="tour-m-crop" aria-hidden="true">
      <img src="/assets/shot-dashboard-light.png" alt="" width={SHOT.w} height={SHOT.h} loading="lazy"
        style={{ width: `${widthPct}%`, transform: `translate(-${x + w / 2}%, -${y + h / 2}%)` }} />
    </div>
  );
}

/* Phone and tablet tour: one swipeable card per step, each with its own crop, title and caption, plus dots. */
export default function TourMobile() {
  const track = useRef(null);
  const [active, setActive] = useState(0);
  useEffect(() => {
    const el = track.current; if (!el) return undefined;
    const cards = Array.from(el.children);
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting && e.intersectionRatio > 0.6) setActive(cards.indexOf(e.target)); });
    }, { root: el, threshold: [0.6] });
    cards.forEach((c) => io.observe(c));
    return () => io.disconnect();
  }, []);
  const go = (i) => { const c = track.current?.children[i]; if (c) c.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" }); };
  return (
    <section id="story" className="story story-m">
      <div className="wrap">
        <div className="story-head">
          <p className="mono">Tour</p>
          <h2>One screen tells you <span className="heading-accent">what's due.</span></h2>
        </div>
      </div>
      <div className="tour-m-track" ref={track} role="list" aria-label="Tour steps">
        {TOUR.map((s, i) => (
          <article className={`tour-m-card${i === active ? " is-active" : ""}`} key={s.title} role="listitem">
            <Crop spot={s.spot} />
            <p className="mono">{String(i + 1).padStart(2, "0")} / {String(TOUR.length).padStart(2, "0")} · {s.label}</p>
            <h3>{s.title}</h3>
            <p>{s.text}</p>
          </article>
        ))}
      </div>
      <div className="tour-m-dots" role="tablist" aria-label="Tour step">
        {TOUR.map((s, i) => <button key={s.title} type="button" role="tab" aria-selected={i === active} aria-label={`Step ${i + 1}`} onClick={() => go(i)} />)}
      </div>
    </section>
  );
}
