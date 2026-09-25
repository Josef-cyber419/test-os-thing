"""Loading the home-screen layout from apps.toml.

The defaults live in /usr/share/hearth/apps.toml (shipped in the image, and
updated with it). Your changes go in ~/.config/hearth/apps.toml and are layered
on top, so you keep getting new default tiles after updates:

    hide = ["plex", "android"]        # remove default tiles by id

    [[rows]]
    title = "Watch"                   # same title: add to / change that row
      [[rows.apps]]
      id = "kodi"                     # same id: change just these fields
      color = "#000000"
      [[rows.apps]]
      id = "twitch"                   # new id: a new tile
      name = "Twitch"
      flatpak = "tv.twitch.Twitch"

    [[rows]]
    title = "Mine"                    # new title: a new row, before System

Put `replace = true` at the top to ignore the defaults entirely.
"""

from __future__ import annotations

import glob
import os
import shlex
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

SYSTEM_CONFIG = Path("/usr/share/hearth/apps.toml")


def user_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "hearth" / "apps.toml"


def flatpak_dirs() -> list[Path]:
    return [
        Path("/var/lib/flatpak/app"),
        Path.home() / ".local/share/flatpak/app",
    ]


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class App:
    id: str
    name: str
    command: tuple[str, ...]
    color: str = "#3a3f58"
    icon: str | None = None
    requires: tuple[str, ...] = ()
    requires_files: tuple[str, ...] = ()
    flatpak: str | None = None
    # Ask "are you sure?" before launching (power actions, desktop mode).
    confirm: bool = False
    # Holding the controller's Guide button returns home (off for apps like
    # Steam that use the Guide button themselves).
    home_button: bool = True
    # Keeps running while you use other apps; shown and hidden from the Quick
    # Menu (e.g. Discord). Launching its tile starts it if needed and shows it.
    background: bool = False
    # Controller drives a mouse pointer while this app is in front.
    pointer: bool = False
    # X11 WM_CLASS, to recognise the app's windows if its process can't be traced.
    wm_class: str | None = None
    # Hearth tags the app's windows so gamescope will show them. Off for Steam,
    # which does this itself.
    tag_windows: bool = True

    def missing(self) -> str | None:
        """Why this tile is hidden, or None if it can be shown."""
        if self.flatpak and not any((d / self.flatpak).is_dir() for d in flatpak_dirs()):
            return f"Flatpak {self.flatpak} not installed"
        for pattern in self.requires_files:
            # May be a glob pattern and may start with ~.
            if not glob.glob(os.path.expanduser(pattern)):
                return f"{pattern} not found"
        for command in self.requires:
            if not shutil.which(command):
                return f"command {command} not found"
        return None

    def available(self) -> bool:
        """Hide tiles whose program isn't installed instead of failing on launch."""
        return self.missing() is None


@dataclass(frozen=True)
class Row:
    title: str
    apps: tuple[App, ...]


@dataclass(frozen=True)
class Config:
    title: str = "Hearth"
    rows: tuple[Row, ...] = field(default_factory=tuple)
    # Freeze the game while the Quick Menu is open, like a console's home menu.
    pause_game: bool = True

    def app(self, app_id: str) -> App | None:
        return next((a for row in self.rows for a in row.apps if a.id == app_id), None)

    def visible(self) -> Config:
        """Config with unavailable apps (and rows left empty) removed."""
        rows = []
        for row in self.rows:
            apps = tuple(a for a in row.apps if a.available())
            if apps:
                rows.append(Row(row.title, apps))
        return Config(self.title, tuple(rows), self.pause_game)


def _parse_command(raw: dict, where: str) -> tuple[str, ...]:
    command = raw.get("command")
    flatpak = raw.get("flatpak")
    args = raw.get("args", [])
    if isinstance(args, str):
        args = shlex.split(args)
    if command is None:
        if not flatpak:
            raise ConfigError(f"{where}: needs either 'command' or 'flatpak'")
        return ("flatpak", "run", flatpak, *args)
    if isinstance(command, str):
        command = shlex.split(command)
    if not command or not all(isinstance(c, str) for c in command):
        raise ConfigError(f"{where}: 'command' must be a non-empty string or list of strings")
    return (*command, *args)


