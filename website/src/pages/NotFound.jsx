import React from "react";
import { usePageMeta } from "../lib/meta.js";
import { PageHero } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";

export default function NotFound() {
  usePageMeta("Not found", "That page does not exist.", { noindex: true });
  return (
    <>
      <PageHero kicker="404" title={<>Lost in <span className="heading-accent">orbit.</span></>} lede="That page does not exist. The planet, however, is right where you left it.">
        <Button to="/" variant="accent">Back home</Button>
        <Button to="/download">Download</Button>
      </PageHero>
      <h2 className="sr-only">Where to go instead</h2>
    </>
  );
}
