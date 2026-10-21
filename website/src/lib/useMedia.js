import { useEffect, useState } from "react";

/* Reactive media query: re-renders when the viewport crosses the breakpoint. */
export function useMedia(query) {
  const get = () => (typeof window !== "undefined" ? window.matchMedia(query).matches : false);
  const [match, setMatch] = useState(get);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setMatch(mq.matches);
    on(); mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return match;
}
export const useIsMobile = () => useMedia("(max-width: 900px)");
