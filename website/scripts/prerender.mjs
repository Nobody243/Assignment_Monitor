/* Runs after `vite build`. Writes one static HTML file per route from dist/index.html:

     /            -> dist/index.html (rewritten in place)
     /download    -> dist/download.html          (vercel.json rewrites /download to it)
     /guide/<slug> -> dist/guide/<slug>.html

   Each file carries the page's own <title>, description, canonical and social tags, structured data (breadcrumbs,
   the FAQ as FAQPage, guides as TechArticle) and, inside #root beneath the boot cover, a plain-HTML outline of
   the page from src/data/pages.js. Crawlers that do not run scripts and link previews read that; React replaces
   it on mount. dist/404.html stays the plain shell, copied before this script runs. */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { PAGES, SITE, BASE, DEFAULT_TITLE } from "../src/data/pages.js";
import { FAQ } from "../src/data/faq.js";
import { GUIDES } from "../src/data/guides.js";

const dist = resolve(dirname(fileURLToPath(import.meta.url)), "..", "dist");
const shell = readFileSync(resolve(dist, "index.html"), "utf8");

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const attr = (s) => esc(s);
const ld = (obj) => `<script type="application/ld+json">${JSON.stringify(obj).replace(/</g, "\\u003c")}</script>`;

function setTag(html, selector, attrName, value) {
  const re = new RegExp(`(<${selector.tag}[^>]*${selector.key}="${selector.value}"[^>]*?)\\s${attrName}="[^"]*"`, "i");
  if (!re.test(html)) throw new Error(`tag not found: ${selector.tag}[${selector.key}=${selector.value}]`);
  return html.replace(re, `$1 ${attrName}="${attr(value)}"`);
}

function outline(page) {
  const parts = [`<h1>${esc(page.h1)}</h1>`, `<p>${esc(page.lede)}</p>`];
  for (const s of page.sections || []) {
    parts.push(`<h2>${esc(s.h)}</h2>`);
    for (const t of s.p || []) parts.push(`<p>${esc(t)}</p>`);
    if (s.bullets) parts.push(`<ul>${s.bullets.map((b) => `<li>${esc(b)}</li>`).join("")}</ul>`);
    if (s.after) parts.push(`<p>${esc(s.after)}</p>`);
  }
  if (page.faq) {
    for (const it of page.faq) parts.push(`<h2>${esc(it.q)}</h2><p>${esc(it.a)}</p>`);
  }
  if (page.guide) {
    const g = GUIDES[page.guide];
    parts.push(`<h2>Read next</h2><ul>${g.related.map(([to, label]) => `<li><a href="${attr(to)}">${esc(label)}</a></li>`).join("")}</ul>`);
  }
  parts.push(`<p><a href="/download">Download Assignment Monitor</a> · <a href="/faq">FAQ</a> · <a href="/privacy">Privacy &amp; security</a></p>`);
  return `<div class="ssr">${parts.join("")}</div>`;
}

function structured(path, page, full) {
  const url = SITE + (path === "/" ? "/" : path);
  const blocks = [];
  if (path !== "/") {
    const crumbs = [{ "@type": "ListItem", position: 1, name: BASE, item: SITE + "/" }];
    if (path.startsWith("/guide/")) crumbs.push({ "@type": "ListItem", position: 2, name: "Guides", item: SITE + "/guide/bahria-lms-deadlines" });
    crumbs.push({ "@type": "ListItem", position: crumbs.length + 1, name: page.title || full, item: url });
    blocks.push(ld({ "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: crumbs }));
  }
  if (page.faq) {
    blocks.push(ld({ "@context": "https://schema.org", "@type": "FAQPage",
      mainEntity: page.faq.map((it) => ({ "@type": "Question", name: it.q, acceptedAnswer: { "@type": "Answer", text: it.a } })) }));
  }
  if (page.guide) {
    const g = GUIDES[page.guide];
    blocks.push(ld({ "@context": "https://schema.org", "@type": "TechArticle", headline: g.title, description: g.description,
      url, inLanguage: "en", dateModified: g.updated, datePublished: g.updated,
      author: { "@type": "Person", name: "Nobody243", url: "https://github.com/Nobody243" },
      publisher: { "@type": "Organization", name: BASE, url: SITE + "/", logo: { "@type": "ImageObject", url: SITE + "/assets/logo-512.png" } },
      image: SITE + "/assets/og.png?v=3", mainEntityOfPage: url }));
  }
  return blocks.join("\n  ");
}

function render(path, page) {
  const full = page.title ? `${page.title} · ${BASE}` : DEFAULT_TITLE;
  const url = SITE + (path === "/" ? "/" : path);
  let html = shell;
  html = html.replace(/<title>[^<]*<\/title>/, `<title>${esc(full)}</title>`);
  html = setTag(html, { tag: "meta", key: "name", value: "description" }, "content", page.description);
  html = setTag(html, { tag: "link", key: "rel", value: "canonical" }, "href", url);
  html = setTag(html, { tag: "meta", key: "property", value: "og:url" }, "content", url);
  html = setTag(html, { tag: "meta", key: "property", value: "og:title" }, "content", full);
  html = setTag(html, { tag: "meta", key: "property", value: "og:description" }, "content", page.description);
  html = setTag(html, { tag: "meta", key: "name", value: "twitter:title" }, "content", full);
  html = setTag(html, { tag: "meta", key: "name", value: "twitter:description" }, "content", page.description);
  const extra = structured(path, page, full);
  if (extra) html = html.replace("</head>", `  ${extra}\n</head>`);
  // the outline goes after the boot cover inside #root; the cover is opaque and fixed, so it sits on top
  const rootStart = html.indexOf('<div id="root">');
  const rootEnd = html.indexOf("</div></div>", rootStart) + "</div></div>".length;   // end of the boot div
  if (rootStart < 0 || rootEnd < rootStart) throw new Error("root/boot markup not found");
  html = html.slice(0, rootEnd) + outline(page) + html.slice(rootEnd);
  return html;
}

let n = 0;
for (const [path, page] of Object.entries(PAGES)) {
  const p = path === "/faq" ? { ...page, faq: FAQ } : page;
  const out = path === "/" ? resolve(dist, "index.html") : resolve(dist, path.slice(1) + ".html");
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, render(path, p));
  n++;
}
console.log(`prerendered ${n} pages`);
