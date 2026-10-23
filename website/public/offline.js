/* The offline page's only script (inline scripts are blocked by the site's CSP). Retries on request, and reloads
   on its own the moment the browser reports a connection, after a short check that the site really answers.
   The check fetches a file the service worker never serves from its cache, so a cached copy cannot fake it. */
(function () {
  var status = document.getElementById("status");
  var retry = document.getElementById("retry");
  var busy = false;
  function say(text, live) {
    status.innerHTML = '<span class="dot" aria-hidden="true"></span>' + text;
    status.classList.toggle("is-live", !!live);
  }
  function attempt() {
    if (busy) return;
    busy = true;
    say("Checking…");
    fetch("/robots.txt?offline-check=" + Date.now(), { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error(String(r.status)); say("Back online. Loading the page…", true); setTimeout(function () { location.reload(); }, 400); })
      .catch(function () { busy = false; say("Still offline. Waiting for a connection. The page reloads by itself."); });
  }
  retry.addEventListener("click", attempt);
  window.addEventListener("online", attempt);
  if (navigator.onLine) setTimeout(attempt, 1500);
})();
