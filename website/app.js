/* Assignment Monitor website — no frameworks, no tracking. */
(function () {
  "use strict";

  const REPO = "Nobody243/Assignment_Monitor";
  const FALLBACK_SETUP = `https://github.com/${REPO}/releases/latest/download/AssignmentMonitor-Setup.exe`;
  const FALLBACK_ZIP = `https://github.com/${REPO}/releases/latest/download/AssignmentMonitor-portable.zip`;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- latest release: version, size, links ---------- */
  const fmtMB = (bytes) => `${Math.round(bytes / 1048576)} MB`;
  const fmtDate = (iso) => new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });

  async function loadRelease() {
    try {
      const r = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } });
      if (!r.ok) throw new Error(r.status);
      const rel = await r.json();
      const setup = (rel.assets || []).find((a) => /-setup\.exe$/i.test(a.name));
      const zip = (rel.assets || []).find((a) => /-portable\.zip$/i.test(a.name));
      const version = (rel.tag_name || "").replace(/^v/i, "");
      document.querySelectorAll("[data-version]").forEach((el) => (el.textContent = version ? `v${version}` : el.textContent));
      if (setup) {
        document.querySelectorAll("[data-setup-size]").forEach((el) => (el.textContent = fmtMB(setup.size)));
        document.querySelectorAll("a[data-download='setup']").forEach((a) => (a.href = setup.browser_download_url));
      }
      if (zip) {
        document.querySelectorAll("[data-zip-size]").forEach((el) => (el.textContent = fmtMB(zip.size)));
        document.querySelectorAll("a[data-download='zip']").forEach((a) => (a.href = zip.browser_download_url));
      }
      if (rel.published_at) document.querySelectorAll("[data-published]").forEach((el) => (el.textContent = fmtDate(rel.published_at)));
      document.querySelectorAll("a[data-release-page]").forEach((a) => (a.href = rel.html_url));
    } catch (_) {
      document.querySelectorAll("a[data-download='setup']").forEach((a) => (a.href = FALLBACK_SETUP));
      document.querySelectorAll("a[data-download='zip']").forEach((a) => (a.href = FALLBACK_ZIP));
    }
  }

  /* ---------- scroll reveal ---------- */
  function reveal() {
    const items = document.querySelectorAll("[data-reveal]");
    if (reduceMotion || !("IntersectionObserver" in window)) {
      items.forEach((el) => el.classList.add("is-visible"));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("is-visible");
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.12 });
    items.forEach((el) => io.observe(el));
  }

  /* ---------- sticky nav state ---------- */
  function nav() {
    const header = document.querySelector(".nav");
    const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- hero tilt ---------- */
  function tilt() {
    const stage = document.querySelector(".hero-shot");
    const frame = stage && stage.querySelector(".window");
    if (!frame || reduceMotion || window.matchMedia("(hover: none)").matches) return;
    stage.addEventListener("mousemove", (e) => {
      const r = stage.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      frame.style.transform = `perspective(1400px) rotateX(${(-y * 5).toFixed(2)}deg) rotateY(${(x * 7).toFixed(2)}deg) translateY(-4px)`;
    });
    stage.addEventListener("mouseleave", () => (frame.style.transform = ""));
  }

  /* ---------- screenshot gallery ---------- */
  function gallery() {
    const root = document.querySelector(".gallery");
    if (!root) return;
    const img = root.querySelector(".gallery-img");
    const caption = root.querySelector(".gallery-caption");
    let theme = "dark";
    let screen = "dashboard";
    const update = () => {
      img.src = `assets/shot-${screen}-${theme}.png`;
      img.alt = `${screen} screen, ${theme} theme`;
      caption.textContent = root.querySelector(`[data-screen='${screen}']`).dataset.caption;
      root.querySelectorAll("[data-screen]").forEach((b) => b.setAttribute("aria-selected", b.dataset.screen === screen));
      root.querySelectorAll("[data-theme]").forEach((b) => b.setAttribute("aria-selected", b.dataset.theme === theme));
    };
    root.querySelectorAll("[data-screen]").forEach((b) => b.addEventListener("click", () => { screen = b.dataset.screen; update(); }));
    root.querySelectorAll("[data-theme]").forEach((b) => b.addEventListener("click", () => { theme = b.dataset.theme; update(); }));
    update();
  }

  /* ---------- only one FAQ open at a time ---------- */
  function faq() {
    const all = document.querySelectorAll(".faq details");
    all.forEach((d) => d.addEventListener("toggle", () => {
      if (d.open) all.forEach((o) => { if (o !== d) o.open = false; });
    }));
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("year").textContent = new Date().getFullYear();
    loadRelease();
    reveal();
    nav();
    tilt();
    gallery();
    faq();
  });
})();
