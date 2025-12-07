"""Brick Breaker logic by Phoebe-Feathers."""

import queue
import sys
from dataclasses import dataclass, field, replace

import pygame

from brickbreaker.UI.ball import Ball, draw_ball_stud
from brickbreaker.UI.bricks import Brick, draw_brick
from brickbreaker.UI.paddle import Paddle  # non-blocking reads from net.incoming
from brickbreaker.UI.end_screens import run_end_screen
from brickbreaker.world import BOARD_W, BOARD_H
from brickbreaker.layout import get_breaker_layout, world_to_screen

if not pygame.get_init():
    pygame.init()

# Configure window size, game area, etc
WINDOW_SIZE, BOARD_RECT, HUD_RECT = get_breaker_layout()
SCREEN_W, SCREEN_H = WINDOW_SIZE      # actual OS window size
WID, HEI = BOARD_W, BOARD_H           # logical game-world size
FPS = 60
BG = (18, 18, 22)
WHITE = (255, 255, 255)
OUTLINE = (140, 140, 140)

# configure the paddle
PADDLE_W = 10
PADDLE_SPEED = 480
PADDLE_BOTTOM_MARGIN = 40  # distance the paddle is from the bottom of the screen

# configure the ball
BALL_RADIUS = 8
BALL_SPEED = 420

# configure timers
COUNTDOWN_SECONDS = 120
BREAKER_DELAY_SECONDS = 15

EXPLOSION_RADIUS = 80
PLACER_BUFF_AMOUNT = 2

_last_timer_send_ms = 0
_last_game_over_sent = False
_last_state_send_ms = 0

_explosion_pending_sync = False

FONT_S = pygame.font.SysFont(None, 24)
FONT_M = pygame.font.SysFont(None, 28)
FONT_L = pygame.font.SysFont(None, 64)

def now_ms():
    """Return the current pygame clock time in milliseconds"""
    return pygame.time.get_ticks()

# Game state
@dataclass
class State:
    paddle: Paddle = field(
        default_factory=lambda: Paddle(0, 0, PADDLE_W)
    )

    ball_pos: pygame.Vector2 = field(
        default_factory=lambda: pygame.Vector2(0, 0)
    )

    ball_vel: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    launched: bool = False

    bricks: list[Brick] = field(default_factory=list)

    timer_running: bool = False
    time_start_ms: int = 0
    time_left: int = COUNTDOWN_SECONDS

    game_over: bool = False
    player_won: bool = False
    end_shown: bool = False

    breaker_delay_start_ms: int = 0
    breaker_delay_active: bool = False

    hud_status: str = ""


S = State()

def reset_initial_positions():
    """Place paddle and ball centered on the board in world coordinates"""
    # Center paddle by its *pixel* width
    S.paddle.x = (WID - S.paddle.w) // 2
    S.paddle.y = HEI - PADDLE_BOTTOM_MARGIN

    # Put ball centered on the paddle, just above it
    paddle_rect = S.paddle.rect()
    S.ball_pos.update(
        paddle_rect.centerx,
        paddle_rect.top - BALL_RADIUS - 1,
    )

# Do this once at startup to ensure sync
reset_initial_positions()

def _serialize_bricks(bricks: list[Brick]) -> list[dict]:
    """Convert a list of Brick objects into simple dicts for network messages"""
    return [
        {"x": brick.rect().x, "y": brick.rect().y, "w": brick.studs_x, "h": brick.studs_y, "color": brick.color_key}
        for brick in bricks
    ]

def _apply_placer_buff():
    """Increase the durability of all breakable bricks as a placer power-up effect"""
    for b in S.bricks:
        if not b.unbreakable:
            b.hits_left += PLACER_BUFF_AMOUNT

def _apply_explosion(center_brick: Brick):
    """Apply an explosion around the given brick, damaging nearby bricks and marking state for sync"""
    global _explosion_pending_sync
    cx, cy = center_brick.rect().center
    survivors: list[Brick] = []
    for b in S.bricks:
        if b.unbreakable:
            survivors.append(b)
            continue

        dx = b.rect().centerx - cx
        dy = b.rect().centery - cy
        if dx * dx + dy * dy <= EXPLOSION_RADIUS * EXPLOSION_RADIUS:
            b.hits_left -= 2
            if b.hits_left <= 0:
                continue
        survivors.append(b)
    S.bricks = survivors
    _explosion_pending_sync = True


