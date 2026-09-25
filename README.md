# Hearth OS

A living-room PC that behaves like a smart TV and a console at the same time.

Power it on and you land on a **TV-style home screen**, driven by a controller or
your TV remote. Pick **Steam** to get the full Steam Deck-style console UI, or go
straight to **emulation, Kodi, YouTube, Jellyfin, Plex, Moonlight**, and more.
Close the app and you're back home. Every app on the home screen is chosen to
work with just a controller or a TV remote, with no keyboard or mouse needed.

```
 power on ──► Hearth home screen ──► Steam (Big Picture / Game Mode)
                 ▲      │       ├──► Emulation (RetroDECK: ES-DE + emulators)
                 │      │       ├──► Kodi · YouTube · Jellyfin · Plex · Android
                 │      │       ├──► Moonlight (stream from another PC)
                 │      │       └──► Desktop Mode (KDE Plasma)
                 └──────┘  app exits, or hold the Guide button
```

## How it's built

Hearth doesn't write an OS from scratch. It **orchestrates** existing pieces:

| Layer | What | Why |
|---|---|---|
| Base OS | [Bazzite](https://bazzite.gg) (`bazzite-deck`), Fedora Atomic | Gaming drivers, Steam, gamescope, HDR/VRR, controller support, atomic updates with rollback |
| Image | [`Containerfile`](Containerfile) | Hearth *is* a container image layered on Bazzite, built by CI and installed with `bootc switch` |
| Session | [`/etc/gamescope-session-plus/sessions.d/`](image/system_files/etc/gamescope-session-plus/sessions.d) | Hearth replaces Steam as the first app in Bazzite's Game Mode and keeps every Game Mode setting |
| Home screen | [`launcher/`](launcher) (Python + SDL2) | 10-foot UI, gamepad/remote/keyboard input, runs apps and returns home |
| Apps | Flatpaks + small scripts in [`/usr/libexec/hearth`](image/system_files/usr/libexec/hearth) | Kodi, RetroDECK, Moonlight, VacuumTube (YouTube's TV interface), Jellyfin and Plex in TV mode |
| Extras | HDMI-CEC, first-boot app installer | See below |

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Features

- **TV home screen**: rows of tiles (Play / Watch / System), clock, confirm
  dialogs for power actions. Scales cleanly from 720p to 4K.
- **Works with anything you hold**: Xbox/PlayStation/8BitDo controllers (SDL
  GameController mappings), TV remotes over HDMI-CEC, IR remotes via FLIRC, and
  keyboards.
- **Always a way home**: hold the controller's **Guide** button for 1.5s, or
  press **Home** on a remote, to close the current app and return. In Steam, use
  *Power → Switch to Desktop*, which Hearth turns into "back to home".
- **Remote-friendly apps only**: every default tile uses a TV/console interface
  (see [Streaming services](docs/STREAMING.md) for why Netflix and similar
  services aren't there, and the options for adding them).
- **Your TV follows the PC**: with a CEC adapter, the TV turns on and switches
  input when the PC wakes, and goes to standby when it sleeps.
- **Customisable without rebuilding**: copy
  [`apps.toml`](image/system_files/usr/share/hearth/apps.toml) to
  `~/.config/hearth/apps.toml` and edit. Tiles for apps that aren't installed are
  hidden automatically.
- **Atomic and reversible**: every update is a new image; roll back from the boot
  menu or with `sudo bootc rollback`.

## Getting started

1. **Hardware**: see [docs/HARDWARE.md](docs/HARDWARE.md). An AMD GPU and a
   Pulse-Eight CEC adapter or FLIRC make the biggest difference.
2. **Install**: see [docs/INSTALL.md](docs/INSTALL.md). You install Bazzite, then
   switch it to the Hearth image with one command. Dual-boot setup is covered there too.

### Try the home screen on any Linux or macOS machine

```sh
cd launcher
pip install -e '.[dev]'
python -m hearth --windowed --dry-run --show-all \
    --config ../image/system_files/usr/share/hearth/apps.toml
```

`--dry-run` prints commands instead of running them. Arrow keys and Enter
navigate; Tab jumps to the System row; Esc on the first tile quits.

### Run the tests

```sh
cd launcher && SDL_VIDEODRIVER=dummy pytest -q
```

## Project status

Early. The launcher is tested and the image build checks its own
assumptions, but nothing has been run on real hardware yet. See
[the checklist](docs/ARCHITECTURE.md#verify-on-real-hardware) of what to
confirm first.

## Repository layout

```
Containerfile                 OS image: Bazzite + Hearth
image/build.sh                runs inside the image build
image/system_files/           files copied into the image, laid out like /
launcher/hearth/              the home screen / session hub (Python)
launcher/tests/               tests (headless, run in CI)
docs/                         install, hardware, architecture
.github/workflows/build.yml   tests + builds and publishes the image to GHCR
```
