"""Brick Placer logic by Phoebe-Feathers."""

import queue  # non-blocking reads from net.incoming
import random
import sys
from dataclasses import dataclass, field

import pygame

# UI integration: use local UI modules rather than package paths
from brickbreaker.UI.ball import Ball, draw_ball_stud
from brickbreaker.UI.bricks import Brick, draw_brick
from brickbreaker.UI.config import BRICK_HIT_POINTS, BRICK_PALETTE
from brickbreaker.UI.end_screens import run_end_screen
from brickbreaker.UI.paddle import Paddle

# from brickbreaker.UI.end_screens import run_end_screen  # UI-only: show end screen on round end

pygame.init()

# Configure
WID, HEI = 1120, 600
FPS = 60
BG = (18, 18, 22)
WHITE: pygame.Color = (255, 255, 255)
OUTLINE = (160, 160, 160)
SIDEBAR_W = 220
ZONE_H = 400

GRID = 10

# Must match breaker.py
PADDLE_W = 10  # set to your breaker's value
PADDLE_H = 1  # set to your breaker's value
BALL_RADIUS = 8  # set to your breaker's value

# Brick queue
W_MIN, W_MAX = 2, 6
H_MIN, H_MAX = 1, 2
QUEUE_SIZE = 6

# Timers
BUILD_SECONDS = 120
COOLDOWN_MS = 1000

# Window popup - will be initialized in main()
screen = None
clock = None

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


def clamp_inside(r: Brick, bounds: pygame.Rect) -> None:
    r.rect().x = max(bounds.left, min(r.rect().x, bounds.right - r.rect().width))
    r.rect().y = max(bounds.top, min(r.rect().y, bounds.bottom - r.rect().height))


