"""The 10-foot home screen: rows of tiles, a clock, and a confirm dialog."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import pygame

from .config import App
from .input import InputMapper
from .model import Home, Nav

BG_TOP = (18, 20, 32)
BG_BOTTOM = (6, 7, 12)
TEXT = (235, 237, 245)
TEXT_DIM = (150, 155, 175)
ACCENT = (255, 190, 90)


def _color(hex_str: str) -> tuple[int, int, int]:
    try:
        c = pygame.Color(hex_str)
        return (c.r, c.g, c.b)
    except ValueError:
        return (58, 63, 88)


def _lighten(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(int(c + (255 - c) * amount) for c in rgb)  # type: ignore[return-value]


class Theme:
    """Sizes derived from screen height so 720p, 1080p and 4K all look right."""

    def __init__(self, size: tuple[int, int]) -> None:
        w, h = size
        u = h / 1080
        self.width, self.height = w, h
        self.margin = int(96 * u)
        self.header_h = int(170 * u)
        self.footer_h = int(110 * u)
        self.tile_w = int(360 * u)
        self.tile_h = int(210 * u)
        self.gap = int(36 * u)
        self.row_title_h = int(64 * u)
        self.row_h = self.row_title_h + self.tile_h + int(56 * u)
        self.radius = int(20 * u)
        self.border = max(2, int(6 * u))
        self.focus_scale = 1.08
        families = "cantarell,notosans,dejavusans,freesans"
        self.font_title = pygame.font.SysFont(families, int(56 * u), bold=True)
        self.font_row = pygame.font.SysFont(families, int(38 * u), bold=True)
        self.font_tile = pygame.font.SysFont(families, int(36 * u), bold=True)
        self.font_letter = pygame.font.SysFont(families, int(110 * u), bold=True)
        self.font_hint = pygame.font.SysFont(families, int(28 * u))


class HomeScreen:
    def __init__(self, surface: pygame.Surface, home: Home, title: str) -> None:
        self.surface = surface
        self.home = home
        self.title = title
        self.theme = Theme(surface.get_size())
        self.background = self._make_background()
        self.confirming: App | None = None
        self.message: str | None = None
        self._icons: dict[str, pygame.Surface | None] = {}
        self._scroll_x: list[float] = [0.0] * len(home.config.rows)
        self._scroll_y = 0.0
        self._target_y = 0.0

    def _make_background(self) -> pygame.Surface:
        w, h = self.surface.get_size()
        bg = pygame.Surface((w, h))
        for y in range(h):
            t = y / max(1, h - 1)
            color = [int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)]
            pygame.draw.line(bg, color, (0, y), (w, y))
        return bg

    def _icon(self, app: App, size: tuple[int, int]) -> pygame.Surface | None:
        if not app.icon:
            return None
        key = f"{app.icon}@{size}"
        if key not in self._icons:
            try:
                img = pygame.image.load(str(Path(app.icon).expanduser())).convert_alpha()
                scale = min(size[0] / img.get_width(), size[1] / img.get_height())
                new = (int(img.get_width() * scale), int(img.get_height() * scale))
                self._icons[key] = pygame.transform.smoothscale(img, new)
            except (pygame.error, FileNotFoundError, ZeroDivisionError):
                self._icons[key] = None
        return self._icons[key]

    # -- input ---------------------------------------------------------------

    def handle(self, nav: Nav) -> App | None:
        """Apply a navigation action; returns the app to launch, if any."""
        self.message = None
        if self.confirming is not None:
            app, self.confirming = self.confirming, None
            return app if nav is Nav.SELECT else None
        if nav is Nav.SELECT:
            app = self.home.selected
            if app is not None and app.confirm:
                self.confirming = app
                return None
            return app
        if nav is Nav.MENU:
            # Jump to the power/system row (the last one), like a TV's menu key.
            if self.home.config.rows:
                self.home.row = len(self.home.config.rows) - 1
            return None
        self.home.move(nav)
        return None

    # -- drawing -------------------------------------------------------------

    def draw(self) -> None:
        th, s = self.theme, self.surface
        s.blit(self.background, (0, 0))

        # Scroll just enough to keep the focused row fully on screen.
        area = pygame.Rect(0, th.header_h, th.width, th.height - th.header_h - th.footer_h)
        row_top = self.home.row * th.row_h
        if row_top < self._target_y:
            self._target_y = row_top
        elif row_top + th.row_h > self._target_y + area.h:
            self._target_y = row_top + th.row_h - area.h
        self._scroll_y += (self._target_y - self._scroll_y) * 0.25
        s.set_clip(area)
        for r in range(len(self.home.config.rows)):
            y = int(area.y + r * th.row_h - self._scroll_y)
            if area.top - th.row_h < y < area.bottom:
                self._draw_row(r, y)
        s.set_clip(None)
        self._draw_header()

        if not self.home.config.rows:
            msg = th.font_row.render("No apps available — check apps.toml", True, TEXT_DIM)
            s.blit(msg, msg.get_rect(center=(th.width // 2, th.height // 2)))
        self._draw_hints()
        if self.confirming is not None:
            self._draw_confirm(self.confirming)

    def _draw_header(self) -> None:
        th = self.theme
        title = th.font_title.render(self.title, True, TEXT)
        self.surface.blit(title, (th.margin, int(th.header_h * 0.25)))
        clock = th.font_title.render(time.strftime("%H:%M"), True, TEXT)
        self.surface.blit(clock, (th.width - th.margin - clock.get_width(), int(th.header_h * 0.25)))

    def _draw_row(self, r: int, y: int) -> None:
        th = self.theme
        row = self.home.config.rows[r]
        focused_row = r == self.home.row
        label = th.font_row.render(row.title, True, TEXT if focused_row else TEXT_DIM)
        self.surface.blit(label, (th.margin, y))

        col = self.home.cols[r]
        step = th.tile_w + th.gap
        visible = max(1, (th.width - 2 * th.margin + th.gap) // step)
        first = min(max(0, col - visible + 1), max(0, len(row.apps) - visible))
        self._scroll_x[r] += (first * step - self._scroll_x[r]) * 0.25

        ty = y + th.row_title_h
        for c, app in enumerate(row.apps):
            x = int(th.margin + c * step - self._scroll_x[r])
            if x > th.width or x + th.tile_w < 0:
                continue
            self._draw_tile(app, x, ty, focused=focused_row and c == col)

    def _draw_tile(self, app: App, x: int, y: int, focused: bool) -> None:
        th, s = self.theme, self.surface
        rect = pygame.Rect(x, y, th.tile_w, th.tile_h)
        base = _color(app.color)
        if focused:
            rect = rect.inflate(int(th.tile_w * (th.focus_scale - 1)), int(th.tile_h * (th.focus_scale - 1)))
            shadow = rect.move(0, th.border * 2)
            pygame.draw.rect(s, (0, 0, 0), shadow, border_radius=th.radius)
            base = _lighten(base, 0.12)
        pygame.draw.rect(s, base, rect, border_radius=th.radius)

        icon = self._icon(app, (int(rect.w * 0.5), int(rect.h * 0.5)))
        if icon is not None:
            s.blit(icon, icon.get_rect(center=(rect.centerx, rect.y + rect.h * 0.4)))
        else:
            letter = th.font_letter.render(app.name[:1].upper(), True, _lighten(base, 0.35))
            s.blit(letter, letter.get_rect(center=(rect.centerx, rect.y + rect.h * 0.4)))

        name = th.font_tile.render(app.name, True, TEXT)
        if name.get_width() > rect.w - 2 * th.gap:
            name = pygame.transform.smoothscale(
                name, (rect.w - 2 * th.gap, int(name.get_height() * (rect.w - 2 * th.gap) / name.get_width()))
            )
        s.blit(name, name.get_rect(midbottom=(rect.centerx, rect.bottom - th.gap // 2)))
        if focused:
            pygame.draw.rect(s, ACCENT, rect, width=th.border, border_radius=th.radius)

    def _draw_hints(self) -> None:
        th = self.theme
        text = self.message or "[A] Open     [B] Back     [Start] Power & System"
        hint = th.font_hint.render(text, True, ACCENT if self.message else TEXT_DIM)
        self.surface.blit(hint, (th.margin, th.height - (th.footer_h + hint.get_height()) // 2))

    def _draw_confirm(self, app: App) -> None:
        th, s = self.theme, self.surface
        shade = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 170))
        s.blit(shade, (0, 0))
        box = pygame.Rect(0, 0, int(th.width * 0.45), int(th.height * 0.28))
        box.center = (th.width // 2, th.height // 2)
        pygame.draw.rect(s, (32, 35, 52), box, border_radius=th.radius)
        pygame.draw.rect(s, ACCENT, box, width=th.border, border_radius=th.radius)
        q = th.font_row.render(f"{app.name}?", True, TEXT)
        s.blit(q, q.get_rect(center=(box.centerx, box.y + box.h * 0.38)))
        h = th.font_hint.render("[A] Yes        [B] Cancel", True, TEXT_DIM)
        s.blit(h, h.get_rect(center=(box.centerx, box.y + box.h * 0.72)))


def run(
    surface: pygame.Surface,
    home: Home,
    title: str,
    message: str | None = None,
    allow_quit: bool = False,
    max_frames: int | None = None,
    input_blocked: Callable[[], bool] | None = None,
) -> App | None:
    """Show the home screen until the user picks an app.

    Returns None only when quitting is allowed (dev mode) and requested.
    `input_blocked` is polled a few times a second; while it's true (the Quick
    Menu is open over the home screen), input is ignored.
    """
    screen = HomeScreen(surface, home, title)
    screen.message = message
    mapper = InputMapper()
    mapper.open_devices()
    clock = pygame.time.Clock()
    frames = 0
    blocked = False
    while max_frames is None or frames < max_frames:
        frames += 1
        if input_blocked and frames % 8 == 0:
            blocked = input_blocked()
        now = pygame.time.get_ticks()
        navs: list[Nav] = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT and allow_quit:
                return None
            nav = mapper.translate(event, now)
            if nav is not None and not blocked:
                navs.append(nav)
        repeat = mapper.repeat(now)
        if repeat is not None:
            navs.append(repeat)
        for nav in navs:
            if nav is Nav.BACK and allow_quit and screen.confirming is None and home.row == 0 and home.col == 0:
                return None
            app = screen.handle(nav)
            if app is not None:
                return app
        screen.draw()
        pygame.display.flip()
        clock.tick(60)
    return None
