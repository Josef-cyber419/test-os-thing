#!/usr/bin/env bash
# Run Hearth inside real gamescope with real PipeWire, drive a scripted
# session (launch a game, Quick Menu, audio, Discord, go home), check every
# step, and record a video to ./out/hearth-demo.mp4.
#
# Needs Docker. The first run builds gamescope (~5 minutes).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
mkdir -p "$here/out"
# Pass an HTTP proxy through if one is configured (harmless otherwise).
proxy_args=()
for var in HTTP_PROXY HTTPS_PROXY http_proxy https_proxy; do
    [[ -n ${!var:-} ]] && proxy_args+=(--build-arg "$var=${!var}")
done
docker build --network host "${proxy_args[@]}" -t hearth-gamescope-lab "$here"
docker run --rm --init -v "$repo:/src:ro" -v "$here/out:/lab/demo" hearth-gamescope-lab /lab/run-demo.sh
echo "Video: $here/out/hearth-demo.mp4 (logs: gamescope.log, hearth.log)"
