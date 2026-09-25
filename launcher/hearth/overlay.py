"""The Quick Menu overlay: a long-running companion to the hub.

- Tap Guide (or a remote's Menu key) anywhere: the Quick Menu slides in over
  the current app, which is paused while it's open (configurable).
- Hold Guide while a background app (Discord) is in front: back to the game.
- Tags new windows with their app's ID so gamescope will show them.
- While a background app with `pointer = true` is in front, the controller
  drives a mouse pointer.

Started by the hub (`python -m hearth.overlay`); safe to restart any time.
"""

from __future__ import annotations

import argparse
import logging
import os
import queue
import subprocess
import time
from pathlib import Path

from . import config as cfg
from . import homebutton, session
from .audio import Audio, Snapshot
from .gamescope import Gamescope, appid_for

log = logging.getLogger("hearth")

TITLE = "Hearth Quick Menu"
ANIM_SECONDS = 0.22
REFRESH_SECONDS = 1.5
HOUSEKEEPING_SECONDS = 0.5
# Without real transparency, the whole overlay is drawn at this opacity.
FALLBACK_OPACITY = 0.93


class Actions:
    """What Quick Menu entries do. Each returns "close" to close the menu."""

    def __init__(self, overlay: "Overlay") -> None:
        self.o = overlay

    def resume(self):
        return "close"

    def go_home(self):
        fg = session.read()["foreground"]
        if fg:
            self.o.thaw()
            session.stop_entry(fg)
        return "close"

    def start_background(self, app_id):
        app = self.o.config.app(app_id)
        if app is None:
            return None
        session.start_background(app)
        return self.show(app_id)

    def show(self, target):
        state = session.update(lambda s: s.__setitem__("focus", target))
        self.o.apply_focus(state)
        return "close"

    def stop_background(self, app_id):
        def change(s):
            info = s["background"].pop(app_id, None)
            if info:
                session.stop_entry(info)
            if s["focus"] == app_id:
                s["focus"] = "foreground" if s["foreground"] else "home"

        self.o.apply_focus(session.update(change))
        self.o.refresh(force=True)
        return None

    def power(self, action):
        self.o.thaw()
        subprocess.Popen(["systemctl", action])
        return "close"


