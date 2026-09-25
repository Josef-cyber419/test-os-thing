# Architecture

## Boot flow

```
firmware (UEFI) ──► GRUB ──► Bazzite (Fedora Atomic, Hearth image)
                               │
                               ▼
                   SDDM autologin → Game Mode session
                   gamescope-session-plus <ogui-steam|steam>
                   │  sources /usr/share/gamescope-session-plus/sessions.d/<session>   (Bazzite's)
                   │  then    /etc/gamescope-session-plus/sessions.d/<session>         (Hearth's: CLIENTCMD=/usr/bin/hearth)
                   ▼
                   gamescope (compositor: HDR, VRR, scaling) ──► hearth (session hub)
                                                                  │
                             ┌────────────────────────────────────┤ loop:
                             │  1. show home screen (pygame/SDL2)  │
                             │  2. user picks a tile               │
                             │  3. close window, run app, wait     │
                             │  4. app exits → back to 1           │
                             └────────────────────────────────────┘
```

Hearth replaces only the *client command* of Bazzite's Game Mode session.
gamescope, and all of Bazzite's per-device tuning, stays exactly as it was.
Steam becomes a tile: `hearth-steam` runs it with the same flags the stock
session uses (`-gamepadui -steamos3 -steampal -steamdeck`).

`gamescope-session-plus` has a safety net: if its client exits within 60
seconds five times in a row, it resets to the desktop session. So a broken
Hearth update can't leave you with a black screen; you land in Desktop Mode,
where `sudo bootc rollback` is one command away.

## Components

| Path | Role |
|---|---|
| `launcher/hearth/hub.py` | Main loop. Loads config, shows the home screen, runs the chosen app in its own process group, shows an error if it fails to start. |
| `launcher/hearth/ui.py` | Rendering (tiles, rows, header, confirm dialog). Sizes derived from screen height. |
| `launcher/hearth/model.py` | Navigation state (rows remember their column). No pygame, easy to test. |
| `launcher/hearth/input.py` | Keyboard / CEC / FLIRC / gamepad → `Nav` actions, stick auto-repeat. |
| `launcher/hearth/homebutton.py` | While an app runs, watches `/dev/input` (read-only) for Guide held 1.5s or `KEY_HOMEPAGE`, then closes the app. |
| `launcher/hearth/config.py` | `apps.toml` parsing and "is this app installed?" checks. |
| `usr/libexec/hearth/hearth-steam` | Runs Steam's console UI inside the current gamescope. |
| `usr/libexec/hearth/shims/steamos-session-select` | On `PATH` for apps started by Hearth. Turns Steam's "Switch to Desktop" into "exit Steam → Hearth home". |
| `usr/libexec/hearth/hearth-desktop` | Real Desktop Mode, via Bazzite's session switcher. |
| `usr/libexec/hearth/hearth-web` | Chrome (Flatpak) kiosk with a dedicated profile. Sends a TV user agent for youtube.com/tv. |
| `usr/libexec/hearth/hearth-reboot-to` + `hearth-bootnext` | Sets EFI `BootNext` to Windows Boot Manager (via a narrow sudoers rule), then reboots. |
| `usr/libexec/hearth/hearth-cec` + udev/systemd units | Pulse-Eight USB-CEC: register as a playback device, wake/standby the TV on resume/suspend/shutdown. |
| `usr/libexec/hearth/hearth-flatpak-setup` | First-boot Flathub installs from `flatpaks.list`. Each app is attempted until it succeeds once, then never again (so uninstalling sticks). |

### Why Python + SDL2 for the home screen?

SDL2 has the best gamepad support on Linux (the same mappings Steam uses),
draws directly under gamescope with no desktop toolkit, and `python3-pygame`
is packaged in Fedora. The UI is small enough that a game-style immediate-mode
renderer is simpler than a widget toolkit.

### Why a hub loop, not app switching?

gamescope shows one app full-screen at a time, and TV users expect "close app →
home". Running apps one at a time from a loop gives exactly that, frees the GPU
and controllers for the app, and makes failures easy to report (the next home
screen shows what went wrong).

## Verify on real hardware

These couldn't be tested without a real machine. Check them first, in this order:

1. **The image builds** against current `bazzite-deck:stable`. `image/build.sh`
   fails loudly if Bazzite's Game Mode session isn't one Hearth overrides.
2. **Hearth appears in Game Mode.** gamescope's `--steam` integration mode
   normally takes focus hints from Steam. Confirm Hearth's window is shown and gets
   controller input when Steam isn't running. If not, a likely fix is
   setting the `STEAM_GAME` X property on Hearth's window, or running Hearth under
   a non-`--steam` gamescope.
3. **Steam from the tile** behaves like normal Game Mode: Quick Access menu,
   performance overlay, sleep, game launching.
4. **Steam → Switch to Desktop** reaches Hearth's shim (i.e. Steam finds
   `steamos-session-select` on `PATH`) and returns home.
5. **Hold Guide** closes Chrome/Kodi/RetroDECK and returns home. The session user
   needs read access to controller event devices. logind normally grants this
   to the active seat, but confirm it.
6. **CEC**: TV remote keys arrive as arrow/Enter keys. Bazzite also runs
   steamos-manager's CEC service, so check the two don't conflict over `/dev/cec0`.
7. **Boot Windows** picks the right EFI entry and returns to Linux on the next
   reboot.

## Ideas / roadmap

- Real artwork: tile icons from each app's Flatpak metadata or SteamGridDB.
- Settings tile: Wi-Fi, Bluetooth controller pairing, display/audio output, all
  with a controller.
- "Continue playing" row: recent Steam games and RetroDECK saves.
- Phone remote: small web page / Home Assistant integration to launch tiles, wake
  the TV, or show what's playing.
- Ambient mode: photo or clock screensaver after idle time on the home screen.
- Profiles: per-person home screens and parental controls.
- Syncthing tile or service for ROM, save and screenshot sync between devices.
