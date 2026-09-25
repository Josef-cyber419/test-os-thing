from hearth.homebutton import BTN_MODE, KEY_HOMEPAGE, HomeButton


def test_guide_must_be_held():
    b = HomeButton(hold_seconds=1.5)
    assert not b.key(BTN_MODE, 1, now=10.0)
    assert not b.tick(11.0)
    assert b.tick(11.5)
    assert not b.tick(20.0)  # fires once per hold


def test_short_guide_press_does_nothing():
    b = HomeButton(hold_seconds=1.5)
    b.key(BTN_MODE, 1, now=0.0)
    b.key(BTN_MODE, 0, now=0.5)
    assert not b.tick(5.0)


def test_remote_home_key_is_instant():
    assert HomeButton().key(KEY_HOMEPAGE, 1, now=0.0)


def test_guide_tap_opens_quick_menu():
    from hearth.homebutton import KEY_MENU, GuideTap

    t = GuideTap(tap_max=0.4)
    assert not t.key(BTN_MODE, 1, now=0.0)
    assert t.key(BTN_MODE, 0, now=0.2)  # quick release: tap
    t.key(BTN_MODE, 1, now=1.0)
    assert not t.key(BTN_MODE, 0, now=2.0)  # that was a hold, not a tap
    assert t.key(KEY_MENU, 1, now=3.0)
