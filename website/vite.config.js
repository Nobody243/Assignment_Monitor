import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";

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
  plugins: [react()],
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