class Overlay:
    def __init__(self, config: cfg.Config, gs: Gamescope | None, window, renderer, xwin, transparent: bool) -> None:
        import pygame

        from .input import InputMapper
        from .pointer import Pointer, make_uinput
        from .quickmenu import QuickMenu
        from .quickmenu_view import QuickMenuView

        self.pg = pygame
        self.config = config
        self.gs, self.window, self.renderer, self.xwin = gs, window, renderer, xwin
        self.transparent = transparent
        self.audio = Audio()
        self.actions = Actions(self)
        self.menu = QuickMenu([])
        self.mapper = InputMapper()
        self.mapper.open_devices()
        self.pointer = Pointer(make_uinput())
        self.pointer_active = False

        size = window.size
        # Draw at up to 1080p and let the GPU scale: keeps 4K fast.
        scale = min(1.0, 1080 / size[1])
        self.size = size
        self.render_size = (int(size[0] * scale), int(size[1] * scale))
        self.surface = pygame.Surface(self.render_size, pygame.SRCALPHA)
        self.view = QuickMenuView(self.render_size)

        self.open = False
        self.t = 0.0
        self.paused_unit: str | None = None
        self.opened_for: str | None = None
        self.state = session.read()
        self._refreshed = 0.0
        self._housekept = 0.0
        self._seen: set[int] = set()
        self._tries: dict[int, int] = {}

        self.events: queue.Queue[str] = queue.Queue()
        homebutton.Watcher(lambda: self.events.put("tap"), homebutton.GuideTap, repeat=True).start()
        homebutton.Watcher(lambda: self.events.put("hold"), homebutton.HomeButton, repeat=True).start()

    # -- state -----------------------------------------------------------------

    def title(self) -> str:
        s = self.state
        if s["focus"] in s["background"]:
            return s["background"][s["focus"]]["name"]
        return (s["foreground"] or {}).get("name") or "Home"

    def apply_focus(self, state: dict) -> None:
        self.state = state
        if self.gs:
            self.gs.show_app(session.focus_appid(state))

    def refresh(self, force: bool = False) -> None:
        from .quickmenu import Context, build_tabs

        now = time.monotonic()
        if not force and now - self._refreshed < REFRESH_SECONDS:
            return
        self._refreshed = now
        self.state = session.read()
        try:
            snapshot = self.audio.snapshot()
        except (OSError, RuntimeError, ValueError) as e:
            log.info("audio unavailable: %s", e)
            snapshot = Snapshot()
        discord = self.config.app("discord")
        ctx = Context(self.audio, snapshot, self.state, self.actions,
                      discord_available=bool(discord and discord.available()))
        self.menu.set_tabs(build_tabs(ctx))

    # -- pause -----------------------------------------------------------------

    def freeze(self) -> None:
        fg = self.state["foreground"]
        if (self.config.pause_game and fg and fg.get("unit") and fg.get("home_button", True)
                and self.state["focus"] == "foreground" and session.freeze(fg["unit"])):
            self.paused_unit = fg["unit"]

    def thaw(self) -> None:
        if self.paused_unit:
            session.thaw(self.paused_unit)
            self.paused_unit = None

    # -- open/close ------------------------------------------------------------

    def open_menu(self) -> None:
        self.state = session.read()
        fg = self.state["foreground"]
        if fg and not fg.get("home_button", True) and self.state["focus"] == "foreground":
            return  # Steam: the Guide button opens Steam's own menu
        self.refresh(force=True)
        self.freeze()
        session.update(lambda s: s.update(overlay_open=True, paused=bool(self.paused_unit)))
        self.opened_for = (fg or {}).get("id")
        self.open = True
        self.pointer.reset()
        if self.gs and self.xwin:
            self.gs.set_overlay_visible(self.xwin, True, 1.0 if self.transparent else FALLBACK_OPACITY)

    def close_menu(self) -> None:
        self.open = False  # the slide-out animation finishes in run()

    def _hidden(self) -> None:
        if self.gs and self.xwin:
            self.gs.set_overlay_visible(self.xwin, False)
        self.thaw()
        session.update(lambda s: s.update(overlay_open=False, paused=False))

    # -- background work -------------------------------------------------------

    def housekeeping(self) -> None:
        now = time.monotonic()
        if now - self._housekept < HOUSEKEEPING_SECONDS:
            return
        self._housekept = now
        self.state = session.read()

        dead = [k for k, info in self.state["background"].items() if not session.background_alive(info)]
        if dead:
            def drop(s):
                for k in dead:
                    s["background"].pop(k, None)
                if s["focus"] in dead:
                    s["focus"] = "foreground" if s["foreground"] else "home"

            self.apply_focus(session.update(drop))

        # The app closed under the open menu (e.g. held Guide): close the menu.
        if self.open and (self.state["foreground"] or {}).get("id") != self.opened_for:
            self.paused_unit = None
            self.close_menu()

        focus = self.state["focus"]
        self.pointer_active = (not self.open and focus in self.state["background"]
                               and self.state["background"][focus].get("pointer", False))
        if not self.pointer_active:
            self.pointer.reset()
        self.tag_windows()

    def tag_windows(self) -> None:
        if not self.gs:
            return
        from Xlib import X
        from Xlib.error import XError

        present = set()
        for win in self.gs.top_level_windows():
            present.add(win.id)
            if win.id in self._seen or (self.xwin and win.id == self.xwin.id):
                continue
            try:
                if win.get_attributes().map_state != X.IsViewable:
                    continue
                if self.gs.is_tagged(win):
                    self._seen.add(win.id)
                    continue
                appid = self.owner_appid(win)
            except XError:
                continue
            if appid is None:
                # Not ours (yet): check again a few times, then leave it alone.
                self._tries[win.id] = self._tries.get(win.id, 0) + 1
                if self._tries[win.id] > 20:
                    self._seen.add(win.id)
                continue
            self.gs.tag(win, appid)
            self._seen.add(win.id)
        self._seen &= present
        self._tries = {k: v for k, v in self._tries.items() if k in present}

    def owner_appid(self, win) -> int | None:
        state = self.state
        pid = self.gs.client_pid(win)
        owner = session.app_for_pid(pid) if pid else None
        fg = state["foreground"]
        if owner:
            kind, app_id = owner
            if kind == "app" and fg and fg["id"] == app_id and not fg.get("tag_windows", True):
                self._seen.add(win.id)  # Steam tags its own windows
                return None
            return appid_for(app_id)
        wm_class = [c.lower() for c in (self.gs.wm_class(win) or ())]
        for app_id, info in state["background"].items():
            if info.get("wm_class") and info["wm_class"].lower() in wm_class:
                return appid_for(app_id)
        if fg and fg.get("tag_windows", True):
            return appid_for(fg["id"])
        return None

    # -- main loop -------------------------------------------------------------

    def handle_events(self) -> None:
        from .model import Nav

        while not self.events.empty():
            kind = self.events.get()
            if kind == "tap":
                self.close_menu() if self.open else self.open_menu()
            elif kind == "hold" and not self.open:
                state = session.read()
                if state["focus"] in state["background"]:
                    back = "foreground" if state["foreground"] else "home"
                    self.apply_focus(session.update(lambda s: s.__setitem__("focus", back)))

        now = self.pg.time.get_ticks()
        navs = []
        for event in self.pg.event.get():
            if event.type == self.pg.CONTROLLERBUTTONDOWN and event.button == self.pg.CONTROLLER_BUTTON_GUIDE:
                continue  # Guide taps arrive via the watcher; don't also handle them here
            nav = self.mapper.translate(event, now)
            if self.open and nav is not None:
                navs.append(nav)
            elif self.pointer_active:
                self.pointer.handle(event)
        if self.open:
            repeat = self.mapper.repeat(now)
            if repeat is not None:
                navs.append(repeat)
        for nav in navs:
            if nav is Nav.MENU:  # Start closes the menu, like B
                nav = Nav.BACK
            if self.menu.handle(nav) == "close":
                self.close_menu()
                break
            self._refreshed = 0  # show the change's effect right away
            self.refresh()

    def draw(self) -> None:
        r = self.renderer
        if self.open:
            self.refresh()
        paused = bool(self.paused_unit)
        if not self.transparent:
            # No per-pixel alpha: the whole window is semi-opaque instead.
            self.surface.fill((0, 0, 0, 255))
        self.view.draw(self.surface, self.menu, self.title(), paused, self.t)
        try:
            frame = self.surface.premul_alpha()
        except AttributeError:  # older pygame
            frame = self.surface
        from pygame._sdl2 import video

        tex = video.Texture.from_surface(r, frame)
        tex.blend_mode = 0  # copy pixels (already premultiplied) as they are
        r.draw_color = (0, 0, 0, 0)
        r.clear()
        tex.draw(dstrect=(0, 0, *self.size))
        r.present()

    def run(self) -> None:
        clock = self.pg.time.Clock()
        while True:
            self.handle_events()
            self.housekeeping()
            target = 1.0 if self.open else 0.0
            if self.t != target or self.open:
                step = clock.get_time() / 1000 / ANIM_SECONDS
                self.t = min(target, self.t + step) if target > self.t else max(target, self.t - step)
                self.draw()
                if self.t == 0.0 and not self.open:
                    self._hidden()
                clock.tick(60)
            elif self.pointer_active:
                self.pointer.tick(clock.get_time() / 1000)
                clock.tick(120)
            else:
                clock.tick(20)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hearth-overlay", description="Hearth Quick Menu overlay")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="hearth-overlay: %(message)s")

    gs = Gamescope.connect()
    visual = gs.argb_visual() if gs else None
    if visual:
        os.environ["SDL_VIDEO_X11_VISUALID"] = hex(visual)
    os.environ.setdefault("SDL_VIDEODRIVER", "x11")
    # Controller input keeps flowing while another app has focus (pointer
    # mode); while the menu is open, gamescope gives this window the focus.
    os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
    os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    import pygame
    from pygame._sdl2 import video

    pygame.display.init()
    pygame.font.init()
    pygame.joystick.init()
    size = pygame.display.get_desktop_sizes()[0]
    window = video.Window(TITLE, size=size, position=(0, 0), borderless=True, hidden=True)
    renderer = video.Renderer(window)
    xwin = gs.find_window(TITLE) if gs else None
    if gs and xwin:
        gs.make_overlay(xwin)
    else:
        log.warning("not running under gamescope/X11: the Quick Menu can't be shown over apps")
    window.show()

    config = cfg.load(args.config)
    overlay = Overlay(config, gs, window, renderer, xwin, transparent=visual is not None)
    try:
        overlay.run()
    finally:
        overlay.thaw()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
