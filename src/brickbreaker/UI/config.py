"""Shared configuration for sizes, speeds, and colors used across modules.
- We render to a small GAME_W x GAME_H surface (pixel-art look), then upscale.
- Brick and stud sizes are tuned to read as LEGO at this resolution.
"""

# Low-res render (pixel art) — upscale with NEAREST in your main loop
GAME_W, GAME_H = 320, 180  # internal canvas size
SCALE = 4  # window size = GAME_*SCALE
FPS = 60

# Playfield margins
TOP_MARGIN = 28
SIDE_MARGIN_DEFAULT = 16  # varied per level for tighter/wider arenas

# LEGO sizing (pixels, in the low-res surface)
STUD_UNIT = 12  # width of a single stud cell
BRICK_HEIGHT = 8  # side-view brick height (studs_y doesn't change this)
STUD_RADIUS = 3  # visual radius (some modules set their own local value)

# Paddle
PADDLE_W_STUDS = 5
PADDLE_H = 6
PADDLE_SPEED = 150

# Ball
BALL_SPEED = 110
BALL_RADIUS = 8

# Colors — approximate classic LEGO palette
COLORS = {
    "bg": (18, 18, 24),
    "hud": (240, 240, 240),
    "hud_dim": (170, 170, 180),
    "red": (214, 40, 28),
    "yellow": (255, 213, 0),
    "green": (0, 146, 61),
    "blue": (0, 87, 166),
    "grey": (120, 120, 128),  # unbreakable / obstacle bricks
    "shadow": (0, 0, 0),
    "paddle": (245, 245, 245),  # smooth white tile paddle
}

BRICK_HIT_POINTS = {
    "red": 1,
    "yellow": 2,
    "green": 3,
    "blue": 4,
    "grey": 100,
}

# Palette for breakable bricks
BRICK_PALETTE = ["red", "yellow", "green", "blue"]
