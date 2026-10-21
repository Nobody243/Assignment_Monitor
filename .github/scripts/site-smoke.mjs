// Headless smoke test of the built website (run from website/ after `npm run preview`).
// Every route must render its h1, the download page must link both release assets, and nothing may 404 or throw.
import { createRequire } from "node:module";
const require = createRequire(process.cwd() + "/");
const { chromium } = require("playwright");
const BASE = process.env.SITE_URL || "http://127.0.0.1:4173";
const b = await chromium.launch();
const errors = [];
const pg = await b.newPage({ reducedMotion: "reduce" });
pg.on("pageerror", (e) => errors.push(String(e)));
pg.on("response", (r) => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
for (const path of ["/", "/download", "/privacy", "/faq", "/nope"]) {
  await pg.goto(BASE + path, { waitUntil: "load" });
  await pg.waitForSelector("main h1", { timeout: 20000 });
  console.log(path, "->", (await pg.textContent("main h1")).trim().slice(0, 60));
}
await pg.goto(BASE + "/download", { waitUntil: "load" });
await pg.waitForSelector("a[data-download]", { timeout: 20000 });
const links = await pg.$$eval("a[data-download]", (as) => as.map((a) => a.href));
if (!links.some((l) => /AssignmentMonitor-Setup\.exe$/.test(l))) throw new Error("installer link missing: " + links.join(", "));
if (!links.some((l) => /AssignmentMonitor-portable\.zip$/.test(l))) throw new Error("zip link missing: " + links.join(", "));
await b.close();
if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
console.log("routes ok, download links ok, no page errors");
