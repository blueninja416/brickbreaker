"""
end_screens.py — LEGO Brick Break end screens (PyGame)

Animations (no assets):
- Breaker WIN  → CRUMBLE: a wall of bricks falls away to reveal "YOU WIN".
- Breaker LOSE → BUILD:  bricks get placed to build "YOU LOSE" letterforms.
- Placer  WIN  → BUILD:  bricks get placed to build "YOU WIN".
- Placer  LOSE → CRUMBLE: a brick wall falls to reveal "YOU LOSE".

Public API:
    run_end_screen(role: str, won: bool) -> None
        role in {"breaker", "placer"}; won is True/False.
        Blocks until the user presses any key or Esc, or a short auto-timeout.

Notes:
- Requires config.py and graphics.py in the same package.
- Everything is drawn vectorially; no images required.
- To integrate: from end_screens import run_end_screen; run_end_screen("breaker", True)
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Tuple

import pygame as pg

from config import GAME_W, GAME_H, SCALE, FPS, COLORS, STUD_UNIT
from graphics import lighter, darker, draw_pixel_text

# ---------------------------- Brick Tile Drawing ---------------------------- #

@dataclass
class Tile:
    x: int
    y: int
    w: int
    h: int
    color: Tuple[int,int,int]
    vx: float = 0.0
    vy: float = 0.0
    life: float = 0.0  # generic timer for effects


def draw_tile_brick(surf: pg.Surface, t: Tile):
    r = pg.Rect(int(t.x), int(t.y), t.w, t.h)
    base = t.color
    # body
    pg.draw.rect(surf, base, r)
    # top highlight, bottom shadow
    pg.draw.line(surf, lighter(base, 25), (r.left, r.top), (r.right-1, r.top))
    pg.draw.line(surf, darker(base, 35), (r.left, r.bottom-1), (r.right-1, r.bottom-1))
    # two tiny studs on top
    cy = r.top + 2
    pg.draw.circle(surf, lighter(base, 10), (r.left + r.width//3, cy), 2)
    pg.draw.circle(surf, darker(base, 40), (r.left + r.width//3, cy), 2, 1)
    pg.draw.circle(surf, lighter(base, 10), (r.left + 2*r.width//3, cy), 2)
    pg.draw.circle(surf, darker(base, 40), (r.left + 2*r.width//3, cy), 2, 1)

# ---------------------------- Text → Tile Field ---------------------------- #

def text_to_tiles(text: str, cell: int = None, palette_keys=("red","yellow","green","blue")) -> List[Tile]:
    """Rasterize text to a coarse grid of LEGO tiles.
    - We render text to a mask surface, then sample a grid; if the cell touches text,
      we place a tile there.
    - cell (tile size) defaults to STUD_UNIT for consistency with gameplay.
    """
    if cell is None:
        cell = STUD_UNIT
    # render text large and centered on a mask
    font = pg.font.SysFont("couriernew", 24, bold=True)
    txt_img = font.render(text, True, (255, 255, 255))
    # compute origin for centering
    ox = (GAME_W - txt_img.get_width()) // 2
    oy = (GAME_H - txt_img.get_height()) // 2
    # stamp to a temporary surface for pixel checks
    mask = pg.Surface((GAME_W, GAME_H), pg.SRCALPHA)
    mask.blit(txt_img, (ox, oy))

    colors = [COLORS[k] for k in palette_keys]
    tiles: List[Tile] = []
    rng = random.Random(1337)
    for gy in range(0, GAME_H, cell):
        for gx in range(0, GAME_W, cell):
            # sample a few points in the cell to decide if we keep it
            count = 0
            for sx in (0, cell//2, cell-1):
                for sy in (0, cell//2, cell-1):
                    x = min(GAME_W-1, gx + sx)
                    y = min(GAME_H-1, gy + sy)
                    if mask.get_at((x, y)).a > 0:  # non-empty pixel
                        count += 1
            if count >= 2:  # occupied
                tiles.append(Tile(gx, gy, cell, int(cell*0.9), rng.choice(colors)))
    return tiles

# ---------------------------- CRUMBLE Animation ---------------------------- #

def run_crumble_reveal(screen: pg.Surface, low: pg.Surface, reveal_text: str, timeout: float = 6.0):
    """Cover screen with a grid of tiles, then drop them away to reveal text."""
    clock = pg.time.Clock()
    # Prepare full wall of tiles
    tiles: List[Tile] = []
    colors = [COLORS[k] for k in ("red","yellow","green","blue")]
    rng = random.Random()
    for gy in range(0, GAME_H, STUD_UNIT):
        for gx in range(0, GAME_W, STUD_UNIT):
            t = Tile(gx, gy, STUD_UNIT, int(STUD_UNIT*0.9), rng.choice(colors))
            # assign random drop delay and velocity
            t.life = rng.uniform(0.2, 1.2)  # delay before it starts falling
            t.vx = rng.uniform(-20, 20)
            t.vy = 0
            tiles.append(t)

    # Reveal text (drawn on background)
    font = pg.font.SysFont("couriernew", 26, bold=True)
    text_img = font.render(reveal_text, True, (250, 250, 250))
    tx = (GAME_W - text_img.get_width()) // 2
    ty = (GAME_H - text_img.get_height()) // 2

    elapsed = 0.0
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        elapsed += dt
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
            if e.type == pg.KEYDOWN:
                return

        # Physics update
        all_gone = True
        for t in tiles:
            if t.life > 0:
                t.life -= dt
            else:
                t.vy += 200 * dt  # gravity
                t.x += t.vx * dt
                t.y += t.vy * dt
            if t.y < GAME_H + 10:  # at least one tile still visible
                all_gone = False

        # Draw
        low.fill(COLORS["bg"])
        # draw revealed text below
        low.blit(text_img, (tx, ty))
        # draw remaining tiles on top
        for t in tiles:
            if -STUD_UNIT < t.x < GAME_W+STUD_UNIT and -STUD_UNIT < t.y < GAME_H+STUD_UNIT:
                draw_tile_brick(low, t)
        # helper label
        draw_pixel_text(low, "Press any key...", GAME_W//2 - 50, GAME_H - 16, COLORS["hud_dim"])

        up = pg.transform.scale(low, (GAME_W*SCALE, GAME_H*SCALE))
        screen.blit(up, (0, 0))
        pg.display.flip()

        if all_gone or elapsed > timeout:
            return

# ---------------------------- BUILD Animation ---------------------------- #

def run_build_text(screen: pg.Surface, low: pg.Surface, build_text: str, timeout: float = 6.0):
    """Bricks appear one-by-one on the grid to build the target text."""
    clock = pg.time.Clock()
    target_tiles = text_to_tiles(build_text)
    # randomized order so it looks like someone placing tiles quickly
    rng = random.Random()
    order = list(range(len(target_tiles)))
    rng.shuffle(order)

    placed: List[Tile] = []
    batch = max(1, len(target_tiles)//40)  # how many tiles to place per step
    timer = 0.0
    delay = 0.04
    elapsed = 0.0

    while True:
        dt = clock.tick(FPS) / 1000.0
        elapsed += dt
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
            if e.type == pg.KEYDOWN:
                return

        timer += dt
        if timer >= delay and order:
            timer = 0.0
            for _ in range(min(batch, len(order))):
                idx = order.pop()
                t = target_tiles[idx]
                # small drop-in tween: start above and fall into place
                t_start_y = t.y - 10
                t_current = Tile(t.x, t_start_y, t.w, t.h, t.color, vx=0, vy=120)
                placed.append(t_current)

        # update falling tiles
        for t in placed:
            if t.y < target_tiles[0].y or t.vy > 0:
                t.y += t.vy * dt
                t.vy -= 240 * dt  # ease-out to settle
                if t.y >= round(t.y / 1):
                    t.vy = 0

        # snap any near their final row
        for t in placed:
            if abs((t.y) - round(t.y/1)) < 0.5:
                t.y = round(t.y/1)

        # draw
        low.fill(COLORS["bg"])
        for t in placed:
            draw_tile_brick(low, t)
        draw_pixel_text(low, "Press any key...", GAME_W//2 - 50, GAME_H - 16, COLORS["hud_dim"])

        up = pg.transform.scale(low, (GAME_W*SCALE, GAME_H*SCALE))
        screen.blit(up, (0, 0))
        pg.display.flip()

        if not order and elapsed > timeout:
            return

# ---------------------------- Orchestrator ---------------------------- #

def run_end_screen(role: str, won: bool) -> None:
    """Run the appropriate animation based on role/outcome.
    role: "breaker" or "placer". won: True/False
    """
    pg.init()
    pg.display.set_caption("LEGO Brick Break — Result")
    screen = pg.display.set_mode((GAME_W * SCALE, GAME_H * SCALE))
    low = pg.Surface((GAME_W, GAME_H))

    role = role.lower().strip()
    if role not in {"breaker", "placer"}:
        role = "breaker"

    if role == "breaker" and won:
        run_crumble_reveal(screen, low, "YOU WIN")
    elif role == "breaker" and not won:
        run_build_text(screen, low, "YOU LOSE")
    elif role == "placer" and won:
        run_build_text(screen, low, "YOU WIN")
    else:  # placer loses
        run_crumble_reveal(screen, low, "YOU LOSE")

    pg.quit()