"""
Procedural map/level builder (NO OVERLAP, FLUSH-END BRICKS).
- Rows are packed on a stud grid: bricks touch end-to-end with zero gaps/overlap.
- Patterns: grid, stairs, chevrons, mix (all use the same row packing).
- `map_w_shrink` increases SIDE_MARGIN to narrow the arena for a given level.
"""
from __future__ import annotations
import random
from typing import List, Tuple
from config import (
    GAME_W, GAME_H, TOP_MARGIN, SIDE_MARGIN_DEFAULT, STUD_UNIT,
    BRICK_PALETTE, BRICK_HEIGHT
)
from bricks import Brick

# Allowed brick lengths (in studs). Side-view shows one stud row on top.
ALLOWED_STUD_LENGTHS = [2, 3, 4]   # 1x2, 1x3, 1x4

# Compatibility with older API that referenced studs_y (depth)
SHAPES: List[Tuple[int, int]] = [(1, s) for s in ALLOWED_STUD_LENGTHS] + [(2, 2)]

def _row_pack(play_left: int, play_right: int, y: int,
              rng: random.Random, left_to_right: bool, pattern: str) -> list[Brick]:
    """
    Pack a single row with flush bricks on the stud grid (no gaps/overlap).
    Fills until fewer than 2 studs remain (smallest piece is 1x2).
    """
    bricks: list[Brick] = []
    width_px = play_right - play_left
    width_studs = width_px // STUD_UNIT

    def add(x_px: int, studs_x: int, color_key: str, unbreakable=False):
        bricks.append(Brick(x=x_px, y=y, studs_x=studs_x, studs_y=1,
                            color_key=color_key, unbreakable=unbreakable))

    consumed = 0
    while width_studs - consumed >= 2:
        remaining = width_studs - consumed
        choices = [s for s in ALLOWED_STUD_LENGTHS if s <= remaining]
        studs_x = rng.choice(choices)
        color_key = rng.choice(BRICK_PALETTE)
        unbreakable = (rng.random() < (0.12 if pattern in ("stairs", "chevrons", "mix") else 0.06))
        if unbreakable:
            color_key = "grey"

        if left_to_right:
            x_px = play_left + consumed * STUD_UNIT
        else:
            x_px = play_right - (consumed + studs_x) * STUD_UNIT

        add(x_px, studs_x, color_key, unbreakable)
        consumed += studs_x

    return bricks

def build_level(map_w_shrink: int, pattern: str, rng: random.Random) -> tuple[list[Brick], int]:
    """
    Build a single level layout; returns (bricks, side_margin).
    """
    bricks: list[Brick] = []
    side_margin = SIDE_MARGIN_DEFAULT + map_w_shrink

    # Align playfield to the stud grid so rows pack cleanly
    play_left = side_margin - (side_margin % STUD_UNIT)
    play_right = GAME_W - side_margin + (side_margin % STUD_UNIT)

    rows = 6
    y0 = TOP_MARGIN + 8
    row_gap = 4  # vertical spacing between rows

    for row in range(rows):
        y = y0 + row * (BRICK_HEIGHT + row_gap)
        if pattern == "grid":
            bricks += _row_pack(play_left, play_right, y, rng, True, pattern)
        elif pattern == "stairs":
            # stairs flavor by using an independent RNG (still packed, no overlap)
            rng_bias = random.Random(rng.randint(0, 99999))
            bricks += _row_pack(play_left, play_right, y, rng_bias, True, pattern)
        elif pattern == "chevrons":
            left_to_right = (row % 2 == 0)
            bricks += _row_pack(play_left, play_right, y, rng, left_to_right, pattern)
        elif pattern == "mix":
            left_to_right = rng.choice([True, False])
            bricks += _row_pack(play_left, play_right, y, rng, left_to_right, pattern)
        else:
            raise ValueError(f"Unknown pattern: {pattern}")

    return bricks, side_margin

def build_levels(seed: int = 1337) -> list[dict]:
    """
    Create a small playlist of levels with varying patterns and widths.
    Returns: [{"bricks": list[Brick], "side_margin": int, "pattern": str}, ...]
    """
    rng = random.Random(seed)
    patterns = ["grid", "stairs", "chevrons", "mix"]
    levels: list[dict] = []
    for _ in range(5):
        shrink = rng.randint(0, 20)
        pattern = rng.choice(patterns)
        bricks, side_margin = build_level(shrink, pattern, rng)
        levels.append({
            "bricks": bricks,
            "side_margin": side_margin,
            "pattern": pattern,
        })
    return levels
