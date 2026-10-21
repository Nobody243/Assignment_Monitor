import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8"));

// The site is a single-page React app. The planet (three.js), GSAP and Framer Motion are split into their own
// chunks so the first paint only waits for React and the page shell; the scene streams in behind the intro.
// Hashed bundles go to /bundle (cached forever); static images stay under /assets (cached for a week).
export default defineConfig({
  plugins: [react()],
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
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
