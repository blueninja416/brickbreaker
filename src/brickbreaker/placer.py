"""Brick Placer logic by Phoebe-Feathers."""

import random
import sys
from dataclasses import dataclass, field

import pygame

pygame.init()

# Configure
WID, HEI = 900, 600
FPS = 60
BG = (18, 18, 22)
WHITE: pygame.Color = (255, 255, 255)
OUTLINE = (160, 160, 160)
SIDEBAR_W = 220
ZONE_H = 400
GRID = 10

# Brick queue
W_MIN, W_MAX = 40, 180
H_MIN, H_MAX = 16, 60
QUEUE_SIZE = 6

# Timers
BUILD_SECONDS = 15
COOLDOWN_MS = 1000

# Window popup
screen = pygame.display.set_mode((WID, HEI))
pygame.display.set_caption("Brick Builder Game")
clock = pygame.time.Clock()

FIELD_RECT = pygame.Rect(0, 0, WID - SIDEBAR_W, HEI)
SIDEBAR = pygame.Rect(FIELD_RECT.right, 0, SIDEBAR_W, HEI)
FONT_S = pygame.font.SysFont(None, 24)
FONT_M = pygame.font.SysFont(None, 28)
FONT_L = pygame.font.SysFont(None, 64)


# Game state/updates
def now_ms() -> int:
    return pygame.time.get_ticks()


def snap(v: int, grid: int = GRID) -> int:
    return grid * round(v / grid)


def zone_rect() -> pygame.Rect:
    return pygame.Rect(FIELD_RECT.left, FIELD_RECT.top, FIELD_RECT.width, ZONE_H)


def clamp_inside(r: pygame.Rect, bounds: pygame.Rect) -> None:
    r.x = max(bounds.left, min(r.x, bounds.right - r.width))
    r.y = max(bounds.top, min(r.y, bounds.bottom - r.height))


@dataclass
class State:
    bricks: list[tuple[pygame.Rect, tuple]] = field(default_factory=list)
    queue: list[tuple[int, int, tuple]] = field(default_factory=list)
    last_place_time: int = 0
    timer_running: bool = False
    timer_start: int = 0
    time_left: int = BUILD_SECONDS
    time_up: bool = False


S = State()


# Helpers
def ui_text(surf, text, font, pos):
    surf.blit(font.render(text, True, WHITE), pos)


def draw_brick(surf, rect, color=WHITE, outline=OUTLINE):
    pygame.draw.rect(surf, color, rect)
    pygame.draw.rect(surf, outline, rect, 1)


# Gameplay logic
def fill_queue(state: State):
    while len(state.queue) < QUEUE_SIZE:
        w = random.randint(W_MIN, W_MAX)
        h = random.randint(H_MIN, H_MAX)
        state.queue.append((w, h, WHITE))


def can_place(state: State) -> bool:
    return (now_ms() - state.last_place_time) >= COOLDOWN_MS


def place_from_queue(state: State, mouse_pos):
    if state.time_up or not state.queue or not can_place(state):
        return

    z = zone_rect()
    w, h, color = state.queue[0]

    # Placement logic/zones
    r = pygame.Rect(snap(mouse_pos[0] - w // 2), snap(mouse_pos[1] - h // 2), w, h)
    clamp_inside(r, z)
    if not z.contains(r):
        return

    # Eliminate possibility of overlap
    for existing, _ in state.bricks:
        if existing.colliderect(r):
            return

    state.bricks.append((r, color))
    state.queue.pop(0)
    fill_queue(state)
    state.last_place_time = now_ms()

    if not state.timer_running:
        state.timer_running = True
        state.timer_start = now_ms()


def update_timer(state: State):
    if state.time_up or not state.timer_running:
        return
    elapsed = (now_ms() - state.timer_start) // 1000
    state.time_left = max(0, BUILD_SECONDS - elapsed)
    if state.time_left == 0:
        state.time_up = True
        state.timer_running = False


# Draw functions
def draw_field(state: State, mouse_pos):
    # base field
    pygame.draw.rect(screen, (24, 24, 28), FIELD_RECT)

    # Show where blocks can be placed
    z = zone_rect()
    overlay = pygame.Surface((z.width, z.height), pygame.SRCALPHA)
    overlay.fill((255, 255, 255, 80))
    screen.blit(overlay, z.topleft)
    pygame.draw.rect(screen, OUTLINE, z, 1)

    # placed bricks
    for rect, color in state.bricks:
        draw_brick(screen, rect, color)

    # Block placement preview
    if state.queue and not state.time_up:
        w, h, _ = state.queue[0]
        ghost = pygame.Rect(snap(mouse_pos[0] - w // 2), snap(mouse_pos[1] - h // 2), w, h)
        clamp_inside(ghost, z)
        if z.contains(ghost):
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill((*WHITE, 100))
            screen.blit(s, ghost.topleft)
            pygame.draw.rect(screen, WHITE, ghost, 1)


def draw_sidebar(state: State):
    pygame.draw.rect(screen, (15, 15, 18), SIDEBAR)

    y = 30
    ui_text(screen, f"Time: {state.time_left:02d}s", FONT_M, (SIDEBAR.left + 16, y))
    y += 40

    # cooldown status
    if not state.time_up:
        if can_place(state):
            ui_text(screen, "Ready to place", FONT_S, (SIDEBAR.left + 16, y))
            y += 30
        else:
            wait = (COOLDOWN_MS - (now_ms() - state.last_place_time)) / 1000.0
            ui_text(screen, f"Cooldown: {wait:.1f}s", FONT_S, (SIDEBAR.left + 16, y))
            y += 30

    ui_text(screen, "Queue", FONT_M, (SIDEBAR.left + 16, y))
    y += 20

    # queue preview
    for w, h, _ in state.queue[:6]:
        box = pygame.Rect(SIDEBAR.left + 16, y, 160, 42)
        pygame.draw.rect(screen, (26, 26, 32), box, border_radius=6)
        pygame.draw.rect(screen, OUTLINE, box, 1, border_radius=6)

        scale = min((box.width - 14) / w, (box.height - 14) / h, 1.0)
        bw, bh = max(6, int(w * scale)), max(6, int(h * scale))
        bx = box.centerx - bw // 2
        by = box.centery - bh // 2
        draw_brick(screen, pygame.Rect(bx, by, bw, bh))
        y += 60


def draw_game_complete(state: State):
    if state.time_up:
        msg = FONT_L.render("Game Complete", True, WHITE)
        screen.blit(msg, msg.get_rect(center=(FIELD_RECT.centerx, HEI - 60)))


# Main
def main():
    fill_queue(S)
    while True:
        dt = clock.tick(FPS) / 1000
        mouse_pos = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if (
                e.type == pygame.MOUSEBUTTONDOWN
                and e.button == 1
                and zone_rect().collidepoint(mouse_pos)
            ):
                place_from_queue(S, mouse_pos)

        update_timer(S)

        screen.fill(BG)
        draw_field(S, mouse_pos)
        draw_sidebar(S)
        draw_game_complete(S)
        pygame.display.flip()


if __name__ == "__main__":
    main()
