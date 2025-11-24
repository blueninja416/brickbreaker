# brickbreaker/UI/end_screens.py
from __future__ import annotations

import random

import pygame as pg

from .config import COLORS, FPS, GAME_H, GAME_W, SCALE, STUD_UNIT
from .graphics import darker, draw_pixel_text, lighter

# ------------------------------ Border & Title --------------------------- #


def draw_brick_border(surf: pg.Surface) -> None:
    """Draw a colorful LEGO brick border around the screen."""
    colors = [COLORS[c] for c in ("red", "yellow", "green", "blue")]
    w, h = surf.get_size()
    brick_h = 10
    brick_w = 16

    # Top/bottom rows
    x = 0
    ci = 0
    while x < w:
        r_top = pg.Rect(x, 0, brick_w, brick_h)
        r_bot = pg.Rect(x, h - brick_h, brick_w, brick_h)
        col = colors[ci % len(colors)]
        for r in (r_top, r_bot):
            pg.draw.rect(surf, col, r)
            pg.draw.line(surf, lighter(col, 25), (r.left, r.top), (r.right - 1, r.top))
            pg.draw.line(surf, darker(col, 35), (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
            cx = r.left + brick_w // 2
            cy = r.top + 1
            pg.draw.circle(surf, lighter(col, 10), (cx, cy), 3)
            pg.draw.circle(surf, darker(col, 40), (cx, cy), 3, 1)
        x += brick_w
        ci += 1

    # Left/right columns
    y = brick_h
    ci = 0
    while y < h - brick_h:
        r_l = pg.Rect(0, y, brick_w, brick_h)
        r_r = pg.Rect(w - brick_w, y, brick_w, brick_h)
        col = colors[ci % len(colors)]
        for r in (r_l, r_r):
            pg.draw.rect(surf, col, r)
            pg.draw.line(surf, lighter(col, 25), (r.left, r.top), (r.right - 1, r.top))
            pg.draw.line(surf, darker(col, 35), (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
            cx = r.left + brick_w // 2
            cy = r.top + 1
            pg.draw.circle(surf, lighter(col, 10), (cx, cy), 3)
            pg.draw.circle(surf, darker(col, 40), (cx, cy), 3, 1)
        y += brick_h
        ci += 1


def draw_title_bricks(surf: pg.Surface, text: str, x: int, y: int) -> None:
    """Render a colorful LEGO-style title (matching the menu look)."""
    colors = [COLORS[c] for c in ("red", "yellow", "green", "blue")]
    font = pg.font.SysFont("couriernew", 24, bold=True)
    gap = 3
    brick_h = 16
    brick_w = 14
    cx = x
    ci = 0
    for ch in text:
        if ch == " ":
            cx += brick_w // 2
            continue
        r = pg.Rect(cx, y, brick_w, brick_h)
        col = colors[ci % len(colors)]
        pg.draw.rect(surf, col, r, border_radius=2)
        pg.draw.line(surf, lighter(col, 25), (r.left, r.top), (r.right - 1, r.top))
        pg.draw.line(surf, darker(col, 35), (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
        # studs
        pg.draw.circle(surf, lighter(col, 10), (r.left + brick_w // 3, r.top + 2), 2)
        pg.draw.circle(surf, darker(col, 40), (r.left + brick_w // 3, r.top + 2), 2, 1)
        pg.draw.circle(surf, lighter(col, 10), (r.left + 2 * brick_w // 3, r.top + 2), 2)
        pg.draw.circle(surf, darker(col, 40), (r.left + 2 * brick_w // 3, r.top + 2), 2, 1)
        img = font.render(ch, True, (250, 250, 250))
        surf.blit(img, img.get_rect(center=r.center))
        cx += brick_w + gap
        ci += 1


# ------------------------------ CRUMBLE Reveal --------------------------- #


class _Tile:
    __slots__ = ("color", "h", "life", "vx", "vy", "w", "x", "y")

    def __init__(self, x, y, w, h, color, vx=0.0, vy=0.0, life=0.0):
        self.x, self.y, self.w, self.h, self.color = x, y, w, h, color
        self.vx, self.vy, self.life = vx, vy, life


def _draw_tile_brick(surf: pg.Surface, t: _Tile) -> None:
    r = pg.Rect(int(t.x), int(t.y), t.w, t.h)
    base = t.color
    pg.draw.rect(surf, base, r)
    pg.draw.line(surf, lighter(base, 25), (r.left, r.top), (r.right - 1, r.top))
    pg.draw.line(surf, darker(base, 35), (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
    cy = r.top + 2
    pg.draw.circle(surf, lighter(base, 10), (r.left + r.width // 3, cy), 2)
    pg.draw.circle(surf, darker(base, 40), (r.left + r.width // 3, cy), 2, 1)
    pg.draw.circle(surf, lighter(base, 10), (r.left + 2 * r.width // 3, cy), 2)
    pg.draw.circle(surf, darker(base, 40), (r.left + 2 * r.width // 3, cy), 2, 1)


def run_crumble_reveal(
    screen: pg.Surface, low: pg.Surface, reveal_text: str, timeout: float = 6.0
) -> None:
    """Cover with a LEGO wall, then let bricks fall away to reveal text underneath."""
    clock = pg.time.Clock()

    # Build a wall of tiles
    tiles: list[_Tile] = []
    colors = [COLORS[k] for k in ("red", "yellow", "green", "blue")]
    rng = random.Random()
    for gy in range(0, GAME_W, STUD_UNIT):
        for gx in range(
            0, GAME_H, STUD_UNIT
        ):  # NOTE: GAME_H used for rows; we draw in low (GAME_W x GAME_H)
            pass
    # Corrected: X goes across width, Y goes down height
    tiles.clear()
    for gy in range(0, GAME_H, STUD_UNIT):
        for gx in range(0, GAME_W, STUD_UNIT):
            t = _Tile(gx, gy, STUD_UNIT, int(STUD_UNIT * 0.9), rng.choice(colors))
            t.life = rng.uniform(0.2, 1.2)  # start delay per tile
            t.vx = rng.uniform(-20, 20)
            t.vy = 0
            tiles.append(t)

    # Pre-render reveal text
    font = pg.font.SysFont("couriernew", 26, bold=True)
    text_img = font.render(reveal_text, True, (250, 250, 250))
    tx = (GAME_W - text_img.get_width()) // 2
    ty = (GAME_H - text_img.get_height()) // 2

    elapsed = 0.0
    while True:
        dt = clock.tick(FPS) / 1000.0
        elapsed += dt
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
            if e.type == pg.KEYDOWN or e.type == pg.MOUSEBUTTONDOWN:
                return

        # Update physics
        all_gone = True
        for t in tiles:
            if t.life > 0:
                t.life -= dt
            else:
                t.vy += 200 * dt
                t.x += t.vx * dt
                t.y += t.vy * dt
            if t.y < GAME_H + 10:
                all_gone = False

        # Draw
        low.fill(COLORS["bg"])
        low.blit(text_img, (tx, ty))  # revealed underlayer
        for t in tiles:
            if -STUD_UNIT < t.x < GAME_W + STUD_UNIT and -STUD_UNIT < t.y < GAME_H + STUD_UNIT:
                _draw_tile_brick(low, t)
        draw_pixel_text(low, "Press any key...", GAME_W // 2 - 50, GAME_H - 16, COLORS["hud_dim"])

        up = pg.transform.scale(low, (GAME_W * SCALE, GAME_H * SCALE))
        screen.blit(up, (0, 0))
        pg.display.flip()

        if all_gone or elapsed > timeout:
            return


# ------------------------------ Orchestrator ----------------------------- #


def run_end_screen(role: str, won: bool) -> None:
    """Show end screen with CRUMBLE where specified, static LEGO title otherwise.

    - Breaker WIN   → CRUMBLE reveals "YOU WIN"
    - Breaker LOSE  → STATIC "YOU LOSE"
    - Placer  WIN   → STATIC "YOU WIN"
    - Placer  LOSE  → CRUMBLE reveals "YOU LOSE"
    """
    if not pg.get_init():
        pg.init()
    pg.display.set_caption("LEGO Brick Break — Result")
    screen = pg.display.set_mode((GAME_W * SCALE, GAME_H * SCALE))
    low = pg.Surface((GAME_W, GAME_H))

    role = (role or "").lower().strip()
    if role not in {"breaker", "placer"}:
        role = "breaker"

    # Decide mode
    crumble = (role == "breaker" and won) or (role == "placer" and not won)
    message = "YOU WIN" if won else "YOU LOSE"

    if crumble:
        run_crumble_reveal(screen, low, message)
        return

    # Static LEGO title (no build animation)
    clock = pg.time.Clock()
    low.fill(COLORS["bg"])
    draw_brick_border(low)
    text_px_width = len(message.replace(" ", "")) * 17 + message.count(" ") * 7
    start_x = max(8, (GAME_W - text_px_width) // 2)
    draw_title_bricks(low, message, x=start_x, y=GAME_H // 2 - 10)
    draw_pixel_text(
        low, "Press any key to continue", GAME_W // 2 - 80, GAME_H - 16, COLORS["hud_dim"]
    )
    up = pg.transform.scale(low, (GAME_W * SCALE, GAME_H * SCALE))

    while True:
        _ = clock.tick(FPS)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
            if e.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN):
                return
        screen.blit(up, (0, 0))
        pg.display.flip()
