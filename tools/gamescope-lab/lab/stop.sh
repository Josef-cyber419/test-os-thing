#!/bin/bash
# Stop gamescope and everything running inside it.
pkill -x gamescope-wl
pkill -x gamescopereaper
pkill -x Xwayland
for pat in "m hearth" "fake_app.py" "ffplay"; do pkill -f -- "$pat"; done
sleep 1.5
pkill -9 -x gamescope-wl; pkill -9 -x Xwayland
rm -f /tmp/.X11-unix/X* /tmp/.X*-lock /run/user/0/gamescope-*
