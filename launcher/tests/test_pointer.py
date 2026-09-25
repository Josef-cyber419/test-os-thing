import pygame

from hearth.pointer import BTN_LEFT, EV_KEY, EV_REL, REL_X, Pointer, curve


class FakeUInput:
    def __init__(self):
        self.events = []

    def write(self, *event):
        self.events.append(event)

    def syn(self):
        self.events.append("syn")


def test_curve_has_deadzone_and_keeps_sign():
    assert curve(0.1) == 0.0
    assert curve(1.0) == 1.0 and curve(-1.0) == -1.0
    assert 0 < curve(0.5) < 0.5


def test_stick_moves_and_a_clicks():
    dev = FakeUInput()
    p = Pointer(dev)
    p.handle(pygame.event.Event(pygame.CONTROLLERAXISMOTION, axis=pygame.CONTROLLER_AXIS_LEFTX, value=32767))
    p.tick(0.01)
    assert (EV_REL, REL_X, 14) in dev.events
    p.handle(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=pygame.CONTROLLER_BUTTON_A))
    assert (EV_KEY, BTN_LEFT, 1) in dev.events
