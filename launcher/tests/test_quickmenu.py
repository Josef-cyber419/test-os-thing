from fakes import FakeActions, FakePactl

from hearth.audio import Audio
from hearth.model import Nav
from hearth.quickmenu import CLOSE, Context, QuickMenu, build_tabs


def make(state=None, discord_available=True):
    pactl, actions = FakePactl(), FakeActions()
    audio = Audio(pactl)
    state = state or {"foreground": {"id": "game", "name": "Game"}, "background": {}, "focus": "foreground"}
    ctx = Context(audio, audio.snapshot(), state, actions, discord_available)
    return QuickMenu(build_tabs(ctx)), pactl, actions


def test_tabs_and_close():
    menu, _, _ = make()
    assert [t.title for t in menu.tabs] == ["Audio", "Mixer", "Discord", "System"]
    menu.handle(Nav.TAB_PREV)
    assert menu.current.key == "system"
    assert menu.handle(Nav.BACK) == CLOSE


def test_volume_slider_and_mute():
    menu, pactl, _ = make()
    assert menu.selected.key == "volume"
    menu.handle(Nav.RIGHT)
    assert pactl.calls[-1] == ["set-sink-volume", "alsa_output.hdmi", "70%"]
    menu.handle(Nav.SELECT)
    assert pactl.calls[-1] == ["set-sink-mute", "alsa_output.hdmi", "1"]


def test_output_choice_switches_device():
    menu, pactl, _ = make()
    menu.handle(Nav.DOWN)
    assert menu.selected.key == "output"
    menu.handle(Nav.RIGHT)
    assert ["set-default-sink", "bluez_output.headset"] in pactl.calls


def test_mixer_per_app_volume():
    menu, pactl, _ = make()
    menu.handle(Nav.TAB_NEXT)
    assert [i.label for i in menu.current.items] == ["Elden Ring", "Discord voice", "Spotify"]
    menu.handle(Nav.LEFT)
    assert pactl.calls[-1] == ["set-sink-input-volume", "41", "95%"]


def test_discord_start_when_not_running():
    menu, _, actions = make()
    menu.handle(Nav.TAB_NEXT)
    menu.handle(Nav.TAB_NEXT)
    assert menu.selected.key == "start"
    assert menu.handle(Nav.SELECT) == CLOSE
    assert actions.calls == [("start", "discord")]


def test_discord_call_controls():
    state = {"foreground": {"id": "game", "name": "Game"}, "background": {"discord": {}}, "focus": "foreground"}
    menu, pactl, actions = make(state)
    menu.handle(Nav.TAB_NEXT)
    menu.handle(Nav.TAB_NEXT)
    assert [i.key for i in menu.current.items] == ["show", "mute", "deafen", "voice-volume", "quit"]
    menu.handle(Nav.DOWN)
    menu.handle(Nav.SELECT)  # mute my mic
    assert pactl.calls[-1] == ["set-source-output-mute", "51", "1"]
    menu.handle(Nav.DOWN)
    menu.handle(Nav.SELECT)  # deafen
    assert pactl.calls[-1] == ["set-sink-input-mute", "42", "1"]


def test_discord_not_installed():
    menu, _, _ = make(discord_available=False)
    tab = next(t for t in menu.tabs if t.key == "discord")
    assert tab.items[0].kind == "info"


def test_power_actions_need_confirmation():
    menu, _, actions = make()
    menu.handle(Nav.TAB_PREV)
    menu.handle(Nav.DOWN)  # Close Game
    assert menu.selected.key == "home"
    assert menu.handle(Nav.SELECT) is None and menu.confirming == "home"
    assert menu.handle(Nav.SELECT) == CLOSE
    assert actions.calls == [("go_home",)]


def test_confirmation_cancelled_by_moving():
    menu, _, actions = make()
    menu.handle(Nav.TAB_PREV)
    menu.handle(Nav.DOWN)
    menu.handle(Nav.SELECT)
    menu.handle(Nav.DOWN)
    menu.handle(Nav.UP)
    menu.handle(Nav.SELECT)
    assert actions.calls == [] and menu.confirming == "home"


def test_refresh_keeps_selection():
    menu, _, _ = make()
    menu.handle(Nav.DOWN)
    menu.handle(Nav.DOWN)
    key = menu.selected.key
    fresh, _, _ = make()
    menu.set_tabs(fresh.tabs)
    assert menu.selected.key == key
