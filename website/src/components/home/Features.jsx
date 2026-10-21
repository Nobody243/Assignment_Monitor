import React, { useRef, useState } from "react";
import { Swiper, SwiperSlide } from "swiper/react";
import { A11y, Autoplay, EffectCoverflow, Keyboard } from "swiper/modules";
import "swiper/css";
import "swiper/css/effect-coverflow";
import { SectionHead } from "../Reveal.jsx";
import { FEATURES } from "../../data/content.js";
import { coarsePointer } from "../../lib/scroll.jsx";

/* Ten features on a wheel: a Swiper coverflow that turns by itself every few seconds, pauses under the pointer,
   and spins with a swipe, the arrows, the dots or the keyboard. Reduced-motion users get a still wheel. */
const reduced = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function Card({ f }) {
  const onMove = (e) => {
    if (coarsePointer()) return;
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`); e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
  };
  return (
    <article className="card" onPointerMove={onMove}>
      <p className="mono">{f.n} · {f.tag}</p>
      <h3>{f.title}</h3>
      <p>{f.text}</p>
      {f.datestr && <div className="datestr"><span className="now">{f.datestr.now}</span><s>{f.datestr.was}</s></div>}
      {f.list && <ul>{f.list.map(([k, v]) => <li key={k}>{k} <span>{v}</span></li>)}</ul>}
    </article>
  );
}

export default function Features() {
  const swiper = useRef(null);
  const [idx, setIdx] = useState(0);
  const auto = !reduced();
  return (
    <section id="features">
      <div className="wrap">
        <div className="feat-head">
          <SectionHead kicker="What it does" title={<>Small tool. <span className="heading-accent">Does the boring part.</span></>}
            lede="It does on your PC exactly what you would do by hand in a browser, on a schedule, and tells you only what matters." />
          <div className="feat-nav">
            <button type="button" className="feat-arrow" onClick={() => swiper.current?.slidePrev()} aria-label="Previous feature">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6" /></svg>
            </button>
            <button type="button" className="feat-arrow" onClick={() => swiper.current?.slideNext()} aria-label="Next feature">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6" /></svg>
            </button>
          </div>
        </div>
      </div>
      <div className="feat-wheel" aria-roledescription="carousel" aria-label="Features">
        <Swiper modules={[A11y, Autoplay, EffectCoverflow, Keyboard]} effect="coverflow" centeredSlides loop grabCursor slidesPerView="auto"
          speed={850} spaceBetween={18} coverflowEffect={{ rotate: 24, stretch: 0, depth: 150, modifier: 1, scale: 0.94, slideShadows: false }}
          autoplay={auto ? { delay: 3400, disableOnInteraction: false, pauseOnMouseEnter: true } : false}
          keyboard={{ enabled: true }} a11y={{ enabled: true }}
          onSwiper={(s) => { swiper.current = s; }} onSlideChange={(s) => setIdx(s.realIndex)}>
          {FEATURES.map((f) => <SwiperSlide key={f.n}><Card f={f} /></SwiperSlide>)}
        </Swiper>
      </div>
      <div className="wrap">
        <div className="feat-dots" role="tablist" aria-label="Feature">
          {FEATURES.map((f, i) => (
            <button key={f.n} type="button" role="tab" aria-selected={i === idx} aria-label={f.title} onClick={() => swiper.current?.slideToLoop(i)} />
          ))}
        </div>
      </div>
    </section>
  );
}
