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

  /* ------------------------------------------------------------ intro: a loading screen on every visit.
     It holds the page while the planet, its textures and the web fonts load (scene.js reports progress), so the hero
     appears finished instead of assembling in front of the visitor. A dial sweeps with real progress, the stages light
     up, and on "ready" the screen opens like an iris while the planet floats up underneath. Capped at 6.5 s; skipped
     for reduced motion. */
  const introDone = new Promise((resolve) => window.addEventListener("intro:done", resolve, { once: true }));
  function initIntro() {
    const el = $("#intro");
    const release = () => { document.documentElement.classList.remove("is-intro"); if (lenis) lenis.start(); window.dispatchEvent(new Event("intro:done")); };
    if (!el || !hasGsap || reduce) { if (el) el.remove(); setTimeout(release, 0); return; }
    document.documentElement.classList.add("is-intro"); window.scrollTo(0, 0); if (lenis) lenis.stop();
    const pctEl = $(".intro-pct", el), statusEl = $(".intro-status", el), arc = $(".intro-arc", el), tip = $(".intro-tip", el), stageEls = $$(".intro-stages li", el);
    const ticksG = $(".intro-ticks", el), ticks = [];
    for (let i = 0; i < 60; i++) {                                          // 60 hairline ticks just inside the track; they light up with progress
      const t = document.createElementNS("http://www.w3.org/2000/svg", "line");
      const major = i % 15 === 0, r1 = major ? 86 : 90, r2 = 94, ang = (i / 60) * Math.PI * 2 - Math.PI / 2;
      t.setAttribute("x1", 110 + Math.cos(ang) * r1); t.setAttribute("y1", 110 + Math.sin(ang) * r1);
      t.setAttribute("x2", 110 + Math.cos(ang) * r2); t.setAttribute("y2", 110 + Math.sin(ang) * r2);
      ticksG.appendChild(t); ticks.push(t);
    }
    const CIRC = 2 * Math.PI * 100;
    const stages = [[0, "Warming up the renderer"], [12, "Loading the planet"], [48, "Painting city lights"], [78, "Placing campuses"], [100, "Ready"]];
    const t0 = performance.now(); let real = 0, shown = 0, ready = false, fontsOk = false, closing = false;
    window.addEventListener("scene:progress", (e) => { real = Math.max(real, (e.detail && e.detail.p) || 0); });
    window.addEventListener("scene:ready", () => { ready = true; }, { once: true });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { fontsOk = true; }); else fontsOk = true;
    const setStatus = (txt) => { if (statusEl.textContent === txt) return; statusEl.textContent = txt; statusEl.classList.remove("is-swap"); void statusEl.offsetWidth; statusEl.classList.add("is-swap"); };
    gsap.from([".intro-dial", ".intro-word", ".intro-status-wrap", ".intro-stages", ".intro-corner"], { opacity: 0, y: 14, duration: 0.7, ease: "power3.out", stagger: 0.07 });
    const paint = (p) => {
      const pct = Math.round(p * 100);
      pctEl.textContent = String(pct).padStart(2, "0");
      arc.style.strokeDashoffset = String(CIRC * (1 - p));
      tip.style.transform = `rotate(${p * 360}deg)`;
      ticks.forEach((t, i) => t.classList.toggle("is-lit", i / 60 <= p));
      stageEls.forEach((li) => li.classList.toggle("is-on", pct >= Number(li.dataset.at)));
      const stage = stages.filter((st) => pct >= st[0]).pop(); if (stage) setStatus(stage[1]);
    };
    const close = () => {
      closing = true; paint(1); el.classList.add("is-ready"); el.setAttribute("aria-busy", "false");
      const R = Math.hypot(window.innerWidth, window.innerHeight) * 0.62 + 80;
      gsap.timeline()
        .to([".intro-word", ".intro-status-wrap", ".intro-stages", ".intro-corner"], { opacity: 0, y: -8, duration: 0.3, ease: "power2.in", stagger: 0.03 }, 0.45)
        .to(".intro-num", { scale: 0.86, opacity: 0, duration: 0.35, ease: "power2.in" }, 0.5)
        .to(".intro-dial svg", { scale: 1.12, opacity: 0, duration: 0.5, ease: "power2.in" }, 0.5)
        .add(release, 0.8)
        .to(el, { "--r": R + "px", duration: 1.15, ease: "power4.inOut" }, 0.8)
        .add(() => el.remove());
    };
    const tick = () => {
      if (closing) return;
      const elapsed = (performance.now() - t0) / 1000;
      const floor = Math.min(0.9, elapsed / 5);                             // keeps moving even on a slow connection
      const done = ready && fontsOk;
      const target = done ? 1 : Math.min(0.96, Math.max(real, floor));
      shown += (target - shown) * (done ? 0.12 : 0.07);
      paint(shown);
      if ((done && elapsed > 1.6 && shown > 0.992) || elapsed > 6.5) { close(); return; }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    setTimeout(() => { if (!closing) close(); }, 6500);                     // hard cap even if frames stall while shaders compile
  }

  /* ------------------------------------------------------------ hero headline (plays once the intro has lifted) */
  function initHero() {
    const h1 = $(".hero h1");
    if (h1 && hasGsap && !reduce) {
      h1.innerHTML = h1.innerHTML.replace(/(<span class="serif">.*?<\/span>)|([^\s<]+)/g, (m, span, word) =>
        span ? `<span class="w">${span}</span>` : `<span class="w">${word}</span>`);
      const rest = [".hero .eyebrow", ".hero .lede", ".hero-cta", ".hero-meta", ".hero-pins"];
      gsap.set(".hero h1 .w", { yPercent: 110, opacity: 0 }); gsap.set(rest, { y: 22, opacity: 0 }); gsap.set(".nav", { y: -14, opacity: 0 });
      introDone.then(() => {
        gsap.to(".nav", { y: 0, opacity: 1, duration: 0.8, ease: "power3.out", delay: 0.2 });
        gsap.to(".hero h1 .w", { yPercent: 0, opacity: 1, duration: 1.1, ease: "power4.out", stagger: 0.06, delay: 0.25 });
        gsap.to(rest, { y: 0, opacity: 1, duration: 0.9, ease: "power3.out", stagger: 0.08, delay: 0.6 });
      });
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
    initScroll(); initHero(); initTicker(); initStory(); initReveals(); initGallery(); initFaq(); initNav(); loadRelease(); initIntro();
  });
})();
