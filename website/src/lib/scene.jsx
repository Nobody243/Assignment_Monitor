import React, { createContext, useContext, useMemo, useRef, useState } from "react";

/* A tiny event bus between the WebGL scene, the intro and the pages:
   progress (0..1 of assets loaded), warm (shaders compiled), ready (planet renderable), introDone (iris opened). */
const Ctx = createContext(null);

export function SceneProvider({ children }) {
  const listeners = useRef(new Map());
  const [introDone, setIntroDone] = useState(false);
  const planet = useRef(null);                              // the scene api once the canvas has mounted
  const api = useMemo(() => ({
    on: (name, fn) => {
      if (!listeners.current.has(name)) listeners.current.set(name, new Set());
      listeners.current.get(name).add(fn);
      return () => listeners.current.get(name)?.delete(fn);
    },
    emit: (name, payload) => { listeners.current.get(name)?.forEach((fn) => fn(payload)); },
    planet,
    introDone,
    finishIntro: () => { setIntroDone(true); planet.current?.startEntry(); planet.current?.setIntroActive(false); listeners.current.get("introDone")?.forEach((fn) => fn()); },
  }), [introDone]);
  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
}

export const useScene = () => useContext(Ctx);
