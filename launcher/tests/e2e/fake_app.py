"""A stand-in app for end-to-end tests: a full-screen window with a name.
Usage: fake_app.py NAME WM_CLASS"""

import os
import signal
import sys

name, wm_class = sys.argv[1], sys.argv[2]
os.environ["SDL_VIDEO_X11_WMCLASS"] = wm_class
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame  # noqa: E402

signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
pygame.display.init()
pygame.font.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption(name)
w, h = screen.get_size()
for y in range(h):  # a colourful "game"
    t = y / h
    pygame.draw.line(screen, (int(30 + 140 * t), int(110 - 60 * t), int(190 - 120 * t)), (0, y), (w, y))
for i in range(9):
    pygame.draw.circle(screen, (240 - 20 * i, 120 + 12 * i, 90 + 15 * i), (w * (i + 1) // 10, h * 2 // 3), h // 6)
label = pygame.font.SysFont("dejavusans", h // 8, bold=True).render(name, True, (255, 255, 255))
screen.blit(label, label.get_rect(center=(w // 3, h // 3)))
pygame.display.flip()
clock = pygame.time.Clock()
while True:
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            sys.exit(0)
    pygame.display.flip()
    clock.tick(10)
