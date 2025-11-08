"""Brick Breaker logic by Phoebe-Feathers."""

import sys
from dataclasses import dataclass, field

import pygame

pygame.init()

# Configure
WID, HEI = 900, 600
FPS = 60
BG = (18, 18, 22)
WHITE = (255, 255, 255)
OUTLINE = (140, 140, 140)

PADDLE_W, PADDLE_H = 120, 16
PADDLE_SPEED = 480

BALL_RADIUS = 8
BALL_SPEED = 420

COUNTDOWN_SECONDS = 45

# Window setup
screen = pygame.display.set_mode((WID, HEI))
pygame.display.set_caption("Brick Breaker Game")
clock = pygame.time.Clock()

FONT_S = pygame.font.SysFont(None, 24)
FONT_M = pygame.font.SysFont(None, 28)
FONT_L = pygame.font.SysFont(None, 64)


# Time helper
def now_ms():
    return pygame.time.get_ticks()


# Game state
@dataclass
class State:
    paddle: pygame.Rect = field(
        default_factory=lambda: pygame.Rect((WID - PADDLE_W) // 2, HEI - 40, PADDLE_W, PADDLE_H)
    )
    ball_pos: pygame.Vector2 = field(
        default_factory=lambda: pygame.Vector2(
            (WID - PADDLE_W) // 2 + PADDLE_W // 2, HEI - 40 - BALL_RADIUS - 1
        )
    )
    ball_vel: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    launched: bool = False

    bricks: list[pygame.Rect] = field(default_factory=list)

    timer_running: bool = False
    time_start_ms: int = 0
    time_left: int = COUNTDOWN_SECONDS

    game_over: bool = False
    player_won: bool = False


S = State()


# Brick layout (temporary demo bricks)
def make_demo_bricks():
    bricks = []
    cols, rows = 10, 6
    gap = 4
    left_margin = 20
    top = 80
    cell_w = (WID - 2 * left_margin) // cols
    cell_h = 28

    for r in range(rows):
        for c in range(cols):
            x = left_margin + c * cell_w + gap // 2
            y = top + r * cell_h + gap // 2
            w = cell_w - gap
            h = cell_h - gap
            bricks.append(pygame.Rect(x, y, w, h))

    return bricks


# Initial setup (no reset later)
S.bricks = make_demo_bricks()


# Launch ball
def launch_ball():
    if S.launched or S.game_over or S.player_won:
        return
    S.launched = True
    S.ball_vel.update(BALL_SPEED * 0.45, -BALL_SPEED)
    S.ball_vel.scale_to_length(BALL_SPEED)

    if not S.timer_running:
        S.timer_running = True
        S.time_start_ms = now_ms()


# Timer update
def update_timer():
    if not S.timer_running or S.game_over or S.player_won:
        return
    elapsed = (now_ms() - S.time_start_ms) // 1000
    S.time_left = max(0, COUNTDOWN_SECONDS - elapsed)
    if S.time_left == 0:
        S.game_over = True


# Paddle movement
def move_paddle(dt):
    keys = pygame.key.get_pressed()
    dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(
        keys[pygame.K_LEFT] or keys[pygame.K_a]
    )
    S.paddle.x += int(dx * PADDLE_SPEED * dt)
    S.paddle.clamp_ip(pygame.Rect(0, 0, WID, HEI))

    if not S.launched:
        S.ball_pos.update(S.paddle.centerx, S.paddle.top - BALL_RADIUS - 1)


# Ball movement
def update_ball(dt):
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
        S.ball_pos.update(S.paddle.centerx, S.paddle.top - BALL_RADIUS - 1)


# Paddle collision
def collide_paddle():
    if not S.launched or S.game_over or S.player_won:
        return

    ball_rect = pygame.Rect(
        S.ball_pos.x - BALL_RADIUS, S.ball_pos.y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2
    )

    if ball_rect.colliderect(S.paddle) and S.ball_vel.y > 0:
        offset = (ball_rect.centerx - S.paddle.centerx) / (S.paddle.width / 2)
        S.ball_vel.y *= -1
        S.ball_vel.x = (BALL_SPEED * 0.9) * offset
        S.ball_vel.scale_to_length(BALL_SPEED)


# Brick collision
def collide_bricks():
    if not S.launched or S.game_over or S.player_won:
        return

    ball_rect = pygame.Rect(
        S.ball_pos.x - BALL_RADIUS, S.ball_pos.y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2
    )

    hit = None
    for i, rect in enumerate(S.bricks):
        if rect.colliderect(ball_rect):
            hit = i
            overlap = [
                ball_rect.right - rect.left,
                rect.right - ball_rect.left,
                ball_rect.bottom - rect.top,
                rect.bottom - ball_rect.top,
            ]
            if min(overlap[:2]) < min(overlap[2:]):
                S.ball_vel.x *= -1
            else:
                S.ball_vel.y *= -1
            break

    if hit is not None:
        S.bricks.pop(hit)


# Draw
def draw():
    screen.fill(BG)

    for r in S.bricks:
        pygame.draw.rect(screen, WHITE, r)
        pygame.draw.rect(screen, OUTLINE, r, 1)

    pygame.draw.rect(screen, WHITE, S.paddle)
    pygame.draw.circle(screen, WHITE, (int(S.ball_pos.x), int(S.ball_pos.y)), BALL_RADIUS)

    ui_top = "Arrow keys or A/D to move   |   Space to launch"
    screen.blit(FONT_S.render(ui_top, True, WHITE), (12, 10))

    timer = FONT_M.render(f"Time: {S.time_left:02d}s", True, WHITE)
    screen.blit(timer, (WID - timer.get_width() - 16, 10))

    if S.player_won:
        msg = FONT_L.render("You Win!", True, WHITE)
        screen.blit(msg, msg.get_rect(center=(WID // 2, HEI // 2)))

    elif S.game_over:
        msg = FONT_L.render("Time's Up", True, WHITE)
        screen.blit(msg, msg.get_rect(center=(WID // 2, HEI // 2)))

    pygame.display.flip()


# Main
def main():
    while True:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                launch_ball()

        move_paddle(dt)
        update_ball(dt)
        collide_paddle()
        collide_bricks()
        update_timer()
        draw()


if __name__ == "__main__":
    main()