def launch_ball():
    """Launch the ball from the paddle."""

    # Do not allow launching before the placer has started the round
    if not S.timer_running:
        return

    # Ball launch delay logic
    if S.breaker_delay_active:
        elapsed = (now_ms() - S.breaker_delay_start_ms) // 1000
        if elapsed < BREAKER_DELAY_SECONDS:
            return
        else:
            S.breaker_delay_active = False

    if S.launched or S.game_over or S.player_won:
        return

    S.launched = True
    S.ball_vel.update(BALL_SPEED * 0.45, -BALL_SPEED)
    S.ball_vel.scale_to_length(BALL_SPEED)

def update_timer():
    """Update the round countdown timer. Triggers game over if it hits 0"""
    if not S.timer_running or S.game_over or S.player_won:
        return
    elapsed = (now_ms() - S.time_start_ms) // 1000
    S.time_left = max(0, COUNTDOWN_SECONDS - elapsed)
    if S.time_left == 0:
        S.game_over = True

def move_paddle(dt):
    """Handles paddle movement, and ensure the ball stays attached to the paddle pre-launch"""
    keys = pygame.key.get_pressed()
    dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(
        keys[pygame.K_LEFT] or keys[pygame.K_a]
    )

    if dx != 0:
        S.paddle.x += int(dx * PADDLE_SPEED * dt)

        # Hard clamp: keep paddle fully inside [0, WID]
        # S.paddle.w is the paddle's pixel width
        if S.paddle.x < 0:
            S.paddle.x = 0
        if S.paddle.x + S.paddle.w > WID:
            S.paddle.x = WID - S.paddle.w

    # Keep ball riding on the paddle until launch
    if not S.launched:
        r = S.paddle.rect()
        S.ball_pos.update(r.centerx, r.top - BALL_RADIUS - 1)

def update_ball(dt):
    """Handles ball movement, boundaries, and resets the ball when it falls off the map."""
    if not S.launched or S.game_over or S.player_won:
        return

    S.ball_pos += S.ball_vel * dt

    # wall collisions
    if S.ball_pos.x <= BALL_RADIUS or S.ball_pos.x >= WID - BALL_RADIUS:
        S.ball_vel.x *= -1

    # win condition
    if S.ball_pos.y <= BALL_RADIUS:
        S.player_won = True
        return

    # fall off = ball rests on paddle and game does NOT reset
    if S.ball_pos.y >= HEI - BALL_RADIUS:
        S.launched = False
        S.ball_vel.update(0, 0)
        S.ball_pos.update(S.paddle.rect().centerx, S.paddle.rect().top - BALL_RADIUS - 1)

def collide_paddle():
    """Handles ball <> paddle collision. Bounces the ball based off impact offset along the paddle"""
    if not S.launched or S.game_over or S.player_won:
        return

    ball_rect = pygame.Rect(
        S.ball_pos.x - BALL_RADIUS, S.ball_pos.y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2
    )

    if ball_rect.colliderect(S.paddle.rect()) and S.ball_vel.y > 0:
        offset = (ball_rect.centerx - S.paddle.rect().centerx) / (S.paddle.rect().width / 2)
        S.ball_vel.y *= -1
        S.ball_vel.x = (BALL_SPEED * 0.9) * offset
        S.ball_vel.scale_to_length(BALL_SPEED)

def collide_bricks():
    """Handles ball <> brick collision, updates brick HP, triggers explosions, and
    returns a removed index for any bricks that are destroyed."""
    if not S.launched or S.game_over or S.player_won:
        return None

    ball_rect = pygame.Rect(
        S.ball_pos.x - BALL_RADIUS,
        S.ball_pos.y - BALL_RADIUS,
        BALL_RADIUS * 2,
        BALL_RADIUS * 2
    )

    for i, brick in enumerate(S.bricks):
        r = brick.rect()

        # Only process damage if the ball actually hits the brick
        if r.colliderect(ball_rect):
            overlap = [
                ball_rect.right - r.left,
                r.right - ball_rect.left,
                ball_rect.bottom - r.top,
                r.bottom - ball_rect.top,
            ]
            if min(overlap[:2]) < min(overlap[2:]):
                S.ball_vel.x *= -1
            else:
                S.ball_vel.y *= -1

            if not brick.unbreakable:
                brick.hits_left -= 1

                # Pink bricks trigger explosion + HUD message
                if brick.hits_left <= 0 and brick.color_key == "pink":
                    S.hud_status = "Pink brick: Boom!"
                    center_brick = S.bricks.pop(i)
                    _apply_explosion(center_brick)
                    return None

                # Purple bricks give buff + HUD message
                if brick.hits_left <= 0:
                    if brick.color_key == "purple":
                        S.hud_status = "Purple brick: +2 HP to all bricks!"
                    S.bricks.pop(i)
                    return i

                return None

            else:
                # Unbreakable brick hit, just bounce
                return None

    return None

