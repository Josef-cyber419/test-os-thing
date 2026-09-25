from hearth import session
from hearth.gamescope import HOME_APPID, appid_for


def test_state_update_and_defaults_isolated():
    session.update(lambda s: s["background"].__setitem__("discord", {"pid": 1}))
    assert session.read()["background"] == {"discord": {"pid": 1}}
    assert session.DEFAULT_STATE["background"] == {}


def test_unit_names_round_trip_through_cgroup():
    unit = session.unit_name("app", "hdmi-in_2")
    cgroup = f"0::/user.slice/user-1000.slice/user@1000.service/app.slice/{unit}\n"
    assert session.app_for_cgroup(cgroup) == ("app", "hdmi-in_2")
    assert session.app_for_cgroup("0::/user.slice/other.scope") is None


def test_focus_appid():
    fg = {"id": "kodi", "tag_windows": True}
    assert session.focus_appid({"focus": "home", "foreground": None, "background": {}}) == HOME_APPID
    assert session.focus_appid({"focus": "foreground", "foreground": fg, "background": {}}) == appid_for("kodi")
    both = {"focus": "discord", "foreground": fg, "background": {"discord": {}}}
    assert session.focus_appid(both) == appid_for("discord")
    steam = {"focus": "foreground", "foreground": {"id": "steam", "tag_windows": False}, "background": {}}
    assert session.focus_appid(steam) is None


def test_appids_are_distinct_and_in_range():
    ids = {appid_for(a) for a in ("steam", "kodi", "discord", "youtube", "emulation")}
    assert len(ids) == 5 and all(HOME_APPID < i < HOME_APPID + 0x10000 for i in ids)
