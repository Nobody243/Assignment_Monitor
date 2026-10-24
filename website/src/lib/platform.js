/* Platform facts, read once and synchronously so the first paint already shows the right buttons.
   The app runs on Windows 10 and 11 only. Anything else (phones, Macs, Linux, unknown) gets the "send this to
   your PC" path; detection failures keep the normal download buttons, which is the safe default. */
const SITE_URL = "https://assignment-monitor.saaddev.top";

function detectWindows() {
  if (typeof navigator === "undefined") return true;
  const hint = navigator.userAgentData && navigator.userAgentData.platform;
  if (hint) return /windows/i.test(hint);
  const ua = navigator.userAgent || "";
  if (!ua) return true;
  return /Windows NT/i.test(ua) && !/Android|iPhone|iPad|Mobile/i.test(ua);
}

export const IS_WINDOWS = detectWindows();
export const CAN_SHARE = typeof navigator !== "undefined" && typeof navigator.share === "function";
export const SHARE = {
  title: "Assignment Monitor",
  text: "Assignment Monitor for Bahria LMS, Windows app",
  url: `${SITE_URL}/download`,
};
export const PLATFORM_NOTE = "Windows 10 and 11 only. Open this page on your PC to install.";
