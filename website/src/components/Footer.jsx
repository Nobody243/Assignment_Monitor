import React from "react";
import { Link } from "react-router-dom";
import { useRelease } from "../lib/release.jsx";
import { useScroll } from "../lib/scroll.jsx";
import { LINKS } from "../data/content.js";
import { IS_WINDOWS } from "../lib/platform.js";
import { SendToPc } from "./SendToPc.jsx";
import { DOWNLOAD_PATH } from "./Button.jsx";

const Ext = ({ href, children }) => <a href={href} target="_blank" rel="noopener">{children}</a>;

export default function Footer() {
  const rel = useRelease();
  const { scrollTo } = useScroll();
  return (
    <footer className="footer">
      <p className="footer-mark" aria-hidden="true">Assignment Monitor</p>
      <div className="wrap">
        <div className="footer-top">
          <div className="footer-brand">
            <Link className="brand footer-brand-link" to="/"><img src="/assets/logo.svg?v=2" alt="" width="34" height="34" /><span>Assignment Monitor<small>for Bahria University LMS</small></span></Link>
            <p>A small, honest tool that reads your LMS so you don't have to. Built by a Bahria student, for Bahria students. Free forever, open source, and it never phones home.</p>
            <div className="footer-cta">
              {IS_WINDOWS
                ? <Link className="btn btn-accent" to={DOWNLOAD_PATH.setup} data-download-page="setup">Download <small>v{rel.version}</small></Link>
                : <SendToPc />}
              <a className="btn btn-ghost" href={LINKS.repo} target="_blank" rel="noopener">Star on GitHub</a>
            </div>
          </div>
          <nav className="footer-cols" aria-label="Footer">
            <div><h3>Get it</h3><ul>
              <li><Link to={DOWNLOAD_PATH.setup}>Installer for Windows</Link></li>
              <li><Link to={DOWNLOAD_PATH.zip}>Portable zip</Link></li>
              <li><Link to="/download">Download guide</Link></li>
              <li><Ext href={LINKS.releases}>All releases</Ext></li>
              <li><Ext href={LINKS.readmeSource}>Run from source</Ext></li>
            </ul></div>
            <div><h3>Explore</h3><ul>
              <li><Link to="/#story">Tour</Link></li><li><Link to="/#features">Features</Link></li><li><Link to="/#screens">Screens</Link></li>
              <li><Link to="/faq">FAQ</Link></li><li><Ext href={LINKS.releases}>Release notes</Ext></li>
            </ul></div>
            <div><h3>Project</h3><ul>
              <li><Ext href={LINKS.repo}>Source code</Ext></li>
              <li><Ext href={LINKS.issues}>Report a problem</Ext></li>
              <li><Ext href={LINKS.signing}>Code signing policy</Ext></li>
              <li><Ext href={LINKS.thirdParty}>Third-party licenses</Ext></li>
            </ul></div>
            <div><h3>Legal</h3><ul>
              <li><Link to="/privacy">Privacy &amp; security</Link></li>
              <li><Ext href={LINKS.privacy}>Terms</Ext></li>
              <li><Ext href={LINKS.license}>MIT license</Ext></li>
            </ul></div>
          </nav>
        </div>
        <div className="footer-bottom">
          <p>© {new Date().getFullYear()} Nobody243 · MIT · Made in Pakistan</p>
          <p className="footer-note">Independent, open-source project. Not affiliated with, endorsed by, or supported by Bahria University. Use it with your own account only; deadlines come from the portal and can be out of date, so always confirm on the LMS.</p>
          <button type="button" className="footer-top-link mono" onClick={() => scrollTo(0)}>Back to top ↑</button>
        </div>
      </div>
    </footer>
  );
}
