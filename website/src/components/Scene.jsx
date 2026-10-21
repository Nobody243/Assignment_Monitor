import React, { useEffect, useRef } from "react";
import { useScene } from "../lib/scene.jsx";
import { reduceMotion } from "../lib/scroll.jsx";

/* The one persistent canvas behind every route. The heavy module is imported lazily so the page shell paints first. */
export default function Scene() {
  const ref = useRef(null);
  const scene = useScene();
  useEffect(() => {
    let api = null, cancelled = false;
    import("../scene/planet.js").then(({ createPlanet }) => {
      if (cancelled) return;
      api = createPlanet(ref.current, {
        introActive: !reduceMotion(),
        onProgress: (p) => scene.emit("progress", p),
        onWarm: () => scene.emit("warm"),
        onReady: () => scene.emit("ready"),
      });
      scene.planet.current = api;
      if (scene.introDone) { api.setIntroActive(false); api.startEntry(); }
    });
    return () => { cancelled = true; if (api) api.dispose(); scene.planet.current = null; };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return <canvas id="space" ref={ref} className={scene.introDone ? "is-lit" : ""} aria-hidden="true" />;
}
