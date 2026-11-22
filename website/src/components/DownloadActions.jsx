import React from "react";
import { Link } from "react-router-dom";
import { Button, DownloadButton } from "./Button.jsx";
import { SendToPc } from "./SendToPc.jsx";
import { IS_WINDOWS, IS_ANDROID, PLATFORM_NOTE } from "../lib/platform.js";
import { usePhoneRelease } from "../lib/phoneRelease.js";
import { useRelease, fmtMB } from "../lib/release.jsx";

/* The pair of actions under the hero and in the closing card.
   Windows: installer plus either the portable zip or the guide. Elsewhere: share the link, with a quiet
   "Download anyway" for people who move files to their PC by hand. Nothing is ever blocked. */
export function DownloadActions({ size = "lg", secondary = "zip", showSize = true }) {
  const phone = usePhoneRelease();
  if (IS_ANDROID) {
    return (
      <>
        <Button href={phone.apkUrl} variant="accent" size={size}>Download for Android <small>v{phone.version}</small></Button>
        <Button to="/phone-app" size={size} variant="quiet">How it works</Button>
      </>
    );
  }
  if (!IS_WINDOWS) {
    return (
      <>
        <SendToPc size={size} />
        <Button to="/download" size={size} variant="quiet">Download anyway</Button>
      </>
    );
  }
  return (
    <>
      <DownloadButton kind="setup" size={size} showSize={showSize} />
      {secondary === "zip" && <DownloadButton kind="zip" size={size} showSize={showSize} />}
      {secondary === "guide" && <Button to="/download" size={size}>Download guide</Button>}
    </>
  );
}

/* The quiet alternative under a lone installer button: the portable zip, as a text link. Windows only. */
export function DownloadAlt({ as: Tag = "p", className = "", ...rest }) {
  const rel = useRelease();
  if (!IS_WINDOWS) return null;
  return (
    <Tag className={`hero-alt ${className}`} {...rest}>
      No installer? <Link to="/download#zip">Portable zip{rel.zipSize ? `, ${fmtMB(rel.zipSize)}` : ""}</Link> · On Android? <Link to="/phone-app">Get the phone app</Link>
    </Tag>
  );
}

/* One line under the actions on non-Windows devices; renders nothing on Windows. */
export function PlatformNote({ as: Tag = "p", className = "", ...rest }) {
  if (IS_WINDOWS || IS_ANDROID) return null;
  return <Tag className={`platform-note ${className}`} {...rest}>{PLATFORM_NOTE}</Tag>;
}
