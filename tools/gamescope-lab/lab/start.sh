#!/bin/bash
# Start real gamescope (headless, Steam mode like Bazzite's Game Mode) with
# Hearth as its client. Hearth runs from the repository mounted at /src.
/lab/stop.sh
export XDG_RUNTIME_DIR=/run/user/0 GAMESCOPE_LAB_NOFLIP=1
export PYTHONPATH=/src/launcher PYGAME_HIDE_SUPPORT_PROMPT=1 SDL_VIDEODRIVER=x11
export HEARTH_LOG_LEVEL=debug XDG_STATE_HOME=/lab/state XDG_CONFIG_HOME=/lab/config HOME=/lab/home
mkdir -p /lab/state /lab/config /lab/home
exec gamescope --backend headless -W 1280 -H 720 -w 1280 -h 720 -e -- \
    python3 -m hearth --config /lab/apps.toml
