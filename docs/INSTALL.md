# Installing Hearth OS

Hearth ships as a container image on top of Bazzite. You install Bazzite with its
normal installer, then point the system at the Hearth image. Updates arrive
automatically from then on.

## 1. Publish the image (one time)

1. Push this repo to GitHub with `main` as the default branch. The
   [`build` workflow](../.github/workflows/build.yml) builds and pushes to
   `ghcr.io/<your-github-user>/hearth-os` (AMD/Intel) and `hearth-os-nvidia`,
   and rebuilds daily to pick up Bazzite updates.
2. GHCR packages start out private. Either make the package public
   (GitHub → your profile → Packages → hearth-os → Package settings → Change
   visibility), or run `sudo podman login ghcr.io` on the PC before switching.

## 2. Plan the disks (if you want Windows too)

**Use a separate drive for each OS.** It's the single best thing you can do for
dual boot: Windows updates can't overwrite the Linux bootloader, and either OS
can be reinstalled without touching the other.

- Install **Windows first**, on its own drive.
- In Windows, turn off *Fast Startup* (Control Panel → Power Options → Choose
  what the power buttons do). Otherwise Windows leaves its disks locked.
- Optional, to stop the clock jumping by hours between the two OSes: in Windows,
  run in an admin terminal
  `reg add HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation /v RealTimeIsUniversal /t REG_DWORD /d 1 /f`.

## 3. Install Bazzite

1. From [bazzite.gg](https://bazzite.gg), download the ISO for your GPU with
   **Steam Gaming Mode** selected (the "deck" edition, which boots to Game Mode).
2. In the firmware setup (BIOS): UEFI mode on. If you keep Secure Boot on,
   follow Bazzite's instructions to enroll its key during install.
3. Install Bazzite to the **second** drive, the one without Windows.

## 4. Switch to Hearth

In Bazzite's Desktop Mode, open a terminal (Konsole) and run:

```sh
sudo bootc switch ghcr.io/<your-github-user>/hearth-os:latest
# NVIDIA:  ghcr.io/<your-github-user>/hearth-os-nvidia:latest
systemctl reboot
```

After the reboot you land on the Hearth home screen. On first boot with
networking, `hearth-flatpak-setup.service` installs Kodi, RetroDECK, Moonlight,
Chrome and Jellyfin in the background. Their tiles appear as each install
finishes, the next time you return to the home screen.

Undo: `sudo bootc rollback` (or choose the previous entry in the boot menu),
or `sudo bootc switch ghcr.io/ublue-os/bazzite-deck:stable` to go back to
plain Bazzite.

## 5. First-run setup

- **Steam**: open the Steam tile and sign in. Steam runs in the same console UI
  as Bazzite's normal Game Mode.
- **Emulation**: open the Emulation tile. RetroDECK walks you through where to
  keep ROMs and BIOS files. Only use games and BIOS files you own.
- **Streaming sites**: YouTube opens its TV interface. Netflix and similar sites
  run in Chrome's kiosk mode. On Linux, Netflix streams at 720p or 1080p, not 4K.
- **Streaming this PC to other screens**: Bazzite includes Sunshine. Run
  `ujust setup-sunshine` in Desktop Mode, then use Moonlight on a phone, tablet or
  another TV.
- **Remote/CEC**: see [HARDWARE.md](HARDWARE.md). With a Pulse-Eight adapter
  plugged in, it's configured automatically. Change the behaviour in
  `/etc/hearth/cec.conf`.

## Dual boot day to day

- **Linux → Windows**: the *Boot Windows* tile (System row). The PC restarts
  into Windows once. Next restart goes back to Hearth.
- **Windows → Hearth**: just restart. If Windows ever makes itself the default
  after an update, fix the order from Hearth's Desktop Mode with
  `sudo efibootmgr` (look for the Fedora entry) and `sudo efibootmgr -o <fedora>,<windows>`.
  Or pick the drive from your motherboard's boot menu key (often F8, F11 or F12).
- Want a "Restart to Hearth" shortcut in Windows? Create a shortcut to
  this command, run as administrator:
  `cmd /c "bcdedit /set {fwbootmgr} bootsequence {<fedora-guid>} && shutdown /r /t 0"`
  (find the GUID with `bcdedit /enum firmware`).

## Customising the home screen

```sh
mkdir -p ~/.config/hearth
cp /usr/share/hearth/apps.toml ~/.config/hearth/apps.toml
```

Edit the copy: reorder rows, add tiles for other flatpaks (`flatpak = "app.id"`)
or commands, set colors and icons. It takes effect the next time you return to
the home screen. The comments at the top of the file list every option.

To boot straight into Steam again instead of Hearth, remove the override:
`sudo rm /etc/gamescope-session-plus/sessions.d/{steam,ogui-steam}`.
