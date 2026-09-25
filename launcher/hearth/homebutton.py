"""Return to the home screen from any app: hold the controller's Guide button,
or press a remote's Home key.

Reads input devices directly with python-evdev (read-only, no grab), so it
works whatever app has focus. Optional: without evdev this is a no-op.
"""

from __future__ import annotations

import logging
import selectors
import threading
import time
from typing import Callable

log = logging.getLogger("hearth")

HOLD_SECONDS = 1.5

# Linux input event codes (linux/input-event-codes.h).
BTN_MODE = 0x13C  # Guide / Xbox / PS button
KEY_HOMEPAGE = 172  # "Home" key on media remotes and FLIRC
HOLD_KEYS = {BTN_MODE}
TAP_KEYS = {KEY_HOMEPAGE}
EV_KEY = 0x01

try:
    import evdev
except ImportError:  # pragma: no cover - depends on the system
    evdev = None


class HomeButton:
    """Tracks key state; decides when a "go home" gesture happened."""

    def __init__(self, hold_seconds: float = HOLD_SECONDS) -> None:
        self.hold_seconds = hold_seconds
        self._held_since: float | None = None

    def key(self, code: int, value: int, now: float) -> bool:
        """Feed a key event (value 1=down, 0=up, 2=repeat). True = go home."""
        if code in TAP_KEYS and value == 1:
            return True
        if code in HOLD_KEYS:
            if value == 1:
                self._held_since = now
            elif value == 0:
                self._held_since = None
        return self.tick(now)

    def tick(self, now: float) -> bool:
        if self._held_since is not None and now - self._held_since >= self.hold_seconds:
            self._held_since = None
            return True
        return False


class Watcher(threading.Thread):
    def __init__(self, on_home: Callable[[], None]) -> None:
        super().__init__(daemon=True, name="hearth-home-button")
        self.on_home = on_home
        self._stopping = threading.Event()

    def stop(self) -> None:
        self._stopping.set()

    def run(self) -> None:
        if evdev is None:
            return
        sel = selectors.DefaultSelector()
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                keys = set(dev.capabilities().get(EV_KEY, []))
            except OSError:
                continue
            if keys & (HOLD_KEYS | TAP_KEYS):
                sel.register(dev, selectors.EVENT_READ)
            else:
                dev.close()
        if not sel.get_map():
            log.info("home button: no Guide/Home capable devices found")
            return

        button = HomeButton()
        try:
            while not self._stopping.is_set():
                for key, _ in sel.select(timeout=0.1):
                    try:
                        events = list(key.fileobj.read())
                    except OSError:  # device unplugged
                        sel.unregister(key.fileobj)
                        continue
                    for ev in events:
                        if ev.type == EV_KEY and button.key(ev.code, ev.value, time.monotonic()):
                            self._fire()
                            return
                if button.tick(time.monotonic()):
                    self._fire()
                    return
        finally:
            for key in list(sel.get_map().values()):
                key.fileobj.close()
            sel.close()

    def _fire(self) -> None:
        if not self._stopping.is_set():
            log.info("home button pressed: returning to home screen")
            self.on_home()
