"""
Snake Game
==========
A complete, polished classic Snake Game built with Python's standard
library (Tkinter only - no external dependencies, no internet required).

Run with:
    python main.py
"""

import tkinter as tk
import json
import os
import random

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

HIGHSCORE_FILE = "highscore.json"

DIFFICULTY_SPEEDS = {
    "Easy": 150,
    "Medium": 100,
    "Hard": 70,
}

MIN_WINDOW_WIDTH = 660
MIN_WINDOW_HEIGHT = 780

# ---- Color theme (dark, modern) ----
COLOR_BG = "#1a1a26"
COLOR_PANEL = "#252538"
COLOR_PANEL_ALT = "#2c2c44"
COLOR_BOARD_BG = "#101018"
COLOR_GRID_LINE = "#20202e"
COLOR_BOARD_BORDER = "#3a3a55"

# Snake - base / light(highlight) / dark(shadow) tones for a 3D beveled look
COLOR_SNAKE_HEAD = "#7CFC93"
COLOR_SNAKE_HEAD_LIGHT = "#C8FFD4"
COLOR_SNAKE_HEAD_DARK = "#2E9E4F"

COLOR_SNAKE_BODY = "#43A047"
COLOR_SNAKE_BODY_LIGHT = "#7EDB86"
COLOR_SNAKE_BODY_DARK = "#245C28"

# Small food (apple-red sphere)
COLOR_FOOD = "#FF5252"
COLOR_FOOD_LIGHT = "#FFB3B3"
COLOR_FOOD_DARK = "#B71C1C"

# Big / bonus food (golden sphere)
COLOR_BIG_FOOD = "#FFC107"
COLOR_BIG_FOOD_LIGHT = "#FFF3C4"
COLOR_BIG_FOOD_DARK = "#B8860B"

COLOR_TEXT = "#EAEAEA"
COLOR_SUBTEXT = "#9A9AB0"
COLOR_ACCENT = "#4CAF50"
COLOR_BUTTON_BG = "#2e2e42"
COLOR_BUTTON_HOVER = "#3a3a55"
COLOR_OVERLAY_BG = "#000000"

FONT_TITLE = ("Segoe UI", 34, "bold")
FONT_SUBTITLE = ("Segoe UI", 12)
FONT_HEADING = ("Segoe UI", 22, "bold")
FONT_BODY = ("Segoe UI", 12)
FONT_BUTTON = ("Segoe UI", 13, "bold")
FONT_SCORE = ("Segoe UI", 13, "bold")




# ----------------------------------------------------------------------
# Button helper
# ----------------------------------------------------------------------
def make_button(parent, text, command, width=20, bg=COLOR_BUTTON_BG,
                 fg=COLOR_TEXT, hover_bg=COLOR_BUTTON_HOVER, font=FONT_BUTTON):
    """
    Creates a flat, modern-looking button with a hover effect.

    Plain Tkinter buttons cannot have true rounded corners, so this
    approximates a clean "rounded-button" feel using flat styling,
    generous padding and a hover color change.
    """
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        font=font,
        bg=bg,
        fg=fg,
        activebackground=hover_bg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        width=width,
        pady=10,
        cursor="hand2",
    )

    def on_enter(_event):
        btn["bg"] = hover_bg

    def on_leave(_event):
        btn["bg"] = bg

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
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
        # The window can now be freely resized/maximized. The game board
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