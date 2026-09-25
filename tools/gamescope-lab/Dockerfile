# Hearth in real gamescope, without a GPU or a TV.
#
# gamescope 3.16.15 (Ubuntu's package source) with a small patch so it runs
# on software Vulkan (lavapipe) in headless mode; see the patch file header
# and README.md. Plus PipeWire for real audio, and ffmpeg to record.
FROM ubuntu:25.10
ENV DEBIAN_FRONTEND=noninteractive

RUN sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
        dpkg-dev patch mesa-vulkan-drivers libvulkan1 xwayland \
        python3-pygame python3-xlib python3-evdev python3-pytest \
        ffmpeg fonts-dejavu-core procps x11-utils \
        pipewire pipewire-pulse wireplumber pulseaudio-utils dbus ca-certificates \
 && apt-get build-dep -y gamescope \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY gamescope-3.16.15-lab.patch /build/
RUN apt-get update \
 && apt-get source gamescope=3.16.15-2 \
 && cd gamescope-3.16.15 \
 && patch -p1 < /build/gamescope-3.16.15-lab.patch \
 && meson setup build -Dpipewire=enabled -Denable_openvr_support=false --buildtype=release \
 && ninja -C build \
 && rm -rf /var/lib/apt/lists/*
ENV PATH=/build/gamescope-3.16.15/build/src:$PATH

COPY lab/ /lab/
RUN chmod +x /lab/*.sh
