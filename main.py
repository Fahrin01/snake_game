"""
Snake Game
==========
A complete, polished classic Snake Game built with Python's standard
library (Tkinter only - no external dependencies, no internet required).

Run with:
    python main.py
"""

import tkinter as tk
import bisect
import json
import math
import os
import random
import time

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

WINDOW_TITLE = "Snake Game"

BOARD_SIZE = 600                       # Width/height of the square board (px)
CELL_SIZE = 20                         # Size of each grid cell (px)
GRID_COUNT = BOARD_SIZE // CELL_SIZE   # Number of cells per row/column

SCORE_PER_FOOD = 10
BIG_FOOD_SCORE = 30                    # points awarded by the special big ball
BIG_FOOD_EVERY = 5                     # a big ball appears after this many small balls
SPEED_INCREASE_STEP = 2                # ms shaved off the delay per food eaten
MIN_DELAY = 40                         # fastest possible delay (ms) - speed cap

FRAME_MS = 16                          # render interval (~60 fps) for smooth motion

HIGHSCORE_FILE = "highscore.json"

DIFFICULTY_SPEEDS = {
    "Easy": 150,
    "Medium": 100,
    "Hard": 70,
}

MIN_WINDOW_WIDTH = 660
MIN_WINDOW_HEIGHT = 780

# ---- Color theme (deep, modern dark) ----
COLOR_BG = "#0f1117"
COLOR_PANEL = "#171a24"
COLOR_CARD_BORDER = "#2a3042"
COLOR_TILE_A = "#5e9a38"               # average grass colour (used for food glow)
GRASS_DARK = (46, 92, 30)              # shaded / dense grass
GRASS_LIGHT = (112, 158, 58)           # sunlit / dry grass
COLOR_BOARD_BORDER = "#5b3a1e"         # soil-brown edge around the field
COLOR_SHADOW = "#2f5a1d"               # shadows cast onto the grass

COLOR_TEXT = "#eef1f7"
COLOR_SUBTEXT = "#8b93a7"
COLOR_ACCENT = "#3ddc84"
COLOR_ACCENT_HOVER = "#62efa0"
COLOR_ACCENT_TEXT = "#08180e"
COLOR_BUTTON_BG = "#1f2433"
COLOR_BUTTON_HOVER = "#2b3247"
COLOR_DANGER = "#ff5c6c"
COLOR_GOLD = "#ffc94d"
COLOR_OVERLAY_BG = "#000000"

# ---- Snake (maroon python - warm dark red stands out against grass) ----
SNAKE_OUTLINE = "#2a0609"
SNAKE_BASE = "#7d1d2a"
SNAKE_HEAD_BASE = "#8e2533"
SNAKE_HIGHLIGHT = "#d88a94"
SNAKE_PATTERN = "#3e0a12"
SNAKE_PATTERN_RIM = "#f5c542"
SNAKE_EYE = "#ffb02e"
SNAKE_PUPIL = "#0a0a0a"
SNAKE_TONGUE = "#e0344a"

# ---- Food ----
APPLE_RED = ("#e53935", "#ff9a8f", "#8e1b1b")      # base, light, dark
APPLE_GOLD = ("#ffc107", "#fff4c2", "#a86f00")
APPLE_STEM = "#6d4c41"
APPLE_LEAF = "#4caf50"

FONT_TITLE = ("Segoe UI Black", 58)
FONT_SUBTITLE = ("Segoe UI", 12)
FONT_HEADING = ("Segoe UI Semibold", 24)
FONT_BODY = ("Segoe UI", 12)
FONT_BUTTON = ("Segoe UI Semibold", 12)
FONT_SMALL_BUTTON = ("Segoe UI Semibold", 10)
FONT_CAPTION = ("Segoe UI Semibold", 8)
FONT_STAT = ("Segoe UI Semibold", 16)
FONT_BIG_STAT = ("Segoe UI Semibold", 28)


