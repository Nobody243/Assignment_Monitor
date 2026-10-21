import React from "react";
import { usePageMeta } from "../lib/meta.js";
import { PageHero } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";

export default function NotFound() {
  usePageMeta("Not found", "That page does not exist.");
  return (
    <PageHero kicker="404" title={<>Lost in <span className="serif accent">orbit.</span></>} lede="That page does not exist. The planet, however, is right where you left it.">
      <Button to="/" variant="accent">Back home</Button>
      <Button to="/download">Download</Button>
    </PageHero>
  );
}
