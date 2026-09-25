from fakes import FakePactl

from hearth.audio import Audio


def test_snapshot_parses_devices_and_streams():
    snap = Audio(FakePactl()).snapshot()
    assert [d.label for d in snap.outputs] == ["LG TV (HDMI)", "Arctis Nova 7"]
    assert [d.label for d in snap.inputs] == ["Arctis Nova 7 mic"]  # monitor filtered out
    assert snap.output().percent == 65 and snap.input().percent == 80
    assert [s.app for s in snap.playback] == ["Elden Ring", "Discord voice", "Spotify"]
    assert snap.playback[2].muted
    assert [s.index for s in snap.discord_playback()] == [42]
    assert [s.index for s in snap.discord_recording()] == [51]


def test_switching_output_moves_playing_streams():
    pactl = FakePactl()
    audio = Audio(pactl)
    audio.set_output("bluez_output.headset", audio.snapshot())
    assert ["set-default-sink", "bluez_output.headset"] in pactl.calls
    moved = [c[1] for c in pactl.calls if c[0] == "move-sink-input"]
    assert moved == ["41", "42", "43"]


def test_volume_is_clamped():
    pactl = FakePactl()
    Audio(pactl).set_output_volume("x", 500)
    assert pactl.calls[-1] == ["set-sink-volume", "x", "150%"]