# ----------------------------------------------------------------------
# Small geometry / color helpers
# ----------------------------------------------------------------------
def blend(c1, c2, t):
    """Mixes two #rrggbb colors; t=0 gives c1, t=1 gives c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def lerp_pt(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def to_world(local_pts, cx, cy, ux, uy, scale=1.0):
    """Converts points in a local frame (x = forward, y = sideways) into
    flat canvas coordinates, rotated so 'forward' points along (ux, uy)."""
    out = []
    for x, y in local_pts:
        x *= scale
        y *= scale
        out.append(cx + x * ux - y * uy)
        out.append(cy + x * uy + y * ux)
    return out


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def round_corners(pts, radius, steps=5):
    """Replaces every sharp bend in a polyline with a short curve, so the
    snake bends organically instead of making hard 90-degree turns."""
    if len(pts) < 3:
        return list(pts)
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        l1 = math.hypot(b[0] - a[0], b[1] - a[1])
        l2 = math.hypot(c[0] - b[0], c[1] - b[1])
        if l1 < 1e-6 or l2 < 1e-6:
            continue
        u1 = ((b[0] - a[0]) / l1, (b[1] - a[1]) / l1)
        u2 = ((c[0] - b[0]) / l2, (c[1] - b[1]) / l2)
        if abs(u1[0] * u2[1] - u1[1] * u2[0]) < 1e-6:
            out.append(b)          # straight - nothing to round
            continue
        r = min(radius, l1 / 2, l2 / 2)
        p0 = (b[0] - u1[0] * r, b[1] - u1[1] * r)
        p2 = (b[0] + u2[0] * r, b[1] + u2[1] * r)
        for k in range(steps + 1):
            t = k / steps
            out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * b[0] + t * t * p2[0],
                        (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * b[1] + t * t * p2[1]))
    out.append(pts[-1])
    return out


class PathWalker:
    """Lets us walk along a polyline by distance (used to taper the tail
    and place body markings at even spacing)."""

    def __init__(self, pts):
        clean = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - clean[-1][0]) + abs(p[1] - clean[-1][1]) > 1e-6:
                clean.append(p)
        self.pts = clean
        self.cum = [0.0]
        for a, b in zip(clean, clean[1:]):
            self.cum.append(self.cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.total = self.cum[-1]

    def at(self, s):
        """Returns (point, unit tangent pointing toward the tail) at distance s."""
        if len(self.pts) < 2:
            return self.pts[0], (-1.0, 0.0)
        s = max(0.0, min(self.total, s))
        i = min(bisect.bisect_right(self.cum, s) - 1, len(self.pts) - 2)
        a, b = self.pts[i], self.pts[i + 1]
        seg = self.cum[i + 1] - self.cum[i]
        f = (s - self.cum[i]) / seg
        return lerp_pt(a, b, f), ((b[0] - a[0]) / seg, (b[1] - a[1]) / seg)

    def slice(self, s0, s1):
        out = [self.at(s0)[0]]
        out += [p for p, c in zip(self.pts, self.cum) if s0 < c < s1]
        out.append(self.at(s1)[0])
        return out


# ----------------------------------------------------------------------
# Snake & food renderers (shared by the game board and the menu demo)
# ----------------------------------------------------------------------
HEAD_SHAPE = [(-0.45, 0.0), (-0.38, 0.30), (-0.05, 0.47), (0.35, 0.37), (0.60, 0.17),
              (0.68, 0.0), (0.60, -0.17), (0.35, -0.37), (-0.05, -0.47), (-0.38, -0.30)]
HEAD_MARK = [(-0.34, 0.20), (0.20, 0.0), (-0.34, -0.20), (-0.18, 0.0)]
DIAMOND = [(0.5, 0.0), (0.0, 0.36), (-0.5, 0.0), (0.0, -0.36)]
PUPIL = [(2.6, 0.0), (0.0, 0.75), (-2.6, 0.0), (0.0, -0.75)]


def draw_snake(canvas, pts, now, tag, cell=CELL_SIZE):
    """Draws a smooth, tapered, patterned snake along pixel points `pts`
    (head first). Layers: shadow, dark outline, body, markings, gloss,
    then tongue and head on top."""
    walker = PathWalker(round_corners(pts, cell * 0.5))
    hx, hy = walker.pts[0]
    total = walker.total
    W = cell * 0.72          # body thickness
    L = cell                 # head scale

    # Direction the head faces (smoothed over the first few pixels)
    ux, uy = 1.0, 0.0
    if total > 0.5:
        back, _ = walker.at(min(8.0, total))
        n = math.hypot(hx - back[0], hy - back[1])
        if n > 1e-6:
            ux, uy = (hx - back[0]) / n, (hy - back[1]) / n

    taper_len = min(total * 0.65, cell * 4.5)
    body_end = total - taper_len

    def factor(s):
        if s <= body_end or taper_len <= 0:
            return 1.0
        u = (s - body_end) / taper_len
        return 1.0 - 0.8 * u ** 1.3

    # The tapering tail is one smooth polygon per layer (sampled edge points
    # on both sides of the centerline) - far cheaper than many small lines.
    # Corners inside the tail get a proper mitred normal so the outline
    # bends cleanly instead of folding over itself.
    tail_samples = []
    if taper_len > 0.5:
        n_tail = max(4, int(taper_len / 4))
        corners = {i: c for i, c in enumerate(walker.cum)
                   if body_end < c < total and 0 < i < len(walker.pts) - 1}
        stops = [(body_end + taper_len * k / n_tail, None) for k in range(n_tail + 1)]
        stops = [(s, None) for s, _ in stops
                 if all(abs(s - c) > 0.5 for c in corners.values())]
        stops += [(c, i) for i, c in corners.items()]
        stops.sort()
        for s, vi in stops:
            if vi is None:
                p, (tx, ty) = walker.at(s)
                normal = (-ty, tx)
            else:
                p = walker.pts[vi]
                (ax, ay), (bx, by), (cx, cy) = walker.pts[vi - 1], p, walker.pts[vi + 1]
                l1 = math.hypot(bx - ax, by - ay)
                l2 = math.hypot(cx - bx, cy - by)
                n1 = (-(by - ay) / l1, (bx - ax) / l1)
                n2 = (-(cy - by) / l2, (cx - bx) / l2)
                mx, my = n1[0] + n2[0], n1[1] + n2[1]
                ml = math.hypot(mx, my)
                if ml < 1e-6:
                    normal = n1
                else:
                    mx, my = mx / ml, my / ml
                    miter = 1.0 / max(0.4, mx * n1[0] + my * n1[1])
                    normal = (mx * miter, my * miter)
            tail_samples.append((p, normal, factor(s)))
    body_pts = walker.slice(0.0, body_end) if body_end > 0.5 else None

    def stroke(color, width, dx=0.0, dy=0.0):
        if body_pts and len(body_pts) >= 2:
            flat = []
            for x, y in body_pts:
                flat += (x + dx, y + dy)
            canvas.create_line(*flat, fill=color, width=width, capstyle="round",
                               joinstyle="round", tags=tag)
        if tail_samples:
            left, right = [], []
            for (px, py), (nx, ny), f in tail_samples:
                h = max(0.5, width * f / 2)
                left += (px + nx * h + dx, py + ny * h + dy)
                right.append((px - nx * h + dx, py - ny * h + dy))
            for x, y in reversed(right):
                left += (x, y)
            canvas.create_polygon(left, fill=color, tags=tag)

    # Soft drop shadow
    stroke(COLOR_SHADOW, W, 3, 4)
    canvas.create_polygon(to_world(HEAD_SHAPE, hx + 3, hy + 4, ux, uy, L),
                          fill=COLOR_SHADOW, smooth=True, tags=tag)

    # Body
    stroke(SNAKE_OUTLINE, W)
    stroke(SNAKE_BASE, W * 0.78)

    # Python-style diamond markings along the back. All diamonds are joined
    # into one polygon (linked by zero-area "bridges"), so the cost stays
    # the same no matter how long the snake grows.
    marks = []
    s = cell * 1.25
    while s < total - cell * 0.5:
        (px, py), (tx, ty) = walker.at(s)
        marks.append((px, py, tx, ty, W * factor(s)))
        s += cell * 1.1
    for scale, color in ((1.05, SNAKE_PATTERN_RIM), (0.8, SNAKE_PATTERN)):
        if not marks:
            break
        flat, anchors = [], []
        for px, py, tx, ty, size in marks:
            d = to_world(DIAMOND, px, py, tx, ty, size * scale)
            flat += d + d[:2]
            anchors.append(d[:2])
        for a in reversed(anchors):
            flat += a
        canvas.create_polygon(flat, fill=color, outline="", tags=tag)

    # Glossy highlight (light from top-left)
    stroke(SNAKE_HIGHLIGHT, W * 0.24, -1.5, -2)

    # Flicking forked tongue
    phase = now % 2.2
    if phase < 0.4:
        e = math.sin(math.pi * phase / 0.4)
        start = 0.6 * L
        reach = start + 0.55 * L * e
        fork = 0.22 * L * e
        root = to_world([(start, 0), (reach, 0)], hx, hy, ux, uy)
        canvas.create_line(*root, fill=SNAKE_TONGUE, width=1.6, tags=tag)
        for side in (1, -1):
            tip = to_world([(reach, 0), (reach + fork, side * fork * 0.7)], hx, hy, ux, uy)
            canvas.create_line(*tip, fill=SNAKE_TONGUE, width=1.3, tags=tag)

    # Head
    canvas.create_polygon(to_world(HEAD_SHAPE, hx, hy, ux, uy, L),
                          fill=SNAKE_OUTLINE, smooth=True, tags=tag)
    canvas.create_polygon(to_world(HEAD_SHAPE, hx, hy, ux, uy, L * 0.86),
                          fill=SNAKE_HEAD_BASE, smooth=True, tags=tag)
    canvas.create_polygon(to_world(HEAD_MARK, hx, hy, ux, uy, L),
                          fill=SNAKE_PATTERN, smooth=True, tags=tag)
    canvas.create_polygon(to_world(HEAD_SHAPE, hx - 1.5, hy - 2, ux, uy, L * 0.4),
                          fill=SNAKE_HIGHLIGHT, smooth=True, tags=tag)

    # Nostrils
    for side in (1, -1):
        nx, ny = to_world([(0.55 * L, side * 0.1 * L)], hx, hy, ux, uy)
        canvas.create_oval(nx - 0.9, ny - 0.9, nx + 0.9, ny + 0.9,
                           fill=SNAKE_OUTLINE, outline="", tags=tag)

    # Eyes with vertical slit pupils and a tiny glint
    for side in (1, -1):
        ex, ey = to_world([(0.16 * L, side * 0.31 * L)], hx, hy, ux, uy)
        r = 3.2
        canvas.create_oval(ex - r, ey - r, ex + r, ey + r, fill=SNAKE_EYE,
                           outline=SNAKE_OUTLINE, tags=tag)
        canvas.create_polygon(to_world(PUPIL, ex, ey, ux, uy), fill=SNAKE_PUPIL, tags=tag)
        canvas.create_oval(ex - 1.8, ey - 1.9, ex - 0.4, ey - 0.5, fill="#ffffff",
                           outline="", tags=tag)


def draw_apple(canvas, cx, cy, r, palette, tag, glow=0.0):
    """Draws a glossy apple with stem and leaf, plus an optional soft glow."""
    base, light, dark = palette
    if glow > 0:
        for k in (3, 2, 1):
            rr = r + k * 3.2 * glow
            canvas.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline="",
                               fill=blend(COLOR_TILE_A, base, 0.09 * (4 - k)), tags=tag)
    canvas.create_oval(cx - r * 0.85, cy + r * 0.55, cx + r * 1.0, cy + r * 1.2,
                       fill=COLOR_SHADOW, outline="", tags=tag)
    canvas.create_oval(cx - r, cy - r * 0.9, cx + r, cy + r, fill=dark, outline="", tags=tag)
    canvas.create_oval(cx - r, cy - r * 0.9, cx + r * 0.86, cy + r * 0.84,
                       fill=base, outline="", tags=tag)
    canvas.create_oval(cx - r * 0.22, cy - r * 0.97, cx + r * 0.22, cy - r * 0.62,
                       fill=dark, outline="", tags=tag)
    canvas.create_oval(cx - r * 0.62, cy - r * 0.55, cx - r * 0.12, cy - r * 0.02,
                       fill=light, outline="", tags=tag)
    canvas.create_line(cx, cy - r * 0.75, cx + r * 0.15, cy - r * 1.35, fill=APPLE_STEM,
                       width=max(1.5, r * 0.18), capstyle="round", tags=tag)
    leaf = [(0, 0), (0.55, -0.4), (1.0, -0.1), (0.5, 0.12)]
    pts = []
    for x, y in leaf:
        pts += (cx + r * 0.12 + x * r * 0.75, cy - r * 1.1 + y * r * 0.75)
    canvas.create_polygon(pts, fill=APPLE_LEAF, smooth=True, tags=tag)


def draw_sparkle(canvas, x, y, s, color, tag):
    pts = [(0, -s), (0.3 * s, -0.3 * s), (s, 0), (0.3 * s, 0.3 * s),
           (0, s), (-0.3 * s, 0.3 * s), (-s, 0), (-0.3 * s, -0.3 * s)]
    canvas.create_polygon([c for px, py in pts for c in (x + px, y + py)],
                          fill=color, outline="", tags=tag)


# ----------------------------------------------------------------------
# Button helper
# ----------------------------------------------------------------------
BUTTON_STYLES = {
    # style: (background, hover background, text color)
    "primary": (COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_ACCENT_TEXT),
    "secondary": (COLOR_BUTTON_BG, COLOR_BUTTON_HOVER, COLOR_TEXT),
    "ghost": (COLOR_BG, COLOR_BUTTON_BG, COLOR_SUBTEXT),
}


def make_button(parent, text, command, width=20, style="secondary",
                font=FONT_BUTTON, pady=10, bg=None):
    """
    Creates a flat, modern-looking button with a hover effect.

    Plain Tkinter buttons cannot have true rounded corners, so this
    approximates a clean, modern feel using flat styling, generous
    padding, color styles and a hover color change.
    """
    base_bg, hover_bg, fg = BUTTON_STYLES[style]
    if bg is not None:
        base_bg = bg
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        font=font,
        bg=base_bg,
        fg=fg,
        activebackground=hover_bg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        highlightthickness=0,
        width=width,
        pady=pady,
        cursor="hand2",
    )
    btn.bind("<Enter>", lambda _e: btn.config(bg=hover_bg))
    btn.bind("<Leave>", lambda _e: btn.config(bg=base_bg))
    return btn


# ----------------------------------------------------------------------
# Main application class
# ----------------------------------------------------------------------
class SnakeGame:
    """Owns every screen, the game state and all game logic."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.configure(bg=COLOR_BG)
        # The window can be freely resized/maximized. The game board
        # itself stays a fixed, consistent size, but the surrounding
        # frames re-center themselves as the window grows or shrinks.
        self.root.resizable(True, True)
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.root.geometry(f"{MIN_WINDOW_WIDTH}x{MIN_WINDOW_HEIGHT}")

        # ---- Persistent data ----
        self.high_score = self.load_high_score()

        # ---- Game state ----
        self.difficulty = "Medium"
        self.snake = []
        self.direction = "Right"
        self.next_direction = "Right"
        self.food = None
        self.food_type = "small"          # "small" or "big"
        self.small_eaten_since_big = 0    # counts small balls toward the next big ball
        self.score = 0
        self.delay = DIFFICULTY_SPEEDS[self.difficulty]
        self.running = False
        self.paused = False
        self.game_loop_id = None

        # ---- Animation state (smooth gliding between grid cells) ----
        self.prev_snake = []
        self.grew = False
        self.anim_static = True
        self.last_tick = time.perf_counter()
        self.frozen_t = 0.0
        self.eaten = None                 # (cell, type) of food being swallowed
        self.render_id = None
        self.menu_anim_id = None
        self.overlay_widgets = []

        # ---- Build every screen up front, then show the menu ----
        self.menu_frame = tk.Frame(self.root, bg=COLOR_BG)
        self.difficulty_frame = tk.Frame(self.root, bg=COLOR_BG)
        self.howto_frame = tk.Frame(self.root, bg=COLOR_BG)
        self.game_frame = tk.Frame(self.root, bg=COLOR_BG)

        self.build_menu_screen()
        self.build_difficulty_screen()
        self.build_howto_screen()
        self.build_game_screen()

        # Handle the window's close button safely
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Global key bindings. Game-specific keys are only acted on
        # while a game is actually running (see on_key_press).
        self.root.bind("<Key>", self.on_key_press)

        self.show_main_menu()

    # ------------------------------------------------------------------
    # High score persistence
    # ------------------------------------------------------------------
    def load_high_score(self):
        """Loads the high score from a local JSON file, handling any
        missing or corrupted file without crashing the program."""
        if not os.path.exists(HIGHSCORE_FILE):
            self.save_high_score(0)
            return 0
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                data = json.load(f)
                score = data.get("high_score", 0)
                if not isinstance(score, int) or score < 0:
                    return 0
                return score
        except (json.JSONDecodeError, OSError, ValueError, AttributeError):
            # File is corrupted / unreadable - reset it instead of crashing
            self.save_high_score(0)
            return 0

    def save_high_score(self, score):
        """Writes the high score to a local JSON file. Never crashes the
        game even if the disk write fails for some reason."""
        try:
            with open(HIGHSCORE_FILE, "w") as f:
                json.dump({"high_score": score}, f)
        except OSError:
            pass  # Not fatal - the game just won't persist this time

    # ------------------------------------------------------------------
    # Screen switching helpers
    # ------------------------------------------------------------------
    def hide_all_frames(self):
        self.stop_render_loop()
        self.stop_menu_animation()
        for frame in (self.menu_frame, self.difficulty_frame,
                      self.howto_frame, self.game_frame):
            frame.pack_forget()

    def show_main_menu(self):
        self.running = False
        self.stop_game_loop()
        self.hide_all_frames()
        self.update_score_labels()
        self.menu_frame.pack(fill="both", expand=True)
        self.menu_animate()

    def show_difficulty_screen(self):
        self.hide_all_frames()
        self.difficulty_frame.pack(fill="both", expand=True)

    def show_howto_screen(self):
        self.hide_all_frames()
        self.howto_frame.pack(fill="both", expand=True)

    def show_game_screen(self):
        self.hide_all_frames()
        self.game_frame.pack(fill="both", expand=True)
        self.render_frame()

    # ------------------------------------------------------------------
    # Screen builders
    # ------------------------------------------------------------------
    def build_menu_screen(self):
        wrapper = tk.Frame(self.menu_frame, bg=COLOR_BG)
        wrapper.pack(expand=True)

        self.menu_canvas = tk.Canvas(wrapper, width=600, height=270, bg=COLOR_BG,
                                     highlightthickness=0)
        self.menu_canvas.pack()
        c = self.menu_canvas
        c.create_text(303, 99, text="SNAKE", font=FONT_TITLE,
                      fill=blend(COLOR_BG, COLOR_ACCENT, 0.22))
        c.create_text(300, 95, text="SNAKE", font=FONT_TITLE, fill=COLOR_ACCENT)
        c.create_text(300, 152, text="Eat, grow and beat your high score!",
                      font=FONT_SUBTITLE, fill=COLOR_SUBTEXT)

        buttons = tk.Frame(wrapper, bg=COLOR_BG)
        buttons.pack(pady=(4, 0))
        make_button(buttons, "▶   Start Game", self.show_difficulty_screen,
                    style="primary").pack(pady=6)
        make_button(buttons, "How to Play", self.show_howto_screen).pack(pady=6)
        make_button(buttons, "Exit", self.on_close, style="ghost").pack(pady=6)

        self.menu_high_score_label = tk.Label(
            wrapper, text="", font=FONT_BUTTON, bg=COLOR_PANEL, fg=COLOR_GOLD,
            padx=18, pady=6
        )
        self.menu_high_score_label.pack(pady=(26, 10))

    def build_difficulty_screen(self):
        wrapper = tk.Frame(self.difficulty_frame, bg=COLOR_BG)
        wrapper.pack(expand=True)

        tk.Label(wrapper, text="Select Difficulty", font=FONT_HEADING,
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(40, 4))
        tk.Label(wrapper, text="How fast should your snake slither?",
                 font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_SUBTEXT).pack(pady=(0, 24))

        labels = {
            "Easy": "\U0001F422   Easy",
            "Medium": "\U0001F40D   Medium",
            "Hard": "⚡   Hard",
        }
        for level in ("Easy", "Medium", "Hard"):
            make_button(
                wrapper, labels[level], lambda lvl=level: self.start_game(lvl),
                style="primary" if level == "Medium" else "secondary"
            ).pack(pady=6)

        make_button(wrapper, "←  Back", self.show_main_menu,
                    style="ghost").pack(pady=(28, 10))

    def build_howto_screen(self):
        wrapper = tk.Frame(self.howto_frame, bg=COLOR_BG)
        wrapper.pack(expand=True)

        tk.Label(wrapper, text="How to Play", font=FONT_HEADING,
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(40, 20))

        instructions = (
            "\U0001F40D  Control the snake using Arrow Keys\n"
            "      or W A S D.\n\n"
            "\U0001F34E  Eat the food to grow.\n\n"
            "⭐  Each food gives 10 points.\n\n"
            "\U0001F4A5  Don't hit the wall.\n\n"
            "\U0001F4A5  Don't hit your own body.\n\n"
            "\U0001F3C6  Try to beat your high score!\n\n"
            "Space = Pause / Resume"
        )
        card = tk.Frame(wrapper, bg=COLOR_PANEL, highlightthickness=1,
                        highlightbackground=COLOR_CARD_BORDER, padx=34, pady=24)
        card.pack(pady=(0, 25))
        tk.Label(card, text=instructions, font=FONT_BODY, bg=COLOR_PANEL,
                 fg=COLOR_TEXT, justify="left").pack()

        make_button(wrapper, "←  Back", self.show_main_menu).pack(pady=10)

    def make_stat(self, parent, caption, value, color):
        """A small card with a caption on top and a big value underneath."""
        card = tk.Frame(parent, bg=COLOR_PANEL, highlightthickness=1,
                        highlightbackground=COLOR_CARD_BORDER, padx=14, pady=5)
        card.pack(side="left", padx=(0, 8))
        tk.Label(card, text=caption, font=FONT_CAPTION, bg=COLOR_PANEL,
                 fg=COLOR_SUBTEXT, anchor="w").pack(fill="x")
        value_label = tk.Label(card, text=value, font=FONT_STAT, bg=COLOR_PANEL,
                               fg=color, anchor="w", width=7)
        value_label.pack(fill="x")
        return value_label

    def build_game_screen(self):
        inner = tk.Frame(self.game_frame, bg=COLOR_BG)
        inner.pack(expand=True)

        # ---- Top bar: stat cards on the left, controls on the right ----
        top = tk.Frame(inner, bg=COLOR_BG)
        top.pack(fill="x", pady=(10, 10))

        self.score_label = self.make_stat(top, "SCORE", "0", COLOR_TEXT)
        self.highscore_label = self.make_stat(top, "BEST", str(self.high_score), COLOR_GOLD)
        self.level_label = self.make_stat(top, "LEVEL", self.difficulty, COLOR_ACCENT)

        make_button(top, "Menu", self.show_main_menu, width=7,
                    font=FONT_SMALL_BUTTON, pady=8).pack(side="right")
        make_button(top, "Restart", self.restart_game, width=7,
                    font=FONT_SMALL_BUTTON, pady=8).pack(side="right", padx=6)
        self.pause_button = make_button(top, "Pause", self.toggle_pause, width=7,
                                        font=FONT_SMALL_BUTTON, pady=8)
        self.pause_button.pack(side="right")

        # ---- Canvas (game board), wrapped in a slim bezel ----
        canvas_border = tk.Frame(inner, bg=COLOR_BOARD_BORDER, padx=3, pady=3)
        canvas_border.pack()

        self.canvas = tk.Canvas(
            canvas_border, width=BOARD_SIZE, height=BOARD_SIZE,
            bg=COLOR_TILE_A, highlightthickness=0
        )
        self.canvas.pack()

        tk.Label(inner, text="Arrows / WASD to move   •   Space to pause",
                 font=FONT_CAPTION, bg=COLOR_BG, fg=COLOR_SUBTEXT).pack(pady=(8, 0))

        self.draw_board_background()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def draw_board_background(self):
        """Paints a natural-looking grass field once into a single image:
        soft light/dark patches, thousands of individual blades and a few
        tiny flowers. Built once and reused, so repainting is free."""
        if getattr(self, "board_image", None) is not None:
            self.canvas.create_image(0, 0, image=self.board_image, anchor="nw", tags="bg")
            return
        rng = random.Random(7)                     # fixed seed: same field every time
        size = BOARD_SIZE

        def value_noise(step):
            """Smooth random field (0..1) with features about `step` px wide."""
            n = size // step + 2
            grid = [[rng.random() for _ in range(n)] for _ in range(n)]
            out = []
            for y in range(size):
                gy, fy = divmod(y / step, 1)
                gy = int(gy)
                fy = fy * fy * (3 - 2 * fy)
                r0, r1 = grid[gy], grid[gy + 1]
                row = []
                for x in range(size):
                    gx, fx = divmod(x / step, 1)
                    gx = int(gx)
                    fx = fx * fx * (3 - 2 * fx)
                    top = r0[gx] + (r0[gx + 1] - r0[gx]) * fx
                    bot = r1[gx] + (r1[gx + 1] - r1[gx]) * fx
                    row.append(top + (bot - top) * fy)
                out.append(row)
            return out

        big = value_noise(90)
        mid = value_noise(28)
        dark, light = GRASS_DARK, GRASS_LIGHT

        # Base colour: smooth patches + fine per-pixel grain
        px = []
        for y in range(size):
            row = []
            by, my = big[y], mid[y]
            for x in range(size):
                t = 0.62 * by[x] + 0.38 * my[x]
                g = rng.randint(-9, 9)
                row.append([dark[0] + (light[0] - dark[0]) * t + g,
                            dark[1] + (light[1] - dark[1]) * t + g,
                            dark[2] + (light[2] - dark[2]) * t + g * 0.5])
            px.append(row)

        # Individual blades: thin, slightly curved strokes, shadowed at the
        # root and catching light at the tip; some are drier/yellower.
        for _ in range(size * size // 9):
            x0 = rng.uniform(0, size)
            y0 = rng.uniform(0, size)
            length = rng.randint(4, 10)
            lean = rng.uniform(-0.45, 0.45)
            bend = rng.uniform(-0.04, 0.04)
            dry = rng.random() < 0.12
            for k in range(length):
                y = int(y0 - k)
                x = int(x0 + lean * k + bend * k * k)
                if not (0 <= x < size and 0 <= y < size):
                    break
                f = k / (length - 1)
                shade = -30 + 52 * f
                c = px[y][x]
                c[0] += shade + (16 if dry else 0)
                c[1] += shade + (8 if dry else 3)
                c[2] += shade * 0.45

        # A few tiny wildflowers
        for _ in range(18):
            x0 = rng.randrange(2, size - 2)
            y0 = rng.randrange(2, size - 2)
            petal = rng.choice(([245, 245, 235], [250, 225, 100], [225, 180, 230]))
            for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                px[y0 + dy][x0 + dx] = list(petal)
            px[y0][x0] = [235, 180, 50]

        def clamp(v):
            v = int(v)
            return 0 if v < 0 else 255 if v > 255 else v

        data = " ".join(
            "{" + " ".join("#%02x%02x%02x" % (clamp(r), clamp(g), clamp(b))
                           for r, g, b in row) + "}"
            for row in px)
        self.board_image = tk.PhotoImage(width=size, height=size)
        self.board_image.put(data, to=(0, 0))
        self.canvas.create_image(0, 0, image=self.board_image, anchor="nw", tags="bg")

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------
    def start_game(self, difficulty):
        """Starts a brand-new game at the chosen difficulty."""
        self.difficulty = difficulty
        self.show_game_screen()
        self.reset_game()

    def reset_game(self):
        """Resets all game state for a fresh run (used by Start and Restart).
        Never touches the high score."""
        self.stop_game_loop()
        self.clear_overlay()

        center = GRID_COUNT // 2
        self.snake = [(center - 1, center), (center - 2, center), (center - 3, center)]
        self.direction = "Right"
        self.next_direction = "Right"
        self.score = 0
        self.food_type = "small"
        self.small_eaten_since_big = 0
        self.delay = DIFFICULTY_SPEEDS[self.difficulty]
        self.paused = False
        self.running = True

        self.prev_snake = []
        self.anim_static = True
        self.eaten = None

        self.pause_button.config(text="Pause")
        self.update_score_labels()

        self.create_food()
        self.redraw_board()
        self.last_tick = time.perf_counter()
        self.game_loop_id = self.root.after(self.delay, self.game_loop)

    def restart_game(self):
        """Restarts the current game without touching the high score."""
        self.reset_game()

    def stop_game_loop(self):
        """Cancels any pending scheduled game loop call, if one exists."""
        if self.game_loop_id is not None:
            try:
                self.root.after_cancel(self.game_loop_id)
            except ValueError:
                pass
            self.game_loop_id = None

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------
    def on_key_press(self, event):
        key = event.keysym

        if not self.running:
            return  # Ignore game keys when no game is on screen

        direction_map = {
            "Up": "Up", "w": "Up", "W": "Up",
            "Down": "Down", "s": "Down", "S": "Down",
            "Left": "Left", "a": "Left", "A": "Left",
            "Right": "Right", "d": "Right", "D": "Right",
        }
        opposite = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}

        if key == "space":
            self.toggle_pause()
            return

        if self.paused:
            return

        if key in direction_map:
            new_dir = direction_map[key]
            # Prevent an immediate 180-degree turn into the snake's own body
            if new_dir != opposite.get(self.direction):
                self.next_direction = new_dir

    # ------------------------------------------------------------------
    # Pause / resume
    # ------------------------------------------------------------------
    def toggle_pause(self):
        if not self.running:
            return
        if self.paused:
            self.resume_game()
        else:
            self.pause_game()

    def pause_game(self):
        self.frozen_t = self.anim_progress()
        self.paused = True
        self.pause_button.config(text="Resume")
        self.stop_game_loop()
        self.show_pause_overlay()

    def resume_game(self):
        self.paused = False
        self.pause_button.config(text="Pause")
        self.clear_overlay()
        # Continue the current glide exactly where it was frozen
        remaining = self.delay * (1.0 - self.frozen_t)
        self.last_tick = time.perf_counter() - self.frozen_t * self.delay / 1000.0
        self.game_loop_id = self.root.after(max(1, int(remaining)), self.game_loop)

    def clear_overlay(self):
        self.canvas.delete("overlay")
        for widget in self.overlay_widgets:
            widget.destroy()
        self.overlay_widgets = []

    def overlay_card(self, height):
        """Dims the board and draws a centered rounded card; returns its top y."""
        self.clear_overlay()
        self.canvas.create_rectangle(
            0, 0, BOARD_SIZE, BOARD_SIZE, fill=COLOR_OVERLAY_BG,
            stipple="gray50", outline="", tags="overlay"
        )
        w = 340
        x1 = (BOARD_SIZE - w) // 2
        y1 = (BOARD_SIZE - height) // 2
        rounded_rect(self.canvas, x1, y1, x1 + w, y1 + height, 22,
                     fill=COLOR_PANEL, outline=COLOR_CARD_BORDER, width=2, tags="overlay")
        return y1

    def overlay_button(self, text, command, y, style):
        btn = make_button(self.canvas, text, command, width=18, style=style,
                          bg=COLOR_PANEL if style == "ghost" else None)
        self.overlay_widgets.append(btn)
        self.canvas.create_window(BOARD_SIZE // 2, y, window=btn, tags="overlay")

    def show_pause_overlay(self):
        cx = BOARD_SIZE // 2
        top = self.overlay_card(200)
        self.canvas.create_text(cx, top + 48, text="PAUSED", font=FONT_HEADING,
                                fill=COLOR_TEXT, tags="overlay")
        self.canvas.create_text(cx, top + 86, text="Press Space to resume",
                                font=FONT_BODY, fill=COLOR_SUBTEXT, tags="overlay")
        self.overlay_button("▶  Resume", self.resume_game, top + 145, "primary")

    # ------------------------------------------------------------------
    # Core game loop (driven by Tkinter's after(), never a blocking loop)
    # ------------------------------------------------------------------
    def game_loop(self):
        if not self.running or self.paused:
            return

        prev = list(self.snake)
        self.move_snake()

        if self.check_collision():
            # Show the snake where it was at the moment of impact
            self.snake = prev
            self.anim_static = True
            self.game_over()
            return

        self.prev_snake = prev
        self.grew = len(self.snake) > len(prev)
        self.anim_static = False
        self.last_tick = time.perf_counter()
        self.eaten = (self.food, self.food_type) if self.grew else None

        self.check_food()

        if self.running:
            self.game_loop_id = self.root.after(self.delay, self.game_loop)

    def move_snake(self):
        """Advances the snake by one cell in the current direction."""
        self.direction = self.next_direction
        head_x, head_y = self.snake[0]

        move_deltas = {
            "Up": (0, -1),
            "Down": (0, 1),
            "Left": (-1, 0),
            "Right": (1, 0),
        }
        dx, dy = move_deltas[self.direction]
        new_head = (head_x + dx, head_y + dy)

        self.snake.insert(0, new_head)
        # Only drop the tail if we did NOT just eat food (growth = keep tail)
        if new_head != self.food:
            self.snake.pop()

    def check_collision(self):
        """Returns True if the snake has hit a wall or its own body."""
        head_x, head_y = self.snake[0]

        if head_x < 0 or head_x >= GRID_COUNT or head_y < 0 or head_y >= GRID_COUNT:
            return True
        if self.snake[0] in self.snake[1:]:
            return True
        return False

    def check_food(self):
        """Handles eating food: score, new food, and a small speed bump.

        Every BIG_FOOD_EVERY small balls eaten, the next ball spawned is a
        big bonus ball worth more points. After the big ball is eaten, the
        game goes back to spawning normal small balls.
        """
        if self.snake[0] != self.food:
            return

        if self.food_type == "big":
            self.score += BIG_FOOD_SCORE
        else:
            self.score += SCORE_PER_FOOD
            self.small_eaten_since_big += 1

        self.update_score_labels()

        # Decide what the NEXT ball should be
        if self.food_type == "small" and self.small_eaten_since_big >= BIG_FOOD_EVERY:
            self.food_type = "big"
            self.small_eaten_since_big = 0
        else:
            self.food_type = "small"

        self.create_food()

        if self.delay > MIN_DELAY:
            self.delay = max(MIN_DELAY, self.delay - SPEED_INCREASE_STEP)

    def create_food(self):
        """Places food on a random empty cell - never on the snake's body."""
        available_cells = [
            (x, y)
            for x in range(GRID_COUNT)
            for y in range(GRID_COUNT)
            if (x, y) not in self.snake
        ]
        if available_cells:
            self.food = random.choice(available_cells)
        else:
            # The snake fills the entire board - an effective "win" state
            self.food = None
            self.game_over()

    # ------------------------------------------------------------------
    # Rendering (runs every frame for smooth animation)
    # ------------------------------------------------------------------
    def render_frame(self):
        self.render_id = None
        self.redraw_board()
        self.render_id = self.root.after(FRAME_MS, self.render_frame)

    def stop_render_loop(self):
        if self.render_id is not None:
            self.root.after_cancel(self.render_id)
            self.render_id = None

    def anim_progress(self):
        """How far (0..1) the snake has glided from its previous cell."""
        if self.anim_static:
            return 1.0
        if self.paused:
            return self.frozen_t
        elapsed_ms = (time.perf_counter() - self.last_tick) * 1000.0
        return max(0.0, min(1.0, elapsed_ms / self.delay))

    @staticmethod
    def cell_center(cell):
        return (cell[0] * CELL_SIZE + CELL_SIZE / 2, cell[1] * CELL_SIZE + CELL_SIZE / 2)

    def snake_path(self, t):
        """Pixel points along the snake (head first) at glide progress t."""
        cur = [self.cell_center(p) for p in self.snake]
        if self.anim_static or not self.prev_snake:
            return cur
        prev = [self.cell_center(p) for p in self.prev_snake]
        pts = [lerp_pt(prev[0], cur[0], t)] + cur[1:]
        if not self.grew:
            pts.append(lerp_pt(prev[-1], cur[-1], t))
        return pts

    def redraw_board(self):
        if not self.snake:
            return
        self.canvas.delete("dyn")
        now = time.perf_counter()
        t = self.anim_progress()

        # Food currently being swallowed shrinks as the head reaches it
        if self.eaten and not self.anim_static and t < 1.0:
            cell, kind = self.eaten
            scale = max(0.0, min(1.0, (1.0 - t) / 0.4))
            if scale > 0:
                self.draw_food_at(cell, kind, now, scale)

        if self.food is not None:
            self.draw_food_at(self.food, self.food_type, now, 1.0)

        draw_snake(self.canvas, self.snake_path(t), now, "dyn")
        self.canvas.tag_raise("overlay")

    def draw_food_at(self, cell, kind, now, scale):
        cx, cy = self.cell_center(cell)
        pulse = 1.0 + 0.06 * math.sin(now * 5)
        if kind == "big":
            r = CELL_SIZE * 0.62 * pulse * scale
            draw_apple(self.canvas, cx, cy, r, APPLE_GOLD, "dyn",
                       glow=(1.0 + 0.4 * math.sin(now * 4)) * scale)
            if scale >= 1.0:
                for k in range(3):
                    ang = now * 2.2 + k * 2 * math.pi / 3
                    draw_sparkle(self.canvas, cx + math.cos(ang) * (r + 8),
                                 cy + math.sin(ang) * (r + 8),
                                 2.6 + math.sin(now * 6 + k), APPLE_GOLD[1], "dyn")
        else:
            r = CELL_SIZE * 0.36 * pulse * scale
            draw_apple(self.canvas, cx, cy, r, APPLE_RED, "dyn", glow=0.6 * scale)

    def update_score_labels(self):
        self.score_label.config(text=str(self.score))
        self.highscore_label.config(text=str(self.high_score))
        self.level_label.config(text=self.difficulty)
        self.menu_high_score_label.config(text=f"\U0001F3C6  High Score: {self.high_score}")

    # ------------------------------------------------------------------
    # Main menu animation (a snake slithering along a wave)
    # ------------------------------------------------------------------
    def menu_animate(self):
        self.menu_anim_id = None
        c = self.menu_canvas
        c.delete("demo")
        now = time.perf_counter()
        head_x = (now * 90) % (600 + 260) - 130
        pts = []
        for i in range(56):
            x = head_x - i * 4
            pts.append((x, 222 + 14 * math.sin(x * 0.045)))
        draw_snake(c, pts, now, "demo")
        self.menu_anim_id = self.root.after(FRAME_MS, self.menu_animate)

    def stop_menu_animation(self):
        if self.menu_anim_id is not None:
            self.root.after_cancel(self.menu_anim_id)
            self.menu_anim_id = None

    # ------------------------------------------------------------------
    # Game over
    # ------------------------------------------------------------------
    def game_over(self):
        self.running = False
        self.stop_game_loop()

        new_record = self.score > self.high_score
        if new_record:
            self.high_score = self.score
            self.save_high_score(self.high_score)

        self.update_score_labels()
        self.show_game_over_overlay(new_record)

    def show_game_over_overlay(self, new_record=False):
        cx = BOARD_SIZE // 2
        top = self.overlay_card(330)

        message = random.choice(["Nice Try!", "Great Run!", "Can you beat your high score?"])

        self.canvas.create_text(cx, top + 44, text="GAME OVER", font=FONT_HEADING,
                                fill=COLOR_DANGER, tags="overlay")
        self.canvas.create_text(cx, top + 78, text=message, font=FONT_BODY,
                                fill=COLOR_SUBTEXT, tags="overlay")
        self.canvas.create_text(cx, top + 124, text=str(self.score), font=FONT_BIG_STAT,
                                fill=COLOR_TEXT, tags="overlay")
        best_text = ("★  NEW HIGH SCORE!  ★" if new_record
                     else f"Best: {self.high_score}")
        self.canvas.create_text(cx, top + 162, text=best_text, font=FONT_BUTTON,
                                fill=COLOR_GOLD, tags="overlay")

        self.overlay_button("Play Again", self.restart_game, top + 222, "primary")
        self.overlay_button("Main Menu", self.show_main_menu, top + 278, "ghost")

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    def on_close(self):
        """Handles the window's close event safely, cancelling any pending loop."""
        self.stop_game_loop()
        self.stop_render_loop()
        self.stop_menu_animation()
        self.root.destroy()


def main():
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