def draw_hud():
    """Draws the top HUD bar. Can resize without impacting the game map."""
    pygame.draw.rect(screen, (15, 15, 18), HUD_RECT)
    pygame.draw.line(
        screen,
        OUTLINE,
        (HUD_RECT.left, HUD_RECT.bottom),
        (HUD_RECT.right, HUD_RECT.bottom),
        1,
    )

    # Left: controls / instructions
    ui_top = "Arrow keys or A/D to move   |   Space to launch"
    txt = FONT_S.render(ui_top, True, WHITE)
    screen.blit(txt, (HUD_RECT.left + 16, HUD_RECT.top + 8))

    # Optional status line 
    if S.hud_status:
        status_txt = FONT_S.render(S.hud_status, True, WHITE)
        screen.blit(
            status_txt,
            (HUD_RECT.left + 16, HUD_RECT.top + 8 + FONT_S.get_height() + 4),
        )
    
    # Right: timer
    timer = FONT_M.render(f"Time: {S.time_left:02d}s", True, WHITE)
    screen.blit(timer, (HUD_RECT.right - timer.get_width() - 16, HUD_RECT.top + 6))

    # Launch delay info under the timer
    if not S.launched and not (S.game_over or S.player_won):
        if S.breaker_delay_active:
            remaining = BREAKER_DELAY_SECONDS - (now_ms() - S.breaker_delay_start_ms) // 1000
        else:
            remaining = BREAKER_DELAY_SECONDS
        remaining = max(0, remaining)

        delay = FONT_S.render(f"Launch available in: {remaining:2d}s", True, WHITE)
        screen.blit(
            delay,
            (
                HUD_RECT.right - delay.get_width() - 16,
                HUD_RECT.top + 6 + FONT_M.get_height() + 6,
            ),
        )

# Draw
def draw():
    """Renders the full window and all its elements."""
    screen.fill(BG)

    for brick in S.bricks:
        # Brick lives in world space; map to screen space for drawing
        r_world = brick.rect()
        bx, by = world_to_screen(r_world.topleft, BOARD_RECT)

        # Make a temporary screen-space copy so we don't mutate game state
        b_screen = replace(brick, x=bx, y=by)
        draw_brick(screen, b_screen)

    # Paddle: world -> screen
    px, py = world_to_screen((S.paddle.x, S.paddle.y), BOARD_RECT)
    p_screen = replace(S.paddle, x=px, y=py)
    p_screen.draw(screen)

    # Ball: world -> screen
    bx, by = world_to_screen((S.ball_pos.x, S.ball_pos.y), BOARD_RECT)
    draw_ball_stud(screen, Ball(int(bx), int(by)))

    # Draw HUD on top
    draw_hud()

    if S.player_won:
        msg = FONT_L.render("You Win!", True, WHITE)
        screen.blit(msg, msg.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2)))

    elif S.game_over:
        msg = FONT_L.render("Time's Up", True, WHITE)
        screen.blit(msg, msg.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2)))

    pygame.display.flip()


