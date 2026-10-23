import React, { useEffect, useRef, useState } from "react";
import { useScene } from "../lib/scene.jsx";
import { reduceMotion } from "../lib/scroll.jsx";

/* The one persistent canvas behind every route. The heavy module is imported lazily so the page shell paints first.
   If the scene cannot start (no WebGL, a blocked or missing chunk after a deploy, a driver that throws), the canvas
   falls back to a painted limb of the planet and the intro is told the scene is ready so it opens without delay. */
export default function Scene() {
  const ref = useRef(null);
  const scene = useScene();
  const [fallback, setFallback] = useState(false);
  useEffect(() => {
    let api = null, cancelled = false;
    const fail = (err) => {
      if (cancelled) return;
      console.warn("planet unavailable, using the painted fallback", err);
      setFallback(true);
      document.documentElement.classList.add("no-scene");
      scene.emit("warm"); scene.emit("progress", 1); scene.emit("ready");
    };
    import("../scene/planet.js").then(({ createPlanet }) => {
      if (cancelled) return;
      try {
        api = createPlanet(ref.current, {
          introActive: !reduceMotion(),
          onProgress: (p) => scene.emit("progress", p),
          onWarm: () => scene.emit("warm"),
          onReady: () => scene.emit("ready"),
        });
      } catch (err) { fail(err); return; }
      scene.planet.current = api;
      if (scene.introDone) { api.setIntroActive(false); api.startEntry(); }
    }).catch(fail);
    return () => { cancelled = true; if (api) api.dispose(); scene.planet.current = null; };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return <canvas id="space" ref={ref} className={`${scene.introDone ? "is-lit" : ""}${fallback ? " is-fallback" : ""}`} aria-hidden="true" />;
}
