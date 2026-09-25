"""Drawing the Quick Menu: a frosted panel that slides in over the game.

Renders onto a transparent (SRCALPHA) surface; the overlay window shows the
running game through the transparent parts.
"""

from __future__ import annotations

import math
import time
import zlib

import pygame

from .quickmenu import Item, QuickMenu

TEXT = (242, 244, 250)
DIM = (150, 157, 182)
ACCENT = (255, 190, 90)
ACCENT_2 = (255, 118, 92)
PANEL = (18, 20, 34, 236)
DARK_TEXT = (28, 20, 12)

AVATAR_COLORS = [(88, 101, 242), (35, 165, 90), (237, 66, 69), (250, 166, 26), (155, 89, 182), (26, 188, 156)]


def ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def _blend_rect(surf: pygame.Surface, rect: pygame.Rect, color, radius: int = 0, width: int = 0) -> None:
    """Draw a (possibly translucent) rounded rect, blending with what's below."""
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, color, layer.get_rect(), width=width, border_radius=radius)
    surf.blit(layer, rect.topleft)


def _gradient_rect(surf: pygame.Surface, rect: pygame.Rect, c1, c2, radius: int = 0, alpha: int = 255) -> None:
    if rect.w <= 0 or rect.h <= 0:
        return
    grad = pygame.Surface((2, 1), pygame.SRCALPHA)
    grad.set_at((0, 0), (*c1, alpha))
    grad.set_at((1, 0), (*c2, alpha))
    grad = pygame.transform.smoothscale(grad, rect.size)
    mask = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(grad, rect.topleft)


