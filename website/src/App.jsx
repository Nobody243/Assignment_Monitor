import React, { useEffect } from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { ScrollProvider, useScroll } from "./lib/scroll.jsx";
import { ReleaseProvider } from "./lib/release.jsx";
import { SceneProvider } from "./lib/scene.jsx";
import Scene from "./components/Scene.jsx";
import Intro from "./components/Intro.jsx";
import Nav from "./components/Nav.jsx";
import Footer from "./components/Footer.jsx";
import Page from "./components/Page.jsx";
import Home from "./pages/Home.jsx";
import Download from "./pages/Download.jsx";
import Privacy from "./pages/Privacy.jsx";
import Faq from "./pages/Faq.jsx";
import NotFound from "./pages/NotFound.jsx";

/* Every route change starts at the top (unless the URL carries a hash, which the page scrolls to itself). */
function ScrollToTop() {
  const { pathname, hash } = useLocation();
  const { scrollTo } = useScroll();
  useEffect(() => { if (!hash) scrollTo(0, { immediate: true }); }, [pathname]);   // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

export default function App() {
  const location = useLocation();
  return (
    <ScrollProvider>
      <ReleaseProvider>
        <SceneProvider>
          <Scene />
          <Intro />
          <Nav />
          <ScrollToTop />
          <AnimatePresence mode="wait" initial={false}>
            <Routes location={location} key={location.pathname}>
              <Route path="/" element={<Page><Home /></Page>} />
              <Route path="/download" element={<Page><Download /></Page>} />
              <Route path="/privacy" element={<Page><Privacy /></Page>} />
              <Route path="/faq" element={<Page><Faq /></Page>} />
              <Route path="*" element={<Page><NotFound /></Page>} />
            </Routes>
          </AnimatePresence>
          <Footer />
        </SceneProvider>
      </ReleaseProvider>
    </ScrollProvider>
  );
}
