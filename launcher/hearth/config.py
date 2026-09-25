"""Loading the home-screen layout from apps.toml.

The system default lives in /usr/share/hearth/apps.toml (shipped in the image).
A user copy at ~/.config/hearth/apps.toml fully replaces it, so customising the
home screen never requires rebuilding the OS image.
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

    def available(self) -> bool:
        """Hide tiles whose program isn't installed instead of failing on launch."""
        if self.flatpak and not any((d / self.flatpak).is_dir() for d in flatpak_dirs()):
            return False
        # Each entry may be a glob pattern and may start with ~.
        if not all(glob.glob(os.path.expanduser(f)) for f in self.requires_files):
            return False
        return all(shutil.which(req) for req in self.requires)


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


def load(path: Path | None = None) -> Config:
    if path is None:
        user = user_config_path()
        path = user if user.exists() else SYSTEM_CONFIG
    with open(path, "rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{path}: {e}") from e
    return parse(data)
