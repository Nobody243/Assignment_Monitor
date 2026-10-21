import React from "react";
import { Button, DownloadButton } from "./Button.jsx";
import { SendToPc } from "./SendToPc.jsx";
import { IS_WINDOWS, PLATFORM_NOTE } from "../lib/platform.js";

/* The pair of actions under the hero and in the closing card.
   Windows: installer plus either the portable zip or the guide. Elsewhere: share the link, with a quiet
   "Download anyway" for people who move files to their PC by hand. Nothing is ever blocked. */
export function DownloadActions({ size = "lg", secondary = "zip", showSize = true }) {
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
      {secondary === "zip"
        ? <DownloadButton kind="zip" size={size} showSize={showSize} />
        : <Button to="/download" size={size}>Download guide</Button>}
    </>
  );
}

/* One line under the actions on non-Windows devices; renders nothing on Windows. */
export function PlatformNote({ as: Tag = "p", className = "", ...rest }) {
  if (IS_WINDOWS) return null;
  return <Tag className={`platform-note ${className}`} {...rest}>{PLATFORM_NOTE}</Tag>;
}
