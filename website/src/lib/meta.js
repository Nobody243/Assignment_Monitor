import { useEffect } from "react";

const BASE = "Assignment Monitor";
/* Per-page title and description. The static OG tags in index.html describe the site as a whole. */
export function usePageMeta(title, description) {
  useEffect(() => {
    document.title = title ? `${title} · ${BASE}` : `${BASE} — never miss a Bahria LMS deadline`;
    const m = document.querySelector('meta[name="description"]');
    if (m && description) m.setAttribute("content", description);
  }, [title, description]);
}
