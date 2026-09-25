"""Turn keyboard, TV remote (HDMI-CEC / FLIRC) and gamepad events into Nav actions.

TV remotes arrive as keyboard events: HDMI-CEC through the kernel's rc-cec keymap,
a FLIRC USB IR receiver as a plain USB keyboard. Gamepads use SDL's
GameController API so button positions are consistent across controller brands.
"""

from __future__ import annotations

import pygame

from .model import Nav

KEYS = {
    pygame.K_UP: Nav.UP,
    pygame.K_DOWN: Nav.DOWN,
    pygame.K_LEFT: Nav.LEFT,
    pygame.K_RIGHT: Nav.RIGHT,
    pygame.K_w: Nav.UP,
    pygame.K_s: Nav.DOWN,
    pygame.K_a: Nav.LEFT,
    pygame.K_d: Nav.RIGHT,
    pygame.K_RETURN: Nav.SELECT,
    pygame.K_KP_ENTER: Nav.SELECT,
    pygame.K_SPACE: Nav.SELECT,
    pygame.K_ESCAPE: Nav.BACK,
    pygame.K_BACKSPACE: Nav.BACK,
    pygame.K_AC_BACK: Nav.BACK,
    pygame.K_MENU: Nav.MENU,
    pygame.K_TAB: Nav.MENU,
}

BUTTONS = {
    pygame.CONTROLLER_BUTTON_DPAD_UP: Nav.UP,
    pygame.CONTROLLER_BUTTON_DPAD_DOWN: Nav.DOWN,
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: Nav.LEFT,
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: Nav.RIGHT,
    pygame.CONTROLLER_BUTTON_A: Nav.SELECT,
    pygame.CONTROLLER_BUTTON_B: Nav.BACK,
    pygame.CONTROLLER_BUTTON_START: Nav.MENU,
    pygame.CONTROLLER_BUTTON_GUIDE: Nav.MENU,
}

# Fallback for devices SDL has no GameController mapping for (Linux xpad layout).
JOY_BUTTONS = {0: Nav.SELECT, 1: Nav.BACK, 7: Nav.MENU}

AXIS_THRESHOLD = 0.6
AXIS_REPEAT_DELAY_MS = 400
AXIS_REPEAT_RATE_MS = 120


class InputMapper:
    """Stateful translator: analog sticks need edge detection and auto-repeat."""

    def __init__(self) -> None:
        self._stick: Nav | None = None
        self._stick_next_ms = 0
        self._devices: dict[int, object] = {}

    def open_devices(self) -> None:
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            self._open(i)

    def _open(self, index: int) -> None:
        try:
            from pygame._sdl2 import controller
        except ImportError:  # pragma: no cover - very old pygame
            controller = None
        if controller is not None and not controller.get_init():
            controller.init()
        if controller is not None and controller.is_controller(index):
            dev = controller.Controller(index)
            self._devices[dev.as_joystick().get_instance_id()] = dev
        else:
            dev = pygame.joystick.Joystick(index)
            self._devices[dev.get_instance_id()] = dev

    def _is_controller(self, instance_id: int) -> bool:
        dev = self._devices.get(instance_id)
        return dev is not None and not isinstance(dev, pygame.joystick.JoystickType)

    def translate(self, event: pygame.event.Event, now_ms: int = 0) -> Nav | None:
        t = event.type
        if t == pygame.KEYDOWN:
            return KEYS.get(event.key)
        if t == pygame.CONTROLLERDEVICEADDED or t == pygame.JOYDEVICEADDED:
            if t == pygame.JOYDEVICEADDED:
                self._open(event.device_index)
            return None
        if t == pygame.CONTROLLERBUTTONDOWN:
            return BUTTONS.get(event.button)
        if t == pygame.CONTROLLERAXISMOTION:
            if event.axis == pygame.CONTROLLER_AXIS_LEFTX:
                return self._stick_axis(event.value / 32767, Nav.LEFT, Nav.RIGHT, now_ms)
            if event.axis == pygame.CONTROLLER_AXIS_LEFTY:
                return self._stick_axis(event.value / 32767, Nav.UP, Nav.DOWN, now_ms)
            return None
        # Raw joystick events are also emitted for GameController devices;
        # only honour them for devices without a mapping to avoid double input.
        instance = getattr(event, "instance_id", None)
        if instance is not None and self._is_controller(instance):
            return None
        if t == pygame.JOYBUTTONDOWN:
            return JOY_BUTTONS.get(event.button)
        if t == pygame.JOYHATMOTION:
            x, y = event.value
            if x:
                return Nav.RIGHT if x > 0 else Nav.LEFT
            if y:
                return Nav.UP if y > 0 else Nav.DOWN
            return None
        if t == pygame.JOYAXISMOTION and event.axis in (0, 1):
            neg, pos = (Nav.LEFT, Nav.RIGHT) if event.axis == 0 else (Nav.UP, Nav.DOWN)
            return self._stick_axis(event.value, neg, pos, now_ms)
        return None

    def _stick_axis(self, value: float, neg: Nav, pos: Nav, now_ms: int) -> Nav | None:
        if abs(value) < AXIS_THRESHOLD:
            if self._stick in (neg, pos):
                self._stick = None
            return None
        direction = pos if value > 0 else neg
        if direction != self._stick:
            self._stick = direction
            self._stick_next_ms = now_ms + AXIS_REPEAT_DELAY_MS
            return direction
        return None

    def repeat(self, now_ms: int) -> Nav | None:
        """Called every frame: emits a repeat while the stick stays held."""
        if self._stick is not None and now_ms >= self._stick_next_ms:
            self._stick_next_ms = now_ms + AXIS_REPEAT_RATE_MS
            return self._stick
        return None
