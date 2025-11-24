from __future__ import annotations
pg.draw.circle(surf, darker(base, 40), (r.left + r.width//3, cy), 2, 1)
pg.draw.circle(surf, lighter(base, 10), (r.left + 2*r.width//3, cy), 2)
pg.draw.circle(surf, darker(base, 40), (r.left + 2*r.width//3, cy), 2, 1)




def run_crumble_reveal(screen: pg.Surface, low: pg.Surface, reveal_text: str, timeout: float = 6.0):
"""Cover with a LEGO wall, then let bricks fall away to reveal text underneath."""
clock = pg.time.Clock()
# Prepare full wall of tiles
tiles: List[_Tile] = []
colors = [COLORS[k] for k in ("red","yellow","green","blue")]
rng = random.Random()
for gy in range(0, GAME_H, STUD_UNIT):
for gx in range(0, GAME_W, STUD_UNIT):
t = _Tile(gx, gy, STUD_UNIT, int(STUD_UNIT*0.9), rng.choice(colors))
t.life = rng.uniform(0.2, 1.2) # start delay
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
low.blit(text_img, (tx, ty)) # revealed underlayer
for t in tiles:
if -STUD_UNIT < t.x < GAME_W+STUD_UNIT and -STUD_UNIT < t.y < GAME_H+STUD_UNIT:
_draw_tile_brick(low, t)
draw_pixel_text(low, "Press any key...", GAME_W//2 - 50, GAME_H - 16, COLORS["hud_dim"])


up = pg.transform.scale(low, (GAME_W*SCALE, GAME_H*SCALE))
screen.blit(up, (0, 0))
pg.display.flip()


if all_gone or elapsed > timeout:
return


# ------------------------------ Orchestrator ----------------------------- #


def run_end_screen(role: str, won: bool) -> None:
"""Show end screen with CRUMBLE where specified, static LEGO title otherwise."""
pg.init()
pg.display.set_caption("LEGO Brick Break — Result")
screen = pg.display.set_mode((GAME_W * SCALE, GAME_H * SCALE))
low = pg.Surface((GAME_W, GAME_H))


role = (role or "").lower().strip()
if role not in {"breaker", "placer"}:
role = "breaker"


# Map outcomes
if (role == "breaker" and won) or (role == "placer" and not won):
# CRUMBLE cases
run_crumble_reveal(screen, low, "YOU WIN" if won else "YOU LOSE")
else:
# STATIC LEGO title cases (no build)
clock = pg.time.Clock()
message = "YOU WIN" if won else "YOU LOSE"
# Pre-render one frame
low.fill(COLORS["bg"])
draw_brick_border(low)
# crude center estimate based on brick tile width
text_px_width = len(message.replace(" ", "")) * 17 + message.count(" ") * 7
start_x = max(8, (GAME_W - text_px_width) // 2)
draw_title_bricks(low, message, x=start_x, y=GAME_H//2 - 10)
draw_pixel_text(low, "Press any key to continue", GAME_W//2 - 80, GAME_H - 16, COLORS["hud_dim"])
up = pg.transform.scale(low, (GAME_W * SCALE, GAME_H * SCALE))
# event loop
while True:
dt = clock.tick(FPS) / 1000.0
for e in pg.event.get():
if e.type == pg.QUIT:
pg.quit(); return
if e.type == pg.KEYDOWN or e.type == pg.MOUSEBUTTONDOWN:
pg.quit(); return
screen.blit(up, (0, 0))
pg.display.flip()


pg.quit()
