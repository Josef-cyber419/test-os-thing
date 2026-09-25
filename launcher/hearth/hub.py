"""The session hub: home screen -> app -> home screen, forever.

This runs as the client of the Game Mode (gamescope) session. The home screen
releases the display before an app starts so the app gets the whole screen,
then comes back when the app exits.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import time
from pathlib import Path

import pygame

from . import config as cfg
from . import homebutton, ui
from .model import Home

log = logging.getLogger("hearth")

SHIM_DIR = Path("/usr/libexec/hearth/shims")
# An app that dies this quickly with an error most likely failed to start.
QUICK_FAIL_SECONDS = 3
# Grace period between asking an app to quit and killing it.
TERM_TIMEOUT_SECONDS = 5


def app_env() -> dict[str, str]:
    env = dict(os.environ)
    # Shims (e.g. steamos-session-select) make "exit" inside apps land back home.
    if SHIM_DIR.is_dir():
        env["PATH"] = f"{SHIM_DIR}:{env.get('PATH', '')}"
    env["HEARTH_SESSION"] = "1"
    return env


def launch(app: cfg.App, dry_run: bool = False) -> str | None:
    """Run an app to completion. Returns an error message for the home screen."""
    log.info("launching %s: %s", app.id, " ".join(app.command))
    if dry_run:
        print("would run:", " ".join(app.command), flush=True)
        return None
    started = time.monotonic()
    try:
        # Own process group, so "go home" can close the app and all its children.
        proc = subprocess.Popen(app.command, env=app_env(), start_new_session=True)
    except OSError as e:
        log.error("failed to start %s: %s", app.id, e)
        return f"Couldn't start {app.name}: {e.strerror or e}"

    sent_home = False

    def go_home() -> None:
        nonlocal sent_home
        sent_home = True
        stop_process_group(proc)

    watcher = homebutton.Watcher(go_home) if app.home_button else None
    if watcher:
        watcher.start()
    try:
        returncode = proc.wait()
    finally:
        if watcher:
            watcher.stop()
    if sent_home:
        return None
    elapsed = time.monotonic() - started
    log.info("%s exited with %s after %.1fs", app.id, returncode, elapsed)
    if returncode != 0 and elapsed < QUICK_FAIL_SECONDS:
        return f"{app.name} closed unexpectedly (exit code {returncode})"
    return None


def stop_process_group(proc: subprocess.Popen) -> None:
    """SIGTERM the app's process group, then SIGKILL if it doesn't exit."""

    def signal_group(sig: int) -> None:
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            pass

    signal_group(signal.SIGTERM)
    try:
        proc.wait(timeout=TERM_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        signal_group(signal.SIGKILL)


def open_display(windowed: bool) -> pygame.Surface:
    pygame.display.init()
    pygame.font.init()
    pygame.joystick.init()
    pygame.display.set_caption("Hearth")
    pygame.mouse.set_visible(windowed)
    if windowed:
        return pygame.display.set_mode((1280, 720))
    return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hearth", description="Hearth TV home screen")
    parser.add_argument("--config", type=Path, help="apps.toml to use (default: user, then system)")
    parser.add_argument("--windowed", action="store_true", help="run in a 1280x720 window (development)")
    parser.add_argument("--dry-run", action="store_true", help="print commands instead of running them")
    parser.add_argument("--show-all", action="store_true", help="show tiles even if the app isn't installed")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="hearth: %(message)s")

    dev_mode = args.windowed or args.dry_run
    last_id: str | None = None
    message: str | None = None
    while True:
        try:
            config = cfg.load(args.config)
        except (OSError, cfg.ConfigError) as e:
            log.error("config: %s", e)
            config = cfg.Config(rows=())
            message = f"Config error: {e}"
        if not args.show_all:
            config = config.visible()

        home = Home(config)
        if last_id:
            home.select_id(last_id)

        surface = open_display(args.windowed)
        app = ui.run(surface, home, config.title, message=message, allow_quit=dev_mode)
        # Release the screen (and input devices) so the app gets them.
        pygame.quit()

        if app is None:
            return 0
        last_id = app.id
        message = launch(app, dry_run=args.dry_run)
