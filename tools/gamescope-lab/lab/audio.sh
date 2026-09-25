#!/bin/bash
# PipeWire with fake devices: two outputs and a microphone, like a TV setup.
export XDG_RUNTIME_DIR=/run/user/0
mkdir -p $XDG_RUNTIME_DIR
if [ ! -S $XDG_RUNTIME_DIR/bus ]; then
    dbus-daemon --session --address=unix:path=$XDG_RUNTIME_DIR/bus --fork --nopidfile
fi
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
pkill -x pipewire-pulse; pkill -x wireplumber; pkill -x pipewire
# Wait for them to exit: WirePlumber saves its state as it shuts down.
for _ in $(seq 50); do pgrep -x wireplumber >/dev/null || pgrep -x pipewire >/dev/null || break; sleep 0.1; done
pkill -9 -x pipewire-pulse; pkill -9 -x wireplumber; pkill -9 -x pipewire; sleep 0.3
# Forget remembered defaults/volumes from earlier runs.
rm -rf /root/.local/state/wireplumber /root/.local/state/pipewire
(pipewire > /tmp/pipewire.log 2>&1 &)
sleep 1
(wireplumber > /tmp/wireplumber.log 2>&1 &)
(pipewire-pulse > /tmp/pipewire-pulse.log 2>&1 &)
sleep 2
pactl load-module module-null-sink sink_name=tv_hdmi 'sink_properties={ device.description="LG TV (HDMI)" }'  >/dev/null
pactl load-module module-null-sink sink_name=headset 'sink_properties={ device.description="Arctis Nova 7" }'  >/dev/null
pactl load-module module-null-sink media.class=Audio/Source/Virtual sink_name=mic channel_map=front-left,front-right 'sink_properties={ device.description="Arctis Nova 7 Mic" }' >/dev/null
pactl set-default-sink tv_hdmi
pactl set-sink-volume tv_hdmi 60%
pactl set-default-source mic
pactl list short sinks
grep -q 'application.name' /root/.local/state/wireplumber/stream-properties 2>/dev/null && echo 'WARNING: per-app volumes were restored'
pactl list short sources | grep -v monitor
