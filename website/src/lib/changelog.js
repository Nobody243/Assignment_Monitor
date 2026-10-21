import raw from "../../../CHANGELOG.md?raw";

/* CHANGELOG.md is bundled at build time, so the site always describes the version the repository ships. */
export function parseChangelog(text = raw) {
  const out = [];
  let cur = null;
  text.split(/\r?\n/).forEach((line) => {
    const h = line.match(/^## (\S+)(?: - (.+))?$/);
    if (h) { cur = { version: h[1], date: h[2] || "", items: [] }; out.push(cur); return; }
    const b = line.match(/^- (.+)$/);
    if (b && cur) cur.items.push(b[1]);
  });
  return out;
}
export const CHANGELOG = parseChangelog();
