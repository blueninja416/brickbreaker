"""menu.py — LEGO Brick Break (PyGame) main menu

Features
- Two options: Host a game as Breaker, Join a game as Placer
- Host flow: shows your local IP + chosen port to share with the opponent
- Join flow: enter host IP and port (basic input UI)
- LEGO-themed visuals: colorful title made of "brick tiles", studded buttons, brick border
- Pixel-art pipeline consistent with config.py (low-res surface upscaled by NEAREST)

Public API
- run_menu() -> dict | None
    Returns a selection dict, e.g.:
      {"mode":"host", "host_ip":"192.168.1.10", "port": 7777}
      {"mode":"join", "join_ip":"192.168.1.10", "port": 7777}
    Returns None if the user quits.

Notes:
- This file does not implement networking; it only collects the choice and params.
- Requires config.py, graphics.py to be present in the same package.
"""

from __future__ import annotations

import socket

import pygame as pg

from brickbreaker.UI.config import COLORS, FPS, GAME_H, GAME_W, SCALE, STUD_UNIT
from brickbreaker.UI.graphics import darker, draw_pixel_text, lighter
from brickbreaker.net.transport import DEFAULT_PORT

# ------------------------------ UI Helpers ------------------------------ #


class BrickButton:
    """A LEGO-brick styled button with studs along the top edge.
    - Drawn entirely with vector shapes.
    - Call .handle_event(event) to update hover/active, .clicked to check clicks.
    """

    def __init__(self, rect: pg.Rect, label: str, color_key: str):
        self.rect = rect
        self.label = label
        self.base_color = COLORS[color_key]
        self.hover = False
        self.clicked = False

    def _draw_studs(self, surf: pg.Surface):
        r = self.rect
        studs = max(1, r.width // STUD_UNIT)
        top_y = r.top + 1
        for i in range(studs):
            cx = r.left + STUD_UNIT // 2 + i * STUD_UNIT
            pg.draw.circle(surf, lighter(self.base_color, 10), (cx, top_y), 3)
            pg.draw.circle(surf, darker(self.base_color, 40), (cx, top_y), 3, 1)
            pg.draw.line(surf, lighter(self.base_color, 15), (cx - 3, top_y), (cx + 3, top_y))

    def draw(self, surf: pg.Surface):
        r = self.rect
        body = lighter(self.base_color, 20) if self.hover else self.base_color
        # Brick body
        pg.draw.rect(surf, body, r, border_radius=3)
        pg.draw.line(surf, lighter(body, 25), (r.left, r.top), (r.right - 1, r.top))
        pg.draw.line(surf, darker(body, 35), (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
        self._draw_studs(surf)
        # Label centered
        font = pg.font.SysFont("couriernew", 12, bold=True)
        label_img = font.render(self.label, True, (250, 250, 250))
        surf.blit(label_img, label_img.get_rect(center=r.center))

    def handle_event(self, e: pg.event.Event):
        if e.type == pg.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
            self.clicked = self.rect.collidepoint(e.pos)
        elif e.type == pg.MOUSEBUTTONUP and e.button == 1:
            # detect click on release inside button
            self.clicked = self.rect.collidepoint(e.pos) and self.hover


class InputBox:
    """Minimal text input (for IP/port). Set numeric_only=True for port input."""

    def __init__(self, rect: pg.Rect, placeholder: str = "", numeric_only: bool = False):
        self.rect = rect
        self.text = ""
        self.placeholder = placeholder
        self.numeric_only = numeric_only
        self.active = False

    def handle_event(self, e: pg.event.Event):
        if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
            self.active = self.rect.collidepoint(e.pos)
        elif e.type == pg.KEYDOWN and self.active:
            if e.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
            elif e.key == pg.K_RETURN:
                # ignore here; consuming code will read .text
                pass
            else:
                ch = e.unicode
                if self.numeric_only and not ch.isdigit():
                    return
                if len(ch) == 1 and (32 <= ord(ch) < 127):
                    self.text += ch

    def value(self) -> str:
        return self.text.strip()

    def draw(self, surf: pg.Surface):
        base = COLORS["grey"] if self.active else (100, 100, 110)
        pg.draw.rect(surf, base, self.rect, border_radius=2)
        pg.draw.rect(surf, (40, 40, 50), self.rect, 1, border_radius=2)
        font = pg.font.SysFont("couriernew", 12)
        content = self.text if self.text else self.placeholder
        color = (250, 250, 250) if self.text else (200, 200, 210)
        txt = font.render(content, True, color)
        surf.blit(txt, (self.rect.x + 6, self.rect.y + 3))


# ------------------------------ Visual Theme ---------------------------- #


def draw_brick_border(surf: pg.Surface):
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
            # studs
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


def draw_title_bricks(surf: pg.Surface, text: str, x: int, y: int):
    """Render a colorful LEGO-style title: each character sits on a colored brick tile
    with a couple of studs on top. Not a perfect font—simple but readable.
    """
    colors = [COLORS[c] for c in ("red", "yellow", "green", "blue")]
    font = pg.font.SysFont("couriernew", 14, bold=True)
    gap = 2
    brick_h = 14
    brick_w = 12
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


# ------------------------------ Networking utils ------------------------ #


def get_local_ip() -> str:
    """Best-effort local IP discovery (no external calls)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # we don't send; just lets OS pick an outgoing iface
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ------------------------------ Menu Logic ------------------------------ #


def run_menu() -> dict | None:
    if not pg.get_init():
        pg.init()
    pg.display.set_caption("LEGO Brick Break — Menu")
    screen = pg.display.set_mode((GAME_W * SCALE, GAME_H * SCALE))
    clock = pg.time.Clock()
    low = pg.Surface((GAME_W, GAME_H))

    # Buttons
    btn_w = 180
    btn_h = 22
    host_btn = BrickButton(
        pg.Rect(GAME_W // 2 - btn_w // 2, 80, btn_w, btn_h), "Host game as Breaker", "green"
    )
    join_btn = BrickButton(
        pg.Rect(GAME_W // 2 - btn_w // 2, 110, btn_w, btn_h), "Join game as Placer", "blue"
    )

    # Join inputs (only IP; port is fixed to DEFAULT_PORT)
    ip_box = InputBox(pg.Rect(GAME_W // 2 - 90, 140, 120, 18), placeholder="Host IP")

    # Host info
    default_port = DEFAULT_PORT
    host_ip = get_local_ip()
    port_value = str(DEFAULT_PORT)

    stage = "menu"  # "menu" | "host" | "join"
    auto_host = False  # when True, auto-confirm host selection after drawing

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        mouse_pos_scaled = None

        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                return None
            if e.type in (pg.MOUSEMOTION, pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP):
                # Convert window mouse pos to low-res coordinates
                mx, my = pg.mouse.get_pos()
                mouse_pos_scaled = (mx // SCALE, my // SCALE)
                # Temporarily override event pos so buttons get correct hit tests
                if hasattr(e, "pos"):
                    e.pos = mouse_pos_scaled

            if stage == "menu":
                host_btn.handle_event(e)
                join_btn.handle_event(e)
                if e.type == pg.MOUSEBUTTONUP and e.button == 1:
                    if host_btn.clicked:
                        stage = "host"
                        auto_host = True
                    elif join_btn.clicked:
                        stage = "join"

            if stage == "join":
                ip_box.handle_event(e)
                if e.type == pg.KEYDOWN and e.key == pg.K_RETURN:
                    ip = ip_box.value()
                    if ip:
                        return {"mode": "join", "join_ip": ip, "port": default_port}
                if e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                    stage = "menu"

            elif stage == "host":
                if e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                    # Cancel hosting and go back to main menu
                    stage = "menu"
                    auto_host = False

        # ------------------- Draw low-res frame ------------------- #
        low.fill(COLORS["bg"])
        draw_brick_border(low)
        draw_title_bricks(low, "LEGO BRICK BREAK", x=22, y=18)

        if stage == "menu":
            host_btn.draw(low)
            join_btn.draw(low)
            draw_pixel_text(low, "Choose an option", GAME_W // 2 - 56, 60, COLORS["hud_dim"])

        elif stage == "join":
            draw_pixel_text(low, "Join as Placer", GAME_W // 2 - 52, 60, COLORS["hud"])
            draw_pixel_text(
                low, f"Enter host IP, then press Enter. Press ESC to return to main menu.", 8, 72, COLORS["hud_dim"]
            )
            ip_box.draw(low)

        elif stage == "host":
            draw_pixel_text(low, "Host as Breaker", GAME_W // 2 - 54, 60, COLORS["hud"])
            draw_pixel_text(low, "Share this IP/Port with your opponent", 24, 72, COLORS["hud_dim"])
            draw_pixel_text(low, f"Your IP: {host_ip}", 30, 96, (240, 240, 240))
            draw_pixel_text(low, f"Port: {default_port}", 30, 110, (240, 240, 240))
            draw_pixel_text(
                low, "Waiting for player 2, or press ESC to go back", 24, 134, COLORS["hud_dim"]
            )

        # Upscale to the real window
        up = pg.transform.scale(low, (GAME_W * SCALE, GAME_H * SCALE))
        screen.blit(up, (0, 0))
        pg.display.flip()

        # If the user chose "Host" we show the info screen for a frame, then
        # immediately return to let the main program open the socket.
        if stage == "host" and auto_host:
            return {"mode": "host", "host_ip": host_ip, "port": default_port}
