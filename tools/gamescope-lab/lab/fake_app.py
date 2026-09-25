"""Lab stand-in app: a full-screen window that can also make real sound.
Usage: fake_app.py NAME WM_CLASS [--tone HZ] [--voice]
--voice acts like a Discord call: a voice stream plus a microphone stream."""
import math, os, signal, subprocess, sys, array

name, wm_class = sys.argv[1], sys.argv[2]
tone = float(sys.argv[sys.argv.index("--tone") + 1]) if "--tone" in sys.argv else None
voice = "--voice" in sys.argv
os.environ["SDL_VIDEO_X11_WMCLASS"] = wm_class
os.environ["SDL_AUDIO_DEVICE_APP_NAME"] = "WEBRTC VoiceEngine" if voice else name
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

rec = None
def quit_(*_):
    if rec:
        rec.terminate()
    sys.exit(0)
signal.signal(signal.SIGTERM, quit_)

pygame.display.init(); pygame.font.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption(name)
w, h = screen.get_size()

if tone or voice:
    pygame.mixer.init(frequency=48000, size=-16, channels=2)
    hz = tone or 330.0
    samples = array.array("h", (int(3000 * math.sin(2 * math.pi * hz * i / 48000)) for i in range(48000) for _ in (0, 1)))
    pygame.mixer.Sound(buffer=samples.tobytes()).play(loops=-1)
if voice:
    rec = subprocess.Popen(["pw-record", "--target", "mic", "-P",
                            '{ application.name="WEBRTC VoiceEngine" application.process.binary="Discord" }',
                            "/tmp/voice.wav"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

big = pygame.font.SysFont("dejavusans", h // 9, bold=True)
small = pygame.font.SysFont("dejavusans", h // 28)
clock = pygame.time.Clock()
t = 0.0
while True:
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            quit_()
    t += clock.get_time() / 1000
    if voice:  # a Discord-ish look
        screen.fill((49, 51, 56))
        pygame.draw.rect(screen, (30, 31, 34), (0, 0, int(w * 0.07), h))
        pygame.draw.rect(screen, (43, 45, 49), (int(w * 0.07), 0, int(w * 0.2), h))
        for i, ch in enumerate(["# general", "# clips", "🔊 Game Night"]):
            screen.blit(small.render(ch.replace("🔊", "»"), True, (148, 155, 164)), (int(w * 0.085), 60 + i * 44))
        for i in range(3):
            c = (int(w * 0.5) + (i - 1) * 190, int(h * 0.45))
            ring = 6 + int(4 * abs(math.sin(t * 4 + i)))
            pygame.draw.circle(screen, (35, 165, 90), c, 70 + ring)
            pygame.draw.circle(screen, [(88, 101, 242), (237, 66, 69), (250, 166, 26)][i], c, 70)
        screen.blit(big.render(name, True, (242, 243, 245)), (int(w * 0.33), int(h * 0.7)))
    else:  # a colourful, moving "game"
        for y in range(0, h, 4):
            k = y / h
            pygame.draw.rect(screen, (int(30 + 140 * k), int(110 - 60 * k), int(190 - 120 * k)), (0, y, w, 4))
        for i in range(9):
            x = (w * (i + 1) // 10 + int(t * 60)) % (w + 200) - 100
            pygame.draw.circle(screen, (240 - 20 * i, 120 + 12 * i, 90 + 15 * i), (x, int(h * 0.66 + 30 * math.sin(t * 2 + i))), h // 6)
        screen.blit(big.render(name, True, (255, 255, 255)), (int(w * 0.08), int(h * 0.2)))
    pygame.display.flip()
    clock.tick(20)
