"""System tray icon so the app can keep running in the background."""
import logging
from pathlib import Path

log = logging.getLogger("bahria.tray")


class TrayIcon:
    """Thin wrapper over pystray. Callbacks are invoked on the tray thread, so the
    caller must marshal them back to the Tk main loop (the app does this with after())."""

    def __init__(self, name: str, icon_path: Path, on_open, on_sync, on_quit):
        import pystray
        from PIL import Image
        try:
            image = Image.open(icon_path)
            image.load()
        except Exception:
            image = Image.new("RGB", (64, 64), "#2563eb")
        menu = pystray.Menu(
            pystray.MenuItem(f"Open {name}", lambda icon, item: on_open(), default=True),
            pystray.MenuItem("Sync now", lambda icon, item: on_sync()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda icon, item: on_quit()),
        )
        self.icon = pystray.Icon(name.replace(" ", ""), image, name, menu)
        self._running = False

    def start(self):
        if not self._running:
            self.icon.run_detached()
            self._running = True

    def stop(self):
        if self._running:
            try:
                self.icon.stop()
            except Exception as e:
                log.debug("Tray stop: %s", e)
            self._running = False

    def set_tooltip(self, text: str):
        try:
            self.icon.title = text[:127]
        except Exception:
            pass

    def notify(self, message: str, title: str = None):
        try:
            self.icon.notify(message, title)
        except Exception:
            pass
