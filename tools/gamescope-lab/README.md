# gamescope lab

Runs Hearth inside **real gamescope** in Steam mode (as Bazzite's Game Mode
does), with **real PipeWire** audio, on any Linux machine with Docker: no GPU,
TV or controller needed. A script plays through a session, checks each step,
and records a video:

```sh
tools/gamescope-lab/run.sh      # → tools/gamescope-lab/out/hearth-demo.mp4
```

What the script does, and what it checks:

| Step | Checked |
|---|---|
| Boot | gamescope focuses the home screen (`GAMESCOPE_FOCUSED_APP`) |
| Launch a game from its tile | gamescope switches to it; its audio stream exists |
| Quick Menu (via `hearthctl menu`) | overlay visible and has gamescope's input focus |
| Audio tab: volume up, switch output | PipeWire sink volume changed; default output changed; the game's stream moved |
| Mixer: game volume down | the game's own stream volume changed |
| Start Discord (a stand-in with a voice and a mic stream) | gamescope shows it; its streams exist |
| Mute mic, deafen | Discord's PipeWire streams muted |
| Back to the game, close it | gamescope focus follows; the home screen returns; Discord keeps running |

Key presses are injected with XTest and reach whichever window gamescope gave
input focus to, the same routing a controller would use.

## How the video is made

gamescope's own screenshots don't capture window contents under software
rendering, so each frame is built from gamescope's published decisions: the
window it focused (`GAMESCOPE_FOCUSED_WINDOW`), plus the Quick Menu overlay
when its opacity is non-zero. Each window's pixels are read from Xwayland, and
the overlay is alpha-blended on top the way gamescope composites it. Audio is
recorded from the virtual TV and headset outputs.

## The gamescope patch

`gamescope-3.16.15-lab.patch` makes gamescope run on software Vulkan
(lavapipe) in a container. **It's for this lab only**; your PC runs Bazzite's
normal gamescope. It contains:

1. Upstream commit b9259c3 ("warn instead of bailing out if the driver
   doesn't implement VK_EXT_physical_device_drm"), which is in gamescope 3.16.24+.
2. Enable `VK_KHR_external_semaphore_fd` only if the driver has it (lavapipe
   doesn't; it's only used for explicit sync with GPU clients).
3. With `GAMESCOPE_LAB_NOFLIP` set, don't allocate display-scanout
   ("flippable") memory. There's no display in a headless container.
4. Treat software (SHM) frames, which have no fence, as ready immediately.
   Otherwise gamescope waits on an invalid fence and never paints.

## Not covered

Real GPU rendering, HDR/VRR, real controllers (the Guide button is simulated
with `hearthctl menu`), and pausing games (needs a systemd user session; the
container has none). The home screen and apps are the ones in `lab/apps.toml`:
stand-in windows, not Steam or Kodi.
