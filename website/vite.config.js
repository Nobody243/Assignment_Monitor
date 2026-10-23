import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { copyFileSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

// Vercel serves dist/404.html with a real 404 status for any path that is not a file and not a listed route
// (see vercel.json). It is a copy of index.html, so the React app boots and shows its own "lost in orbit" page,
// planet and all, while crawlers get the right status instead of a soft 404.
const notFoundPage = () => {
  let out = "dist";
  return {
    name: "am-404-page", apply: "build",
    configResolved(c) { out = resolve(c.root, c.build.outDir); },
    closeBundle() { copyFileSync(resolve(out, "index.html"), resolve(out, "404.html")); },
  };
};

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8"));
// The version shown before (or without) the GitHub release lookup is the app's own, read from config.py in the
// repository root, so the two can never drift; package.json is the fallback when the site is built on its own.
let appVersion = pkg.version;
try {
  const cfg = readFileSync(new URL("../config.py", import.meta.url), "utf8");
  const m = cfg.match(/^APP_VERSION\s*=\s*"([^"]+)"/m);
  if (m) appVersion = m[1];
} catch { /* built outside the repository */ }

// The site is a single-page React app. The planet (three.js), GSAP and Framer Motion are split into their own
// chunks so the first paint only waits for React and the page shell; the scene streams in behind the intro.
// Hashed bundles go to /bundle (cached forever); static images stay under /assets (cached for a week).
export default defineConfig({
  plugins: [react(), notFoundPage()],
  define: { __APP_VERSION__: JSON.stringify(appVersion) },
  build: {
    target: "es2020",
    sourcemap: false,
    assetsDir: "bundle",
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          motion: ["framer-motion", "gsap", "gsap/ScrollTrigger", "lenis"],
          three: ["three"],
        },
      },
    },
  },
});
