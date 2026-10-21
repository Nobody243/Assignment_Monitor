import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useScroll } from "../lib/scroll.jsx";
import { useScene } from "../lib/scene.jsx";
import { useRelease } from "../lib/release.jsx";
import { LINKS } from "../data/content.js";
import { EASE } from "../lib/motion.js";

const SECTIONS = [["story", "Tour"], ["features", "Features"], ["screens", "Screens"]];
const PAGES = [["/download", "Download"], ["/privacy", "Privacy"], ["/faq", "FAQ"], ["/changelog", "Changelog"]];

const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.6-1.4-1.4-1.8-1.4-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.9 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .5z" /></svg>
);

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const { scrollTo } = useScroll();
  const { introDone } = useScene();
  const rel = useRelease();
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
        <Link className="brand" to="/" aria-label="Assignment Monitor home" onClick={() => setOpen(false)}>
          <img src="/assets/logo.svg" alt="" width="28" height="28" />
          <span>Assignment Monitor<small>for Bahria University LMS</small></span>
        </Link>
        <nav className="nav-links" aria-label="Site">
          {SECTIONS.map(([id, label]) => <a key={id} href={`/#${id}`} onClick={(e) => goSection(e, id)}>{label}</a>)}
          {PAGES.map(([to, label]) => <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "is-active" : undefined)}>{label}</NavLink>)}
        </nav>
        <div className="nav-cta">
          <a className="icon-btn" href={LINKS.repo} target="_blank" rel="noopener" aria-label="Source on GitHub"><GitHubIcon /></a>
          <a className="btn btn-primary" href={rel.setupUrl} data-download="setup">Download <small>v{rel.version}</small></a>
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
              {[...SECTIONS.map(([id, label]) => ({ label, href: `/#${id}`, id })), ...PAGES.map(([to, label]) => ({ label, to }))].map((item) => (
                <motion.div key={item.label} variants={{ hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } } }}>
                  {item.to ? <NavLink to={item.to} className={({ isActive }) => (isActive ? "is-active" : undefined)}>{item.label}</NavLink>
                    : <a href={item.href} onClick={(e) => goSection(e, item.id)}>{item.label}</a>}
                </motion.div>
              ))}
            </motion.nav>
            <div className="menu-foot">
              <a className="btn btn-accent btn-lg" href={rel.setupUrl} data-download="setup">Download for Windows <small>v{rel.version}</small></a>
              <a className="btn btn-ghost btn-lg" href={LINKS.repo} target="_blank" rel="noopener">GitHub</a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>,
        document.body,
      )}
    </motion.header>
  );
}