def _parse_app(raw: dict, where: str) -> App:
    for key in ("id", "name"):
        if not isinstance(raw.get(key), str) or not raw[key]:
            raise ConfigError(f"{where}: missing '{key}'")
    requires = raw.get("requires", [])
    if isinstance(requires, str):
        requires = [requires]
    requires_files = raw.get("requires_files", [])
    if isinstance(requires_files, str):
        requires_files = [requires_files]
    return App(
        id=raw["id"],
        name=raw["name"],
        command=_parse_command(raw, where),
        color=raw.get("color", App.color),
        icon=raw.get("icon"),
        requires=tuple(requires),
        requires_files=tuple(requires_files),
        flatpak=raw.get("flatpak"),
        confirm=bool(raw.get("confirm", False)),
        home_button=bool(raw.get("home_button", True)),
        background=bool(raw.get("background", False)),
        pointer=bool(raw.get("pointer", False)),
        wm_class=raw.get("wm_class"),
        tag_windows=bool(raw.get("tag_windows", True)),
    )


def parse(data: dict) -> Config:
    rows = []
    seen: set[str] = set()
    for r, raw_row in enumerate(data.get("rows", [])):
        title = raw_row.get("title", "")
        apps = []
        for a, raw_app in enumerate(raw_row.get("apps", [])):
            app = _parse_app(raw_app, f"rows[{r}].apps[{a}]")
            if app.id in seen:
                raise ConfigError(f"duplicate app id '{app.id}'")
            seen.add(app.id)
            apps.append(app)
        rows.append(Row(title, tuple(apps)))
    quick_menu = data.get("quick_menu", {})
    return Config(
        title=data.get("title", "Hearth"),
        rows=tuple(rows),
        pause_game=bool(quick_menu.get("pause_game", True)),
    )


def _read(path: Path) -> dict:
    with open(path, "rb") as f:
        try:
            return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{path}: {e}") from e


def merge(base: dict, user: dict) -> dict:
    """Layer user changes over the defaults (see the module docstring)."""
    if user.get("replace"):
        return user
    merged = {**base, **{k: v for k, v in user.items() if k not in ("rows", "hide", "quick_menu")}}
    merged["quick_menu"] = {**base.get("quick_menu", {}), **user.get("quick_menu", {})}
    rows = [{**r, "apps": [dict(a) for a in r.get("apps", [])]} for r in base.get("rows", [])]
    by_title = {r.get("title"): r for r in rows}
    new_rows = []
    for urow in user.get("rows", []):
        row = by_title.get(urow.get("title"))
        if row is None:
            new_rows.append({**urow, "apps": [dict(a) for a in urow.get("apps", [])]})
            continue
        by_id = {a.get("id"): a for a in row["apps"]}
        for uapp in urow.get("apps", []):
            if uapp.get("id") in by_id:
                by_id[uapp["id"]].update(uapp)
            else:
                row["apps"].append(dict(uapp))
    # New rows go before the last default row (System), which stays last so
    # the Menu button still jumps to it.
    rows = rows[:-1] + new_rows + rows[-1:] if rows else new_rows
    hidden = set(user.get("hide", []))
    for row in rows:
        row["apps"] = [a for a in row["apps"] if a.get("id") not in hidden]
    merged["rows"] = [r for r in rows if r["apps"]]
    return merged


def load(path: Path | None = None) -> Config:
    """An explicit path is used as-is; otherwise defaults + your changes."""
    if path is not None:
        return parse(_read(path))
    user = user_config_path()
    base = _read(SYSTEM_CONFIG) if SYSTEM_CONFIG.exists() else {}
    if user.exists():
        return parse(merge(base, _read(user)))
    return parse(base)