@dataclass
class State:
    bricks: list[tuple[Brick, tuple]] = field(default_factory=list)
    queue: list[tuple[int, int, tuple]] = field(default_factory=list)
    last_place_time: int = 0
    timer_running: bool = False
    timer_start: int = 0
    time_left: int = BUILD_SECONDS
    time_up: bool = False
    # Round status flags
    game_over: bool = False
    player_won: bool = False  # True when placer wins (time), False when breaker wins
    # Mirrored render state from the breaker (host)
    paddle: Paddle = field(
        default_factory=lambda: Paddle((WID - PADDLE_W) // 2, HEI - 40, PADDLE_W)
    )
    ball_pos: pygame.Vector2 = field(
        default_factory=lambda: pygame.Vector2(
            (WID - PADDLE_W) // 2 + PADDLE_W // 2, HEI - 40 - BALL_RADIUS - 1
        )
    )
    launched: bool = False

    # UI-only guard so the end screen shows once without affecting logic
    end_shown: bool = False


S = State()


# Helpers
def ui_text(surf, text, font, pos):
    surf.blit(font.render(text, True, WHITE), pos)


# --- Network helpers for sync ---
def _deserialize_bricks(items: list[dict]) -> list[tuple[pygame.Rect, tuple]]:
    """Convert [{'x','y','w','h'}, ...] to [(Rect, WHITE), ...] to match S.bricks format."""
    bricks = []
    for it in items:
        color = it.get("color", "red")
        b = Brick(it["x"], it["y"], it["w"], it["h"], color)
        bricks.append((b, color))
    return bricks

def pump_incoming_client_for_sync(net):
    """Client (placer) applies full map and timer sent by host breaker."""
    if not net or getattr(net, "is_host", False):
        return
    while True:
        try:
            msg = net.incoming.get_nowait()
        except queue.Empty:
            break

        t = msg.get("type")
        if t == "sync_bricks":
            S.bricks = _deserialize_bricks(msg["bricks"])

        elif t == "game_over":
            winner = msg.get("winner")
            reason = msg.get("reason")
            # Mirror the host's end state and freeze
            if winner == "breaker" and reason == "goal":
                S.player_won = False
                S.game_over = True
                S.time_up = False
            elif winner == "placer" and reason == "time":
                S.player_won = True
                S.game_over = True
                S.time_up = True
            S.timer_running = False

        elif t == "brick_remove":
            idx = int(msg["index"])
            if 0 <= idx < len(S.bricks):
                S.bricks.pop(idx)

        elif t == "timer_state":
            # Mirror the host's timer
            S.time_left = int(msg.get("time_left", S.time_left))

        elif t == "render_state":
            # Mirror the host's paddle & ball positions
            px = int(msg.get("paddle_x", S.paddle.x))
            S.paddle.x = px
            # keep the paddle on-screen within the field area
            S.paddle.rect().clamp_ip(FIELD_RECT)

            S.ball_pos.update(
                float(msg.get("ball_x", S.ball_pos.x)),
                float(msg.get("ball_y", S.ball_pos.y)),
            )
            S.launched = bool(msg.get("launched", S.launched))


# Gameplay logic
def fill_queue(state: State):
    while len(state.queue) < QUEUE_SIZE:
        w = random.randint(W_MIN, W_MAX)
        h = random.randint(H_MIN, H_MAX)

        base_color = random.choice(BRICK_PALETTE)
        roll = random.random()

        if roll < 0.06:
            color = "purple"
        elif roll < 0.10:
            color = "pink"
        else:
            color = base_color

        state.queue.append((w, h, color))


def can_place(state: State) -> bool:
    return (now_ms() - state.last_place_time) >= COOLDOWN_MS


def place_from_queue(state: State, mouse_pos, net=None):
    if state.game_over or state.time_up or not state.queue or not can_place(state):
        return

    z = zone_rect()
    w, h, color = state.queue[0]

    # Placement logic/zones
    r = Brick(
        snap(mouse_pos[0] - w // 2),
        snap(mouse_pos[1] - h // 2),
        w,
        h,
        color,
        False,
        BRICK_HIT_POINTS[color],
    )
    clamp_inside(r, z)
    if not z.contains(r):
        return

    # Eliminate possibility of overlap
    for existing, _ in state.bricks:
        if existing.rect().colliderect(r):
            return

    state.bricks.append((r, color))

    # Tell the host breaker about this new brick (protocol unchanged)
    if net and not getattr(net, "is_host", False):
        net.send({"type": "brick_add", "x": r.x, "y": r.y, "w": r.studs_x, "h": r.studs_y, "color": color})

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
        draw_brick(screen, rect)

    # Draw mirrored paddle and ball from host
    S.paddle.draw(screen)
    draw_ball_stud(screen, Ball(int(state.ball_pos.x), int(state.ball_pos.y)), BALL_RADIUS)

    # Block placement preview
    if state.queue and not state.time_up and not state.game_over:
        w, h, _ = state.queue[0]
        ghost = Brick(snap(mouse_pos[0] - w // 2), snap(mouse_pos[1] - h // 2), w, h, "red")
        clamp_inside(ghost, z)
        if z.contains(ghost):
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill((*WHITE, 100))
            screen.blit(s, ghost.rect().topleft)
            pygame.draw.rect(screen, WHITE, ghost, 1)


def draw_sidebar(state: State):
    pygame.draw.rect(screen, (15, 15, 18), SIDEBAR)

    y = 30
    ui_text(screen, f"Time: {state.time_left:02d}s", FONT_M, (SIDEBAR.left + 16, y))
    y += 40

    # cooldown status
    if not state.time_up and not state.game_over:
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
    for w, h, color in state.queue[:6]:
        box = pygame.Rect(SIDEBAR.left + 16, y, 160, 42)
        pygame.draw.rect(screen, (26, 26, 32), box, border_radius=6)
        pygame.draw.rect(screen, OUTLINE, box, 1, border_radius=6)

        scale = min((box.width - 14) / w, (box.height - 14) / h, 1.0)
        bw, bh = max(6, int(w * scale)), max(6, int(h * scale))
        bx = box.centerx - bw // 2
        by = box.centery - bh // 2
        draw_brick(screen, Brick(bx, by, w, h, color))
        y += 60


def draw_game_complete(state: State):
    if state.game_over:
        if state.player_won:
            text = "Placer Wins (Time)!"
        else:
            text = "Breaker Wins (Goal)!"
        msg = FONT_L.render(text, True, WHITE)
        screen.blit(msg, msg.get_rect(center=(FIELD_RECT.centerx, HEI - 60)))


# Main
def main(net=None):
    global screen, clock
    if not pygame.get_init():
        pygame.init()

    screen = pygame.display.set_mode((WID, HEI))
    pygame.display.set_caption("Brick Builder Game")
    clock = pygame.time.Clock()

    # Role-aware title
    if net and not getattr(net, "is_host", False):
        pygame.display.set_caption("Placer (Client)")
    elif net and getattr(net, "is_host", False):
        pygame.display.set_caption("Placer (Host)")
    else:
        pygame.display.set_caption("Placer (Local)")

    # Ask the host breaker for the current full map (covers late joins)
    if net and not getattr(net, "is_host", False):
        net.send({"type": "sync_request"})

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
                place_from_queue(S, mouse_pos, net)

        pump_incoming_client_for_sync(net)
        if not (S.game_over or S.player_won):
            update_timer(S)

        screen.fill(BG)
        draw_field(S, mouse_pos)
        draw_sidebar(S)
        draw_game_complete(S)
        pygame.display.flip()

        # UI-only: show end screen once the round is finished (placer perspective)
        if (S.game_over or S.player_won) and not S.end_shown:
            run_end_screen("placer", bool(S.player_won))
            S.end_shown = True
            return


if __name__ == "__main__":
    main()
