# Global Variables
GAP = 8
INFO_H = 72
FPS = 60
ANIM_FRAMES = 20  # frames spent sliding the tile  (~333 ms at 60 fps)
HOLD_FRAMES = 6  # frames the settled state is shown before the next move

# imports
import pygame
import sys
import colorsys
from typing import Optional

def _tile_size(n: int) -> int:
    # Compute a tile pixel size that keeps the board around 460 px wide.
    board_target = 460
    return (board_target - (n + 1) * GAP) // n


"""
Map tile value v (1..total) to an RGB color via HSV.
The hue starts at blue-violet and shifts through the full spectrum.
"""


def tile_color(v: int, total: int) -> tuple[int, int, int]:
    hue = (0.62 + (v - 1) / max(total, 1) * 0.82) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.68, 0.90)
    return int(r * 255), int(g * 255), int(b * 255)


"""
Render a single tile at pixel position (x, y) with:
  • a dark drop-shadow offset by (3, 5)
  • a filled rounded rectangle in the tile's HSV color
  • a lighter highlight strip across the top edge
  • a centered white number label
"""


def draw_tile(screen: pygame.Surface, v: int, x: int, y: int, tile: int, font: pygame.font.Font, total: int, ) -> None:
    color = tile_color(v, total)
    # Drop shadow
    pygame.draw.rect(screen, (6, 6, 12), (x + 3, y + 5, tile, tile), border_radius=12)
    # Fill
    pygame.draw.rect(screen, color, (x, y, tile, tile), border_radius=12)
    # Top highlight strip
    hi = tuple(min(255, c + 50) for c in color)
    pygame.draw.rect(screen, hi, (x + 8, y + 6, tile - 16, 5), border_radius=3)
    # Number
    label = font.render(str(v), True, (248, 248, 255))
    screen.blit(label, (x + (tile - label.get_width()) // 2, y + (tile - label.get_height()) // 2,))


def find_move(state_a: tuple[int, ...], state_b: tuple[int, ...], ) -> tuple[int, int, int]:
    blank_a = state_a.index(0)
    blank_b = state_b.index(0)
    return state_a[blank_b], blank_b, blank_a


"""
Render one display frame.

Draws every tile at its position in `state`, except the tile identified
by `moving`, which is instead rendered at its smoothstep-interpolated
position between from_flat and to_flat.

Parameters:
    moving  -- (tile_value, from_flat, to_flat, progress∈[0,1]) or None
    solved  -- if True the info bar shows the "Solved!" message
"""


def draw_frame(screen: pygame.Surface, state: tuple[int, ...], n: int, tile: int, font: pygame.font.Font,
               info_font: pygame.font.Font, step: int,
               total_steps: int, moving: Optional[tuple[int, int, int, float]] = None, solved: bool = False, ) -> None:
    board_px = n * tile + (n + 1) * GAP
    total = n * n - 1
    screen.fill((14, 14, 22))

    for i in range(n * n):
        r, c = i // n, i % n
        x = GAP + c * (tile + GAP)
        y = GAP + r * (tile + GAP)
        pygame.draw.rect(screen, (28, 28, 44), (x, y, tile, tile), border_radius=12)

    # ── Static tiles ──────────────────────────────────────────────────────
    skip_v = moving[0] if moving else None
    for idx, v in enumerate(state):
        if v == 0 or v == skip_v:
            continue

        r, c = idx // n, idx % n
        draw_tile(screen, v,
                  GAP + c * (tile + GAP),
                  GAP + r * (tile + GAP),
                  tile, font, total)

    # ── Animated tile ─────────────────────────────────────────────────────
    if moving:
        mv, from_i, to_i, progress = moving
        fr, fc = from_i // n, from_i % n
        tr, tc = to_i // n, to_i % n
        fx = GAP + fc * (tile + GAP)
        fy = GAP + fr * (tile + GAP)
        tx = GAP + tc * (tile + GAP)
        ty = GAP + tr * (tile + GAP)
        # Smoothstep: ease in and out
        p = progress * progress * (3.0 - 2.0 * progress)
        cx = int(fx + (tx - fx) * p)
        cy = int(fy + (ty - fy) * p)
        draw_tile(screen, mv, cx, cy, tile, font, total)

    # ── Info bar ──────────────────────────────────────────────────────────
    bar_y = board_px
    pygame.draw.rect(screen, (20, 20, 32), (0, bar_y, board_px, INFO_H))

    if solved:
        msg = f"Solved in {total_steps} move{'s' if total_steps != 1 else ''}!"
        color = (85, 255, 145)

    else:
        msg = f"Move  {step}  /  {total_steps}"
        color = (160, 160, 210)

    txt = info_font.render(msg, True, color)
    screen.blit(txt, (board_px // 2 - txt.get_width() // 2, bar_y + INFO_H // 2 - txt.get_height() // 2,))


"""
Animate the solution path in a pygame window.

Each move is triggered as we "pop" the next state from the solution list.
The animation runs at FPS fps with ANIM_FRAMES frames of sliding
motion followed by HOLD_FRAMES frames of the settled board.

Controls:
    SPACE / ENTER  -- skip the intro pause and start immediately
    ESC / close    -- quit
"""


def visualize(path: list[tuple[int, ...]], n: int) -> None:
    tile = _tile_size(n)
    board_px = n * tile + (n + 1) * GAP
    total = len(path) - 1

    pygame.init()
    pygame.display.set_caption(f"{n * n - 1}-Puzzle  ·  A*")
    screen = pygame.display.set_mode((board_px, board_px + INFO_H))
    clock = pygame.time.Clock()

    font_sz = max(24, tile // 2 + 2)
    font = pygame.font.SysFont("monospace", font_sz, bold=True)
    info_font = pygame.font.SysFont("monospace", 24, bold=True)

    phase = "solved" if total == 0 else "intro"
    step = 0
    frame = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if phase == "intro":
                        phase = "animating"
                        frame = 0

                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        if phase == "intro":
            # ~1 second intro
            if frame >= FPS:
                phase = "animating"
                frame = 0

        elif phase == "animating":
            if frame >= ANIM_FRAMES:
                phase = "holding"
                frame = 0

        elif phase == "holding":
            if frame >= HOLD_FRAMES:
                step += 1
                if step >= total:
                    phase = "solved"

                else:
                    phase = "animating"

                frame = 0

        if phase in ("intro", "solved"):
            draw_frame(screen, path[step], n, tile, font, info_font, step, total, solved=(phase == "solved"))

        elif phase == "animating":
            state_a = path[step]
            state_b = path[step + 1]
            mv, from_i, to_i = find_move(state_a, state_b)
            progress = frame / ANIM_FRAMES
            draw_frame(screen, state_a, n, tile, font, info_font, step, total, moving=(mv, from_i, to_i, progress))

        elif phase == "holding":
            draw_frame(screen, path[step + 1], n, tile, font, info_font, step + 1, total)

        frame += 1
        pygame.display.flip()
        clock.tick(FPS)
