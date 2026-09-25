# Updates, troubleshooting and recovery

Everything below is run from a terminal: Desktop Mode (System → Desktop Mode
→ Konsole), or over SSH from another computer (turn SSH on once with
`sudo systemctl enable --now sshd`).

## hearthctl

| Command | What it does |
|---|---|
| `hearthctl doctor` | Checks every part of the setup and says how to fix what's wrong: Game Mode hook, controllers, audio, apps and emulators, updates. **Start here.** |
| `hearthctl status` | What's running and in front, versions, whether an update is waiting. |
| `hearthctl logs` / `logs -f` | The home screen's and Quick Menu's log (`-f` follows it live). |
| `hearthctl update` | Install OS and app updates now. Restart to finish. |
| `hearthctl rollback` | Go back to the previous OS version on the next restart. |
| `hearthctl menu` / `home` | Open the Quick Menu / close the current app, e.g. over SSH if a controller dies. |
| `hearthctl disable` / `enable` | Make Game Mode start Steam directly / Hearth again. |
| `hearthctl dev PATH` / `dev --off` | Run the launcher from a source checkout (see below). |

## Updates

**Automatic.** Bazzite's updater (`uupd`) runs in the background. It downloads
new OS images (rebuilt daily by this repo's CI) and updates Flatpak apps.
ES-DE checks for updates weekly. An update is applied when you next restart;
the home screen shows **"Update ready: restart to finish"** when one is waiting.

**Manually:** Quick Menu → System → *Check for updates*, or `hearthctl update`.

**Changed your mind?** Every update keeps the previous version. Pick it in the
boot menu, or run `hearthctl rollback` and restart.

## When something's wrong

- **A tile is missing**: `hearthctl doctor` lists every hidden tile and why
  (usually an app still installing on first boot).
- **The home screen crashed**: it recovers by itself and shows the error. If
  it crashes 5 times within a minute, Game Mode falls back to Desktop Mode
  on its own. Check `hearthctl logs`.
- **The Quick Menu doesn't open**: `hearthctl doctor` checks the controller's
  Guide button is readable and the Quick Menu process is running.
- **No sound / wrong speaker**: Quick Menu → Audio → Output.
- **Need Steam without Hearth for a while**: `hearthctl disable`, restart.
  `hearthctl enable` brings Hearth back.
- **A bad OS update**: `hearthctl rollback` (or the boot menu), restart.

## Customising the home screen

Your changes live in `~/.config/hearth/apps.toml` and are layered over the
defaults, so new default tiles still appear after updates. Only write what you
want to change:

```toml
hide = ["plex", "android"]        # remove default tiles

[quick_menu]
pause_game = false                # keep games running under the Quick Menu

[[rows]]
title = "Watch"                   # an existing row: change it
  [[rows.apps]]
  id = "kodi"                     # an existing tile: change only these fields
  color = "#0f6fa8"
  [[rows.apps]]
  id = "twitch"                   # a new tile
  name = "Twitch"
  flatpak = "tv.twitch.Twitch"

[[rows]]
title = "Retro"                   # a new row (goes before System)
  [[rows.apps]]
  id = "retroarch"
  name = "RetroArch"
  flatpak = "org.libretro.RetroArch"
```

All tile options are listed at the top of `/usr/share/hearth/apps.toml`.
Changes show up the next time you return to the home screen. Add
`replace = true` to ignore the defaults entirely.

## Changing Hearth itself

Two ways, depending on how permanent the change is:

- **Try it on the TV now**: clone this repo on the PC, then
  `hearthctl dev ~/test-os-thing/launcher` and restart Game Mode. The home
  screen and Quick Menu run from your checkout. Edit, restart Game Mode to
  test, and `hearthctl dev --off` to go back.
- **Ship it**: push to `main`. CI runs the tests, builds the image, and the PC
  picks it up with its next automatic update.

Develop on any computer without the TV: see "Try the home screen" in the
README, and run `pytest` in `launcher/`. To see your change inside real
gamescope, with a recorded video, run `tools/gamescope-lab/run.sh` (needs
Docker; see its README).

For more detail in the log, set `HEARTH_LOG_LEVEL=debug` (e.g. in
`~/.config/environment.d/hearth.conf`). It records every Quick Menu input and
every audio change. The end-to-end test runs the real
home screen and Quick Menu on a virtual display (Xvfb) with fake apps; set
`HEARTH_E2E_SHOTS=/some/dir` to save screenshots of each step.
