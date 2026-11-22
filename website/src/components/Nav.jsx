import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useScroll } from "../lib/scroll.jsx";
import { useScene } from "../lib/scene.jsx";
import { LINKS } from "../data/content.js";
import { EASE } from "../lib/motion.js";
import DownloadMenu from "./DownloadMenu.jsx";
import { DownloadActions, PlatformNote } from "./DownloadActions.jsx";

/* The bar shows only the few things most visitors want; everything else sits under "More" (and in the footer). */
const TOP = [["/download", "Download"], ["/phone-app", "Android app"], ["/gpa-calculator", "GPA calculator"], ["/privacy", "Privacy"]];
const SECTIONS = [["story", "Tour"], ["features", "Features"], ["screens", "Screens"]];
const MORE_PAGES = [["/cloud", "Cloud checks"], ["/faq", "FAQ"]];
const PAGES = [...TOP, ...MORE_PAGES];

const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.6-1.4-1.4-1.8-1.4-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.9 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .5z" /></svg>
);

/* "More" in the bar: a button that opens a short list. Closes on a choice, on Escape and on a click elsewhere. */
function MoreMenu({ goSection, pathname }) {
  const [open, setOpen] = useState(false);
  const ref = React.useRef(null);
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const away = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const esc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", away); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("pointerdown", away); document.removeEventListener("keydown", esc); };
  }, [open]);
  const here = MORE_PAGES.some(([to]) => to === pathname);
  return (
    <div className="more" ref={ref}>
      <button type="button" className={`more-btn${here ? " is-active" : ""}`} aria-expanded={open} aria-haspopup="true" onClick={() => setOpen((v) => !v)}>
        More <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true"><path d="M2 4.5 6 8.5 10 4.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </button>
      {open && (
        <div className="more-panel" role="menu">
          {SECTIONS.map(([id, label]) => <a key={id} role="menuitem" href={`/#${id}`} onClick={(e) => { setOpen(false); goSection(e, id); }}>{label}</a>)}
          <hr />
          {MORE_PAGES.map(([to, label]) => <NavLink key={to} role="menuitem" to={to} className={({ isActive }) => (isActive ? "is-active" : undefined)}>{label}</NavLink>)}
        </div>
      )}
    </div>
  );
}

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const { scrollTo } = useScroll();
  const { introDone } = useScene();
  const { pathname } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 24); on();
    window.addEventListener("scroll", on, { passive: true }); return () => window.removeEventListener("scroll", on);
  }, []);
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => { document.documentElement.classList.toggle("is-menu", open); return () => document.documentElement.classList.remove("is-menu"); }, [open]);

  /* Section links scroll when already on the home page and navigate there otherwise. */
  const goSection = (e, id) => {
    e.preventDefault(); setOpen(false);
    if (pathname === "/") scrollTo(`#${id}`); else navigate(`/#${id}`);
  };

  return (
    <motion.header className={`nav${scrolled || open ? " is-scrolled" : ""}`} initial={{ y: -16, opacity: 0 }} animate={introDone ? { y: 0, opacity: 1 } : {}} transition={{ duration: 1, ease: EASE, delay: 0.5 }}>
      <div className="wrap">
        <Link className="brand" to="/" aria-label="Assignment Monitor home" onClick={(e) => { setOpen(false); if (window.location.pathname === "/") { e.preventDefault(); if (window.__lenis) window.__lenis.scrollTo(0, { duration: 1.1 }); else window.scrollTo({ top: 0, behavior: "smooth" }); window.history.replaceState(null, "", "/"); } }}>
          <img src="/assets/logo.svg?v=2" alt="" width="28" height="28" />
          <span>Assignment Monitor<small>for Bahria University LMS</small></span>
        </Link>
        <nav className="nav-links" aria-label="Site">
          {TOP.map(([to, label]) => <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "is-active" : undefined)}>{label}</NavLink>)}
          <MoreMenu goSection={goSection} pathname={pathname} />
        </nav>
        <div className="nav-cta">
          <a className="icon-btn" href={LINKS.repo} target="_blank" rel="noopener" aria-label="Source on GitHub"><GitHubIcon /></a>
          <DownloadMenu />
          <button type="button" className={`burger${open ? " is-open" : ""}`} aria-expanded={open} aria-controls="menu" aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen((v) => !v)}>
            <i /><i />
          </button>
        </div>
      </div>
      {createPortal(
      <AnimatePresence>
        {open && (
          <motion.div id="menu" className="menu" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
            <motion.nav className="menu-links" aria-label="Menu" initial="hidden" animate="show" exit="hidden"
              variants={{ hidden: {}, show: { transition: { staggerChildren: 0.05, delayChildren: 0.08 } } }}>
              {[...TOP.map(([to, label]) => ({ label, to })), ...SECTIONS.map(([id, label]) => ({ label, href: `/#${id}`, id, minor: true })), ...MORE_PAGES.map(([to, label]) => ({ label, to, minor: true }))].map((item) => (
                <motion.div key={item.label} variants={{ hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } } }}>
                  {item.to ? <NavLink to={item.to} className={({ isActive }) => [isActive ? "is-active" : "", item.minor ? "menu-minor" : ""].join(" ").trim() || undefined}>{item.label}</NavLink>
                    : <a className={item.minor ? "menu-minor" : undefined} href={item.href} onClick={(e) => goSection(e, item.id)}>{item.label}</a>}
                </motion.div>
              ))}
            </motion.nav>
            <div className="menu-foot">
              <DownloadActions size="lg" />
              <a className="btn btn-ghost btn-lg" href={LINKS.repo} target="_blank" rel="noopener">GitHub</a>
              <PlatformNote className="menu-note" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>,
        document.body,
      )}
    </motion.header>
  );
}