def _pump_incoming_host_for_sync(net):
    """Host (breaker) replies to sync_request and applies brick_add from client."""
    if not net or not getattr(net, "is_host", False):
        return
    while True:
        try:
            msg = net.incoming.get_nowait()
        except queue.Empty:
            break

        t = msg.get("type")

        # Once the round is over, stop replying to network requests.
        if S.game_over or S.player_won:
            continue

        if t == "sync_request":
            # 1) full map
            net.send({"type": "sync_bricks", "bricks": _serialize_bricks(S.bricks)})
            # 2) immediate render snapshot (so the client sees paddle/ball instantly)
            net.send(
                {
                    "type": "render_state",
                    "paddle_x": int(S.paddle.x),
                    "ball_x": float(S.ball_pos.x),
                    "ball_y": float(S.ball_pos.y),
                    "launched": bool(S.launched),
                }
            )

        elif t == "brick_add":
            if S.game_over or S.player_won:
                continue  # ignore adds after round ends

            color = msg.get("color", "red") # PHOEBE: Get brick color

            if color == "purple": # PHOEBE: powerup logic
                _apply_placer_buff() # PHOEBE: powerup logic

            r = Brick(msg["x"], msg["y"], msg["w"], msg["h"], color) # PHOEBE: removed "red"/change to color
            S.bricks.append(r)

            # 15 second delay until ball launch starts when placer places first brick
            if not S.breaker_delay_active:
                S.breaker_delay_active = True
                S.breaker_delay_start_ms = now_ms()
            if not S.timer_running and not (S.game_over or S.player_won):
                S.timer_running = True
                S.time_start_ms = now_ms()

def main(net=None):
    """Main breaker gameplay loop"""
    global _last_timer_send_ms, _last_game_over_sent, _last_state_send_ms, _explosion_pending_sync
    global screen, clock

    # Make sure pygame core and display are initialized (menu may have called display.quit())
    if not pygame.get_init():
        pygame.init()

    if not pygame.display.get_init():
        pygame.display.init()

    # Window setup
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()

    # Title by role
    if net and getattr(net, "is_host", False):
        pygame.display.set_caption("Breaker (Host)")
    else:
        pygame.display.set_caption("Breaker (Local)") # unused, only for testing

    # Host proactively sends full map once (client may already be connected)
    if net and getattr(net, "is_host", False):
        net.send({"type": "sync_bricks", "bricks": _serialize_bricks(S.bricks)})

    while True:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if not (S.game_over or S.player_won):  # freeze input after game over
                if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                    launch_ball()

        _pump_incoming_host_for_sync(net)

        if not (S.game_over or S.player_won):  # freeze simulation after game over
            move_paddle(dt)
            update_ball(dt)
            collide_paddle()
            removed = collide_bricks()
            if net and getattr(net, "is_host", False) and removed is not None:
                net.send({"type": "brick_remove", "index": removed})

        if net and getattr(net, "is_host", False) and _explosion_pending_sync and not (S.game_over or S.player_won):
            net.send({"type": "sync_bricks", "bricks": _serialize_bricks(S.bricks)})
            _explosion_pending_sync = False

        # Send paddle/ball render state to placer ~30 Hz
        if net and getattr(net, "is_host", False) and not (S.game_over or S.player_won):
            now = now_ms()
            if now - _last_state_send_ms > 33:  # ~30 Hz
                _last_state_send_ms = now
                net.send(
                    {
                        "type": "render_state",
                        "paddle_x": int(S.paddle.x),
                        "ball_x": float(S.ball_pos.x),
                        "ball_y": float(S.ball_pos.y),
                        "launched": bool(S.launched),
                    }
                )

        update_timer()

        # End-of-round sync (host -> client) exactly once
        if net and getattr(net, "is_host", False) and not _last_game_over_sent:
            if S.player_won:
                net.send({"type": "game_over", "winner": "breaker", "reason": "goal"})
                _last_game_over_sent = True
            elif S.game_over:  # timer expired => placer wins
                net.send({"type": "game_over", "winner": "placer", "reason": "time"})
                _last_game_over_sent = True

        # Host broadcasts timer to client ~1 Hz, but not after game over
        if net and getattr(net, "is_host", False) and not (S.game_over or S.player_won):
            now = now_ms()
            if S.timer_running and not (S.game_over or S.player_won):
                if now - _last_timer_send_ms > 1000:
                    _last_timer_send_ms = now
                    net.send({"type": "timer_state", "time_left": int(S.time_left)})
        draw()

        # UI-only: show end screen once the round is finished (breaker perspective)
        if (S.game_over or S.player_won) and not S.end_shown:
            run_end_screen("breaker", bool(S.player_won))
            S.end_shown = True
            return

if __name__ == "__main__":
    main()
