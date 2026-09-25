#!/bin/bash
# Inside the lab container: audio, gamescope + Hearth, the scripted demo,
# then encode the video. Output goes to /lab/demo (mounted from ./out).
set -e
mkdir -p /run/user/0 && chmod 700 /run/user/0
bash /lab/audio.sh
rm -rf /lab/state /lab/home /lab/config /run/user/0/hearth
(bash /lab/start.sh > /lab/demo/gamescope.log 2>&1 &)
for _ in $(seq 100); do [ -e /tmp/.X11-unix/X0 ] && break; sleep 0.2; done
sleep 6  # let Hearth and the Quick Menu start
cd /tmp
status=0
DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/0 python3 /lab/demo.py || status=$?
python3 /lab/encode.py
cp /lab/state/hearth/hearth.log /lab/demo/hearth.log
bash /lab/stop.sh
exit $status
