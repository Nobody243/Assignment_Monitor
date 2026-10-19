/* Assignment Monitor website. No frameworks, no tracking.
   Motion stack: Lenis (smooth scroll) + GSAP ScrollTrigger + a tiny WebGL shader. */
(function () {
  "use strict";

  const REPO = "Nobody243/Assignment_Monitor";
  const FALLBACK_SETUP = `https://github.com/${REPO}/releases/latest/download/AssignmentMonitor-Setup.exe`;
  const FALLBACK_ZIP = `https://github.com/${REPO}/releases/latest/download/AssignmentMonitor-portable.zip`;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const coarse = window.matchMedia("(hover: none), (pointer: coarse)").matches;
  const hasGsap = typeof window.gsap !== "undefined" && typeof window.ScrollTrigger !== "undefined";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  /* ------------------------------------------------------------ release data */
  const fmtMB = (b) => `${Math.round(b / 1048576)} MB`;
  const fmtDate = (iso) => new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  async function loadRelease() {
    try {
      const r = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } });
      if (!r.ok) throw new Error(r.status);
      const rel = await r.json();
      const setup = (rel.assets || []).find((a) => /-setup\.exe$/i.test(a.name));
      const zip = (rel.assets || []).find((a) => /-portable\.zip$/i.test(a.name));
      const version = (rel.tag_name || "").replace(/^v/i, "");
      if (version) $$("[data-version]").forEach((el) => (el.textContent = `v${version}`));
      if (setup) { $$("[data-setup-size]").forEach((el) => (el.textContent = fmtMB(setup.size))); $$("a[data-download='setup']").forEach((a) => (a.href = setup.browser_download_url)); }
      if (zip) { $$("[data-zip-size]").forEach((el) => (el.textContent = fmtMB(zip.size))); $$("a[data-download='zip']").forEach((a) => (a.href = zip.browser_download_url)); }
      if (rel.published_at) $$("[data-published]").forEach((el) => (el.textContent = fmtDate(rel.published_at)));
      $$("a[data-release-page]").forEach((a) => (a.href = rel.html_url));
    } catch (_) {
      $$("a[data-download='setup']").forEach((a) => (a.href = FALLBACK_SETUP));
      $$("a[data-download='zip']").forEach((a) => (a.href = FALLBACK_ZIP));
    }
  }

  /* ------------------------------------------------------------ smooth scroll */
  let lenis = null;
  function initScroll() {
    if (!hasGsap) return;
    gsap.registerPlugin(ScrollTrigger);
    if (reduce || typeof window.Lenis === "undefined") return;
    lenis = new Lenis({ duration: 1.05, smoothWheel: true, wheelMultiplier: 0.95 });
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
    $$('a[href^="#"]').forEach((a) => a.addEventListener("click", (e) => {
      const id = a.getAttribute("href");
      if (id.length > 1 && $(id)) { e.preventDefault(); lenis.scrollTo(id, { offset: -72 }); }
    }));
  }

  /* ------------------------------------------------------------ hero headline + app reveal */
  function initHero() {
    const h1 = $(".hero h1");
    if (h1 && hasGsap && !reduce) {
      h1.innerHTML = h1.innerHTML.replace(/(<span class="serif">.*?<\/span>)|([^\s<]+)/g, (m, span, word) =>
        span ? `<span class="w">${span}</span>` : `<span class="w">${word}</span>`);
      gsap.from(".hero h1 .w", { yPercent: 110, opacity: 0, duration: 1.1, ease: "power4.out", stagger: 0.06, delay: 0.15 });
      gsap.from([".hero .eyebrow", ".hero .lede", ".hero-cta", ".hero-meta"], { y: 22, opacity: 0, duration: 0.9, ease: "power3.out", stagger: 0.08, delay: 0.5 });
    }
    if (!hasGsap || reduce) return;
    gsap.to(".hero-copy", { yPercent: -14, opacity: 0, ease: "none", scrollTrigger: { trigger: ".hero", start: "12% top", end: "70% top", scrub: 0.6 } });
  }

  /* ------------------------------------------------------------ ticker reacts to scroll velocity */
  function initTicker() {
    const track = $(".ticker-track");
    if (!track || !hasGsap) return;
    track.innerHTML += track.innerHTML;
    if (reduce) return;
    const tween = gsap.to(track, { xPercent: -50, duration: 38, ease: "none", repeat: -1 });
    const speed = gsap.quickTo(tween, "timeScale", { duration: 0.6 });
    if (lenis) lenis.on("scroll", ({ velocity }) => speed(1 + Math.min(Math.abs(velocity) / 12, 5)));
  }

  /* ------------------------------------------------------------ pinned tour: vertical carousel */
  function initStory() {
    const section = $(".story"), visual = $(".story-visual .shot"), steps = $$(".story-step"), dots = $$(".story-rail li"), hint = $(".story-hint");
    if (!section || !visual || !steps.length) return;
    let current = -1;
    const setActive = (idx) => {
      idx = Math.max(0, Math.min(steps.length - 1, idx));
      if (idx === current) return;
      current = idx;
      const step = steps[idx];
      const [x, y, w, h] = step.dataset.spot.split(",").map(Number);
      visual.style.setProperty("--sx", x + "%"); visual.style.setProperty("--sy", y + "%");
      visual.style.setProperty("--sw", w + "%"); visual.style.setProperty("--sh", h + "%");
      $(".spot-label", visual).textContent = step.dataset.label;
      steps.forEach((s, i) => { s.classList.toggle("is-active", i === idx); s.classList.toggle("is-past", i < idx); });
      dots.forEach((d, i) => { d.classList.toggle("is-active", i === idx); d.classList.toggle("is-past", i < idx); });
      if (hint) hint.classList.toggle("is-done", idx === steps.length - 1);
    };
    setActive(0);
    const desktop = window.matchMedia("(min-width: 901px)").matches;
    if (!hasGsap || reduce || !desktop) { if (!desktop) steps.forEach((s) => s.classList.add("is-active")); return; }
    const perStep = () => Math.round(window.innerHeight * 0.42);   // short scroll per step: the carousel should feel quick
    const st = ScrollTrigger.create({
      trigger: section, start: "top top", end: () => "+=" + perStep() * steps.length, pin: ".story-pin", pinSpacing: true,
      anticipatePin: 1, scrub: true,
      onUpdate: (self) => setActive(Math.floor(self.progress * steps.length)),
    });
    dots.forEach((d, i) => d.querySelector("button").addEventListener("click", () => {
      const target = st.start + perStep() * i + perStep() * 0.5;
      if (lenis) lenis.scrollTo(target, { duration: 1 }); else window.scrollTo({ top: target, behavior: "smooth" });
    }));
  }

  /* ------------------------------------------------------------ reveals, counters, drawn line */
  function initReveals() {
    const items = $$("[data-reveal]");
    // IntersectionObserver, not the scroll library, decides visibility: content can never stay hidden.
    if (reduce || !("IntersectionObserver" in window)) { items.forEach((el) => el.classList.add("is-visible")); }
    else {
      const io = new IntersectionObserver((entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("is-visible"); io.unobserve(e.target); } }),
        { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
      items.forEach((el) => io.observe(el));
      setTimeout(() => items.forEach((el) => { const r = el.getBoundingClientRect(); if (r.top < innerHeight) el.classList.add("is-visible"); }), 1500);
    }
    if (!hasGsap || reduce) return;
    $$("[data-count]").forEach((el) => {
      const end = parseFloat(el.dataset.count), suffix = el.dataset.suffix || "";
      const obj = { v: 0 };
      ScrollTrigger.create({ trigger: el, start: "top 85%", once: true, onEnter: () => gsap.to(obj, { v: end, duration: 1.4, ease: "power2.out", onUpdate: () => (el.textContent = Math.round(obj.v) + suffix) }) });
    });
    const line = $(".steps-line path");
    if (line) {
      const len = line.getTotalLength(); line.style.strokeDasharray = len; line.style.strokeDashoffset = len;
      gsap.to(line, { strokeDashoffset: 0, ease: "none", scrollTrigger: { trigger: ".steps", start: "top 75%", end: "bottom 60%", scrub: true } });
    }
    // pointer-following highlight on cards
    if (!coarse) $$(".card").forEach((c) => c.addEventListener("pointermove", (e) => {
      const r = c.getBoundingClientRect(); c.style.setProperty("--mx", (e.clientX - r.left) + "px"); c.style.setProperty("--my", (e.clientY - r.top) + "px");
    }, { passive: true }));
  }

  /* ------------------------------------------------------------ gallery + faq + nav */
  function initGallery() {
    const root = $(".gallery"); if (!root) return;
    const img = $(".gallery-img", root), caption = $(".gallery-caption", root);
    let theme = "dark", screen = "dashboard";
    const update = () => {
      img.src = `assets/shot-${screen}-${theme}.png`; img.alt = `${screen} screen, ${theme} theme`;
      caption.textContent = $(`[data-screen='${screen}']`, root).dataset.caption;
      $$("[data-screen]", root).forEach((b) => b.setAttribute("aria-selected", b.dataset.screen === screen));
      $$("[data-theme]", root).forEach((b) => b.setAttribute("aria-selected", b.dataset.theme === theme));
    };
    $$("[data-screen]", root).forEach((b) => b.addEventListener("click", () => { screen = b.dataset.screen; update(); }));
    $$("[data-theme]", root).forEach((b) => b.addEventListener("click", () => { theme = b.dataset.theme; update(); }));
    update();
  }
  function initFaq() { const all = $$(".faq details"); all.forEach((d) => d.addEventListener("toggle", () => d.open && all.forEach((o) => o !== d && (o.open = false)))); }
  function initNav() {
    const nav = $(".nav"); const on = () => nav.classList.toggle("is-scrolled", window.scrollY > 24);
    on(); window.addEventListener("scroll", on, { passive: true });
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("#year").textContent = new Date().getFullYear();
    initScroll(); initHero(); initTicker(); initStory(); initReveals(); initGallery(); initFaq(); initNav(); loadRelease();
  });
})();
