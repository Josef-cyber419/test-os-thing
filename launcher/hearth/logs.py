"""Logging for the hub and the overlay: to the journal (stderr) and to a
rotating file that's easy to read from Desktop Mode or `hearthctl logs`."""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path


def log_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local/state")
    return Path(base) / "hearth" / "hearth.log"


def setup(role: str, level: int | None = None) -> Path:
    """HEARTH_LOG_LEVEL=debug in the environment logs every input action."""
    if level is None:
        level = getattr(logging, os.environ.get("HEARTH_LOG_LEVEL", "info").upper(), logging.INFO)
    path = log_path()
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    stderr = logging.StreamHandler()
    stderr.setFormatter(logging.Formatter(f"hearth-{role}: %(levelname)s %(message)s"))
    root.addHandler(stderr)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        file = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3)
        file.setFormatter(logging.Formatter(f"%(asctime)s {role:<7} %(levelname)-7s %(message)s"))
        root.addHandler(file)
    except OSError as e:
        root.warning("can't write %s: %s", path, e)

    def excepthook(kind, value, tb):
        logging.getLogger("hearth").critical("crashed", exc_info=(kind, value, tb))
        sys.__excepthook__(kind, value, tb)

    sys.excepthook = excepthook
    return path
