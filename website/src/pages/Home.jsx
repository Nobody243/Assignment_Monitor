import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { usePageMeta } from "../lib/meta.js";
import { useScroll } from "../lib/scroll.jsx";
import { useScene } from "../lib/scene.jsx";
import Hero from "../components/home/Hero.jsx";
import Ticker from "../components/home/Ticker.jsx";
import Numbers from "../components/home/Numbers.jsx";
import Tour from "../components/home/Tour.jsx";
import TourMobile from "../components/home/TourMobile.jsx";
import { useIsMobile } from "../lib/useMedia.js";
import Features from "../components/home/Features.jsx";
import Steps from "../components/home/Steps.jsx";
import Gallery from "../components/home/Gallery.jsx";
import PrivacySection from "../components/home/PrivacySection.jsx";
import Cta from "../components/home/Cta.jsx";
import FaqList from "../components/FaqList.jsx";
import { SectionHead, Reveal } from "../components/Reveal.jsx";
import { FAQ } from "../data/content.js";

export default function Home() {
  usePageMeta("", "A free, open-source Windows app that watches your Bahria University LMS and CMS: assignments with extended-deadline detection, attendance margins, the exam seating plan and course announcements. Everything stays on your PC.");
  const { hash } = useLocation();
  const { scrollTo } = useScroll();
  const { introDone } = useScene();
  const mobile = useIsMobile();
  /* /#features and friends: scroll to the section once the page (and, on first load, the intro) is ready. */
  useEffect(() => {
    if (!hash || !introDone) return undefined;
    // twice: once as soon as the page exists, once after the route transition has settled
    const go = () => { const el = document.querySelector(hash); if (el) scrollTo(el); };
    const a = setTimeout(go, 120), b = setTimeout(go, 700);
    return () => { clearTimeout(a); clearTimeout(b); };
  }, [hash, introDone, scrollTo]);
  return (
    <>
      <Hero />
      <Ticker />
      <Numbers />
      {mobile ? <TourMobile /> : <Tour />}
      <Features />
      <Steps />
      <Gallery />
      <PrivacySection />
      <section id="faq">
        <div className="wrap">
          <SectionHead kicker="FAQ" title="Questions, answered." />
          <Reveal><FaqList items={FAQ.slice(0, mobile ? 4 : 6)} /></Reveal>
          <Reveal className="links"><Link to="/faq">All questions</Link></Reveal>
        </div>
      </section>
      <Cta />
    </>
  );
}
