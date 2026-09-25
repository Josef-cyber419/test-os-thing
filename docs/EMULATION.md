# Emulation

## What you'll see

The **Emulation** tile opens [ES-DE](https://es-de.org), a controller-driven
game menu:

1. **Console screen**: a row of console logos. **A console only appears once
   it has at least one game**, so the screen grows as you add games.
2. **Game list**: pick a console to see its games with box art, screenshots,
   descriptions and video previews (after you download artwork, below).
3. **Play**: pick a game and it opens in the right emulator automatically. Quit
   the game and you're back in the list.

Press B on the console screen to go back to the Hearth home screen.

## Adding games (in Desktop Mode)

The plan: use the desktop for maintenance, and the TV screen for playing.

1. On the Hearth home screen, choose **System → Desktop Mode**.
2. Open the file manager (Dolphin). Your home folder has:
   - `ROMs/`: one folder per console. On the first run ES-DE offers to
     create them all (*Create directories*). Or create them yourself with the
     names below.
   - `BIOS/`: BIOS, firmware and key files that some consoles need.
3. Copy games into the matching console folder, e.g. `ROMs/ps2/`,
   `ROMs/gc/`, `ROMs/switch/`.
4. Click **Return to Gaming Mode** on the desktop. The console appears in the
   Emulation menu.
5. **Artwork**: in ES-DE press Start → *Scraper*, create a free ScreenScraper
   account, and let it download box art and videos for everything.

**Games on a second drive?** Bazzite mounts extra drives under `/run/media`
or `/var/mnt`. Make a `ROMs` folder on the drive, then replace `~/ROMs` with a
link to it (in a terminal: `rm -r ~/ROMs && ln -s /var/mnt/games/ROMs ~/ROMs`,
with your drive's path). Emulators already have permission to read those
locations.

Only use games, BIOS files and keys you've dumped from hardware you own.

## Consoles, emulators and your hardware

The emulators are installed automatically on first boot (from
[`emulators.list`](../image/system_files/usr/share/hearth/emulators.list)). ES-DE
finds each one on its own.

Performance is estimated for an **Intel Core i7-4790K** (the top Intel
desktop chip that used DDR3) with an **RX 6750 XT** and 16 GB of RAM. The graphics card
is plenty for everything here. The **CPU** limits the newest consoles.

| Console | Folder | Emulator | Needs from you | Expect |
|---|---|---|---|---|
| NES, SNES, Game Boy / Color / Advance | `nes`, `snes`, `gb`, `gbc`, `gba` | RetroArch | – | Perfect |
| Nintendo 64 | `n64` | Rosalie's Mupen GUI | – | Excellent, upscaled |
| GameCube / Wii | `gc`, `wii` | Dolphin | – | Excellent, 4K |
| Wii U | `wiiu` | Cemu | Keys for encrypted dumps | Very good |
| Nintendo DS | `nds` | melonDS | DS BIOS/firmware (optional) | Perfect |
| Nintendo 3DS | `n3ds` | Azahar | Decrypted games | Excellent |
| **Nintendo Switch** | `switch` | Eden | `prod.keys` + firmware from **your** Switch | Lighter games good. Big 3D games may stutter or run below 30 fps on this CPU |
| PlayStation | `psx` | DuckStation | PS1 BIOS | Perfect, upscaled |
| PlayStation 2 | `ps2` | PCSX2 | PS2 BIOS | Excellent, 4K |
| PSP | `psp` | PPSSPP | – | Perfect |
| **PlayStation 3** | `ps3` | RPCS3 | PS3 firmware (free from Sony) | Many games playable. Demanding ones below full speed (RPCS3 wants 6+ cores) |
| PS Vita | `psvita` | Vita3K (manual, below) | Vita firmware | Good for supported games |
| **PlayStation 4** | `ps4` | shadPS4 | PS4 firmware modules | Experimental. A growing list of lighter games |
| Original Xbox | `xbox` | xemu | Xbox BIOS, MCPX boot ROM, HDD image | Good |
| **Xbox 360** | `xbox360` | Xenia (manual, below) | – | Experimental on Linux, and this CPU is weak for it |
| Arcade | `arcade`, `mame` | MAME / RetroArch | Matching ROM sets | Excellent |
| Xbox One / Series, PS5, Switch 2 | – | No working emulators exist | – | Use the real console through the **HDMI Input** tile ([HARDWARE.md](HARDWARE.md#capture-card-play-real-consoles-through-hearth)) |

Upgrading the CPU platform (for example a used Ryzen 5 5600 or 7 5700X3D board
with DDR4) is the single biggest improvement for Switch, PS3, PS4 and Xbox 360.
Everything else already runs great.

### Not installed automatically

These have no Flathub package. Download the AppImage in Desktop Mode, put it
in `~/Applications/`, and ES-DE finds it:
- **Vita3K** (PS Vita): `Vita3K-x86_64.AppImage` from vita3k.org.
- **Xenia Canary / Xenia Edge** (Xbox 360): see ES-DE's user guide for its
  Linux options. It currently runs best through Proton.

## One-time setup per emulator

Do this once in Desktop Mode, from the app menu:
- **Controllers**: most emulators pick up an Xbox-style controller
  automatically. Dolphin, Cemu, RPCS3 and Eden may need one mapping pass
  (Settings → Controllers).
- **BIOS / firmware / keys**: each emulator has a setting for where these
  live. Point it at the matching folder in `~/BIOS`.
- **Exit shortcut**: set a controller shortcut to quit the game back to ES-DE,
  e.g. Select + Start. RetroArch, PCSX2, DuckStation and Dolphin all support one.

**Holding the Guide button always gets you back to the Hearth home screen**, but
it closes the emulator *and* ES-DE without saving. Save in-game first, or use
the emulator's exit shortcut instead.

## Wii Remotes

With a Mayflash DolphinBar in mode 4, real Wii Remotes pair through the
DolphinBar itself. In Dolphin → Controllers, set each Wii Remote to *Real Wii
Remote*. See [HARDWARE.md](HARDWARE.md).