def _glow(surf: pygame.Surface, rect: pygame.Rect, color, radius: int, spread: int) -> None:
    """Soft glow: a rounded rect blurred by down- then up-scaling."""
    big = rect.inflate(spread * 2, spread * 2)
    layer = pygame.Surface(big.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, color, pygame.Rect(spread, spread, rect.w, rect.h), border_radius=radius)
    small = pygame.transform.smoothscale(layer, (max(1, big.w // 8), max(1, big.h // 8)))
    surf.blit(pygame.transform.smoothscale(small, big.size), big.topleft)


class Icons:
    @staticmethod
    def draw(surf: pygame.Surface, name: str, center: tuple[int, int], size: int, color, bg=(0, 0, 0)) -> None:
        cx, cy = center
        s = size / 2
        w = max(2, int(size / 12))
        if name == "speaker":
            body = [(cx - s * 0.9, cy - s * 0.3), (cx - s * 0.45, cy - s * 0.3), (cx, cy - s * 0.75),
                    (cx, cy + s * 0.75), (cx - s * 0.45, cy + s * 0.3), (cx - s * 0.9, cy + s * 0.3)]
            pygame.draw.polygon(surf, color, body)
            for r in (0.45, 0.8):
                box = pygame.Rect(0, 0, s * r * 2, s * r * 2)
                box.center = (cx, cy)
                pygame.draw.arc(surf, color, box, -math.pi / 3.2, math.pi / 3.2, w)
        elif name == "sliders":
            for i, knob in enumerate((0.35, -0.3, 0.1)):
                y = cy + (i - 1) * s * 0.6
                pygame.draw.line(surf, color, (cx - s * 0.85, y), (cx + s * 0.85, y), w)
                pygame.draw.circle(surf, color, (cx + knob * s * 1.6, y), max(3, int(s * 0.22)))
        elif name == "chat":
            box = pygame.Rect(0, 0, s * 1.8, s * 1.3)
            box.center = (cx, cy - s * 0.1)
            pygame.draw.rect(surf, color, box, border_radius=int(s * 0.4))
            pygame.draw.polygon(surf, color, [(cx - s * 0.5, box.bottom - 2), (cx - s * 0.1, box.bottom - 2),
                                              (cx - s * 0.6, box.bottom + s * 0.4)])
            for dx in (-0.45, 0, 0.45):
                pygame.draw.circle(surf, bg, (cx + dx * s, box.centery), max(2, int(s * 0.13)))
        elif name == "power":
            box = pygame.Rect(0, 0, s * 1.6, s * 1.6)
            box.center = (cx, cy + s * 0.08)
            pygame.draw.arc(surf, color, box, math.pi * 0.62, math.pi * 2.38, w + 1)
            pygame.draw.line(surf, color, (cx, cy - s * 0.9), (cx, cy - s * 0.05), w + 1)


class QuickMenuView:
    def __init__(self, size: tuple[int, int]) -> None:
        self.size = size
        w, h = size
        self.u = u = h / 1080
        families = "cantarell,notosans,dejavusans,freesans"
        font = lambda px, bold=False: pygame.font.SysFont(families, max(8, int(px * u)), bold=bold)
        self.f_caption = font(21, True)
        self.f_title = font(42, True)
        self.f_clock = font(30, True)
        self.f_tab = font(25, True)
        self.f_label = font(30, True)
        self.f_detail = font(22)
        self.f_value = font(26, True)
        self.f_hint = font(22)
        self.f_avatar = font(26, True)
        self.panel_w = int(660 * u)
        self.margin = int(28 * u)
        self.pad = int(38 * u)
        self._scroll = 0.0
        self._backdrop = self._make_backdrop()

    def _make_backdrop(self) -> pygame.Surface:
        """Darken the game towards the right, where the panel sits."""
        grad = pygame.Surface((2, 1), pygame.SRCALPHA)
        grad.set_at((0, 0), (0, 0, 0, 70))
        grad.set_at((1, 0), (0, 0, 0, 185))
        return pygame.transform.smoothscale(grad, self.size)

    def px(self, v: float) -> int:
        return int(v * self.u)

    def draw(self, surf: pygame.Surface, menu: QuickMenu, title: str, paused: bool, t: float = 1.0) -> None:
        surf.fill((0, 0, 0, 0))
        e = ease_out(max(0.0, min(1.0, t)))
        backdrop = self._backdrop.copy()
        backdrop.set_alpha(int(255 * e))
        surf.blit(backdrop, (0, 0))

        w, h = self.size
        panel = pygame.Rect(0, self.margin, self.panel_w, h - 2 * self.margin)
        panel.right = int(w - self.margin + (1 - e) * (self.panel_w + self.margin * 2))

        layer = pygame.Surface(panel.size, pygame.SRCALPHA)
        self._draw_panel(layer, menu, title, paused)
        layer.set_alpha(int(255 * e))
        _glow(surf, panel, (0, 0, 0, int(160 * e)), self.px(40), self.px(36))
        surf.blit(layer, panel.topleft)

    def _draw_panel(self, s: pygame.Surface, menu: QuickMenu, title: str, paused: bool) -> None:
        r = s.get_rect()
        radius = self.px(36)
        pygame.draw.rect(s, PANEL, r, border_radius=radius)
        # A faint warm sheen at the top and a hairline border sell the glass look.
        sheen_h = self.px(260)
        sheen = pygame.Surface((1, 2), pygame.SRCALPHA)
        sheen.set_at((0, 0), (255, 170, 110, 34))
        sheen.set_at((0, 1), (255, 170, 110, 0))
        sheen = pygame.transform.smoothscale(sheen, (r.w, sheen_h))
        mask = pygame.Surface((r.w, sheen_h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, r.w, r.h), border_radius=radius)
        sheen.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        s.blit(sheen, (0, 0))
        _blend_rect(s, r, (255, 255, 255, 30), radius, width=max(1, self.px(2)))

        pad = self.pad
        y = pad
        cap = self.f_caption.render("NOW PLAYING" if title != "Home" else "HEARTH", True, DIM)
        s.blit(cap, (pad, y))
        clock = self.f_clock.render(time.strftime("%H:%M"), True, TEXT)
        s.blit(clock, (r.w - pad - clock.get_width(), y - self.px(4)))
        y += cap.get_height() + self.px(6)
        name = self.f_title.render(title, True, TEXT)
        max_w = r.w - 2 * pad - (self.px(150) if paused else 0)
        if name.get_width() > max_w:
            name = name.subsurface((0, 0, max_w, name.get_height()))
        s.blit(name, (pad, y))
        if paused:
            chip = self.f_caption.render("PAUSED", True, DARK_TEXT)
            chip_rect = chip.get_rect().inflate(self.px(26), self.px(12))
            chip_rect.midright = (r.w - pad, y + name.get_height() // 2)
            _gradient_rect(s, chip_rect, ACCENT, ACCENT_2, chip_rect.h // 2)
            s.blit(chip, chip.get_rect(center=chip_rect.center))
        y += name.get_height() + self.px(30)

        y = self._draw_tabs(s, menu, y)
        footer_h = self.px(70)
        self._draw_items(s, menu, pygame.Rect(0, y + self.px(22), r.w, r.h - y - self.px(22) - footer_h))
        self._draw_footer(s, pygame.Rect(0, r.h - footer_h, r.w, footer_h))

    def _draw_tabs(self, s: pygame.Surface, menu: QuickMenu, y: int) -> int:
        pad, gap = self.pad, self.px(10)
        n = len(menu.tabs)
        tab_w = (s.get_width() - 2 * pad - gap * (n - 1)) // n
        tab_h = self.px(92)
        for i, tab in enumerate(menu.tabs):
            rect = pygame.Rect(pad + i * (tab_w + gap), y, tab_w, tab_h)
            active = i == menu.tab
            if active:
                _glow(s, rect, (*ACCENT_2, 90), self.px(20), self.px(14))
                _gradient_rect(s, rect, ACCENT, ACCENT_2, self.px(20))
            else:
                _blend_rect(s, rect, (255, 255, 255, 16), self.px(20))
            color = DARK_TEXT if active else DIM
            Icons.draw(s, tab.icon, (rect.centerx, rect.y + self.px(34)), self.px(30), color,
                       bg=ACCENT if active else PANEL[:3])
            label = self.f_tab.render(tab.title, True, color)
            s.blit(label, label.get_rect(midbottom=(rect.centerx, rect.bottom - self.px(10))))
        return y + tab_h

    def _draw_items(self, s: pygame.Surface, menu: QuickMenu, area: pygame.Rect) -> None:
        pad = self.pad
        row_h, gap = self.px(104), self.px(10)
        items = menu.current.items
        sel = menu.selected
        idx = items.index(sel) if sel in items else 0
        # Keep the selected row in view.
        target = max(0, (idx + 1) * (row_h + gap) - area.h)
        target = min(target, idx * (row_h + gap))
        self._scroll += (target - self._scroll) * 0.35
        clip = s.get_clip()
        s.set_clip(area)
        for i, item in enumerate(items):
            rect = pygame.Rect(pad - self.px(12), area.y + i * (row_h + gap) - int(self._scroll),
                               s.get_width() - 2 * pad + self.px(24), row_h)
            if rect.bottom < area.top or rect.top > area.bottom:
                continue
            self._draw_item(s, item, rect, item is sel, menu.confirming == item.key)
        s.set_clip(clip)

    def _draw_item(self, s: pygame.Surface, item: Item, rect: pygame.Rect, selected: bool, confirming: bool) -> None:
        radius = self.px(22)
        inner = rect.inflate(-self.px(40), 0)
        if selected:
            _glow(s, rect, (*ACCENT, 38), radius, self.px(10))
            _blend_rect(s, rect, (255, 255, 255, 26), radius)
            _blend_rect(s, rect, (*ACCENT, 150), radius, width=max(1, self.px(2)))

        x = inner.x
        if item.avatar:
            color = AVATAR_COLORS[zlib.crc32(item.label.encode()) % len(AVATAR_COLORS)]
            c = (x + self.px(26), rect.centery - (self.px(10) if item.kind == "slider" else 0))
            pygame.draw.circle(s, color, c, self.px(26))
            letter = self.f_avatar.render(item.avatar, True, TEXT)
            s.blit(letter, letter.get_rect(center=c))
            x += self.px(68)

        label_color = DIM if item.kind == "info" else TEXT
        text = "Press A again to confirm" if confirming else item.label
        label = self.f_label.render(text, True, ACCENT if confirming else label_color)
        detail = self.f_detail.render(item.detail, True, DIM) if item.detail and not confirming else None
        if item.kind == "slider":
            top = rect.y + self.px(16)
            s.blit(label, (x, top))
            value = self.f_value.render("Muted" if item.muted else f"{item.value}%", True,
                                        DIM if item.muted else (ACCENT if selected else TEXT))
            s.blit(value, (inner.right - value.get_width(), top + self.px(2)))
            if detail:
                s.blit(detail, (x + label.get_width() + self.px(14), top + self.px(6)))
            self._slider(s, pygame.Rect(x, rect.bottom - self.px(30), inner.right - x, self.px(12)),
                         item.value, item.muted, selected)
            return

        text_h = label.get_height() + (detail.get_height() if detail else 0)
        top = rect.centery - text_h // 2
        s.blit(label, (x, top))
        if detail:
            s.blit(detail, (x, top + label.get_height()))

        if item.kind == "toggle":
            self._switch(s, pygame.Rect(0, 0, self.px(84), self.px(46)), inner.right, rect.centery, bool(item.value))
        elif item.kind == "choice" and item.options:
            self._choice(s, item, inner.right, rect.centery, selected, x + label.get_width() + self.px(20))
        elif item.kind == "action":
            chev = self.f_label.render("›", True, ACCENT if selected else DIM)
            s.blit(chev, chev.get_rect(midright=(inner.right, rect.centery)))

    def _slider(self, s: pygame.Surface, track: pygame.Rect, value: int, muted: bool, selected: bool) -> None:
        radius = track.h // 2
        _blend_rect(s, track, (255, 255, 255, 38), radius)
        fill = pygame.Rect(track.x, track.y, max(track.h, int(track.w * value / 100)), track.h)
        if muted:
            _blend_rect(s, fill, (255, 255, 255, 70), radius)
        else:
            _gradient_rect(s, fill, ACCENT, ACCENT_2, radius)
        if selected:
            knob = (fill.right, track.centery)
            _glow(s, pygame.Rect(knob[0] - track.h, knob[1] - track.h, track.h * 2, track.h * 2),
                  (*ACCENT, 120), track.h, self.px(8))
            pygame.draw.circle(s, TEXT, knob, int(track.h * 1.2))

    def _switch(self, s: pygame.Surface, rect: pygame.Rect, right: int, cy: int, on: bool) -> None:
        rect.midright = (right, cy)
        if on:
            _gradient_rect(s, rect, ACCENT, ACCENT_2, rect.h // 2)
        else:
            _blend_rect(s, rect, (255, 255, 255, 50), rect.h // 2)
        knob_x = rect.right - rect.h // 2 if on else rect.x + rect.h // 2
        pygame.draw.circle(s, TEXT, (knob_x, rect.centery), rect.h // 2 - self.px(5))

    def _choice(self, s: pygame.Surface, item: Item, right: int, cy: int, selected: bool, min_x: int) -> None:
        arrow_color = ACCENT if selected else DIM
        text = item.options[item.value]
        value = self.f_value.render(text, True, TEXT)
        avail = right - min_x - self.px(70)
        if value.get_width() > avail > 0:
            while len(text) > 3 and self.f_value.size(text + "…")[0] > avail:
                text = text[:-1]
            value = self.f_value.render(text + "…", True, TEXT)
        a = self.px(9)
        rx = right - a
        pygame.draw.polygon(s, arrow_color, [(rx - a, cy - a), (rx + a // 2, cy), (rx - a, cy + a)])
        vx = rx - a - self.px(14) - value.get_width()
        s.blit(value, (vx, cy - value.get_height() // 2))
        lx = vx - self.px(16)
        pygame.draw.polygon(s, arrow_color, [(lx + a, cy - a), (lx - a // 2, cy), (lx + a, cy + a)])

    def _draw_footer(self, s: pygame.Surface, area: pygame.Rect) -> None:
        x = self.pad
        for button, text in (("LB RB", "Tabs"), ("A", "Select"), ("◀ ▶", "Adjust"), ("B", "Close")):
            cap = self.f_caption.render(button, True, DARK_TEXT)
            chip = cap.get_rect().inflate(self.px(16), self.px(8))
            chip.midleft = (x, area.centery)
            _blend_rect(s, chip, (*DIM, 230), chip.h // 2)
            s.blit(cap, cap.get_rect(center=chip.center))
            label = self.f_hint.render(text, True, DIM)
            s.blit(label, (chip.right + self.px(8), area.centery - label.get_height() // 2))
            x = chip.right + self.px(8) + label.get_width() + self.px(26)
