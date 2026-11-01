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
        for frame in (self.menu_frame, self.difficulty_frame,
                      self.howto_frame, self.game_frame):
            frame.pack_forget()

    def show_main_menu(self):
        self.running = False
        self.stop_game_loop()
        self.hide_all_frames()
        self.update_score_labels()
        self.menu_frame.pack(fill="both", expand=True)

    def show_difficulty_screen(self):
        self.hide_all_frames()
        self.difficulty_frame.pack(fill="both", expand=True)

    def show_howto_screen(self):
        self.hide_all_frames()
        self.howto_frame.pack(fill="both", expand=True)

    def show_game_screen(self):
        self.hide_all_frames()
        self.game_frame.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Screen builders
    # ------------------------------------------------------------------
    def build_menu_screen(self):
        wrapper = tk.Frame(self.menu_frame, bg=COLOR_BG)
        wrapper.pack(expand=True)

        tk.Label(wrapper, text="\U0001F40D Snake Game", font=FONT_TITLE,
                 bg=COLOR_BG, fg=COLOR_ACCENT).pack(pady=(40, 5))
        tk.Label(wrapper, text="Eat, grow and beat your high score!",
                 font=FONT_SUBTITLE, bg=COLOR_BG, fg=COLOR_SUBTEXT).pack(pady=(0, 30))

        make_button(wrapper, "Start Game", self.show_difficulty_screen).pack(pady=8)
        make_button(wrapper, "How to Play", self.show_howto_screen).pack(pady=8)
        make_button(wrapper, "Exit", self.on_close).pack(pady=8)

        self.menu_high_score_label = tk.Label(
            wrapper, text=f"High Score: {self.high_score}",
            font=FONT_BODY, bg=COLOR_BG, fg=COLOR_SUBTEXT
        )
        self.menu_high_score_label.pack(pady=(30, 10))

    def build_difficulty_screen(self):
        wrapper = tk.Frame(self.difficulty_frame, bg=COLOR_BG)
        wrapper.pack(expand=True)

        tk.Label(wrapper, text="Select Difficulty", font=FONT_HEADING,
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(40, 25))

        for level in ("Easy", "Medium", "Hard"):
            make_button(
                wrapper, level, lambda lvl=level: self.start_game(lvl)
            ).pack(pady=8)

        make_button(wrapper, "Back", self.show_main_menu,
                    bg=COLOR_PANEL, hover_bg=COLOR_BUTTON_HOVER).pack(pady=(30, 10))

    def build_howto_screen(self):
        wrapper = tk.Frame(self.howto_frame, bg=COLOR_BG)
        wrapper.pack(expand=True)

        tk.Label(wrapper, text="How to Play", font=FONT_HEADING,
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(40, 20))

        instructions = (
            "\U0001F40D  Control the snake using Arrow Keys\n"
            "      or W A S D.\n\n"
            "\U0001F34E  Eat the food to grow.\n\n"
            "\u2B50  Each food gives 10 points.\n\n"
            "\U0001F4A5  Don't hit the wall.\n\n"
            "\U0001F4A5  Don't hit your own body.\n\n"
            "\U0001F3C6  Try to beat your high score!\n\n"
            "Space = Pause / Resume"
        )
        tk.Label(wrapper, text=instructions, font=FONT_BODY, bg=COLOR_BG,
                 fg=COLOR_TEXT, justify="left").pack(pady=(0, 25))

        make_button(wrapper, "Back", self.show_main_menu).pack(pady=10)




    def build_game_screen(self):
        # ---- Top score panel ----
        panel = tk.Frame(self.game_frame, bg=COLOR_PANEL, height=60)
        panel.pack(fill="x")

        self.score_label = tk.Label(
            panel, text="Score: 0", font=FONT_SCORE, bg=COLOR_PANEL, fg=COLOR_TEXT
        )
        self.score_label.pack(side="left", padx=20, pady=12)

        self.highscore_label = tk.Label(
            panel, text=f"High Score: {self.high_score}",
            font=FONT_SCORE, bg=COLOR_PANEL, fg=COLOR_ACCENT
        )
        self.highscore_label.pack(side="right", padx=20, pady=12)

        # ---- Control buttons ----
        controls = tk.Frame(self.game_frame, bg=COLOR_BG)
        controls.pack(fill="x", pady=6)

        self.pause_button = make_button(
            controls, "Pause", self.toggle_pause, width=10, font=FONT_BODY
        )
        self.pause_button.pack(side="left", padx=20)

        make_button(
            controls, "Restart", self.restart_game, width=10, font=FONT_BODY
        ).pack(side="left", padx=6)

        make_button(
            controls, "Main Menu", self.show_main_menu, width=10, font=FONT_BODY
        ).pack(side="right", padx=20)

        # ---- Canvas (game board), wrapped in a colored bezel border ----
        canvas_border = tk.Frame(self.game_frame, bg=COLOR_BOARD_BORDER, padx=4, pady=4)
        canvas_border.pack(pady=10)

        self.canvas = tk.Canvas(
            canvas_border, width=BOARD_SIZE, height=BOARD_SIZE,
            bg=COLOR_BOARD_BG, highlightthickness=0
        )
        self.canvas.pack()

        self.draw_grid_lines()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def draw_grid_lines(self):
        """Draws subtle grid lines once; they sit behind the snake/food."""
        for i in range(1, GRID_COUNT):
            pos = i * CELL_SIZE
            self.canvas.create_line(pos, 0, pos, BOARD_SIZE, fill=COLOR_GRID_LINE)
            self.canvas.create_line(0, pos, BOARD_SIZE, pos, fill=COLOR_GRID_LINE)





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
        self.canvas.delete("overlay")

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

        self.pause_button.config(text="Pause")
        self.update_score_labels()

        self.create_food()
        self.redraw_board()
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
        self.paused = True
        self.pause_button.config(text="Resume")
        self.stop_game_loop()
        self.show_pause_overlay()

    def resume_game(self):
        self.paused = False
        self.pause_button.config(text="Pause")
        self.canvas.delete("overlay")
        self.game_loop_id = self.root.after(self.delay, self.game_loop)

    def show_pause_overlay(self):
        self.canvas.delete("overlay")
        cx, cy = BOARD_SIZE // 2, BOARD_SIZE // 2
        self.canvas.create_rectangle(
            0, 0, BOARD_SIZE, BOARD_SIZE, fill=COLOR_OVERLAY_BG,
            stipple="gray50", outline="", tags="overlay"
        )
        self.canvas.create_text(
            cx, cy - 40, text="PAUSED", font=FONT_HEADING,
            fill=COLOR_TEXT, tags="overlay"
        )
        resume_btn = make_button(self.canvas, "Resume", self.resume_game, width=14)
        self.canvas.create_window(cx, cy + 20, window=resume_btn, tags="overlay")