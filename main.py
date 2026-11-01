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




    # ------------------------------------------------------------------
    # Core game loop (driven by Tkinter's after(), never a blocking loop)
    # ------------------------------------------------------------------
    def game_loop(self):
        if not self.running or self.paused:
            return

        self.move_snake()

        if self.check_collision():
            self.game_over()
            return

        self.check_food()
        self.redraw_board()

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
    # Rendering
    # ------------------------------------------------------------------
    def redraw_board(self):
        self.canvas.delete("snake", "food")
        self.draw_food()
        self.draw_snake()

    def draw_3d_block(self, x1, y1, x2, y2, light, base, dark, tag):
        """Draws one grid cell as a small beveled 3D-looking cube.

        Technique: a dark full-size rectangle acts as the block's shadow
        edge, a slightly inset lighter rectangle forms the main face (so a
        thin dark sliver remains visible along the bottom/right = shadow),
        and a thin bright strip along the top/left simulates a light
        source hitting the block, giving it a raised, chunky 3D feel.
        """
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=dark, outline="", tags=tag)
        self.canvas.create_rectangle(
            x1, y1, x2 - 2, y2 - 2, fill=base, outline="", tags=tag
        )
        self.canvas.create_rectangle(
            x1, y1, x2 - 2, y1 + 3, fill=light, outline="", tags=tag
        )
        self.canvas.create_rectangle(
            x1, y1, x1 + 3, y2 - 2, fill=light, outline="", tags=tag
        )

    def draw_snake(self):
        for index, (x, y) in enumerate(self.snake):
            x1, y1 = x * CELL_SIZE, y * CELL_SIZE
            x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
            pad = 1  # tiny gap between segments so each block reads clearly

            if index == 0:
                self.draw_3d_block(
                    x1 + pad, y1 + pad, x2 - pad, y2 - pad,
                    COLOR_SNAKE_HEAD_LIGHT, COLOR_SNAKE_HEAD, COLOR_SNAKE_HEAD_DARK,
                    "snake"
                )
                self.draw_eyes(x1, y1)
            else:
                self.draw_3d_block(
                    x1 + pad, y1 + pad, x2 - pad, y2 - pad,
                    COLOR_SNAKE_BODY_LIGHT, COLOR_SNAKE_BODY, COLOR_SNAKE_BODY_DARK,
                    "snake"
                )

    def draw_eyes(self, x1, y1):
        """Draws two small glossy eyes on the snake's head, oriented by direction."""
        eye_radius = 2
        offsets = {
            "Up": [(6, 6), (CELL_SIZE - 6, 6)],
            "Down": [(6, CELL_SIZE - 6), (CELL_SIZE - 6, CELL_SIZE - 6)],
            "Left": [(6, 6), (6, CELL_SIZE - 6)],
            "Right": [(CELL_SIZE - 6, 6), (CELL_SIZE - 6, CELL_SIZE - 6)],
        }
        for ox, oy in offsets.get(self.direction, offsets["Right"]):
            ex, ey = x1 + ox, y1 + oy
            self.canvas.create_oval(
                ex - eye_radius, ey - eye_radius, ex + eye_radius, ey + eye_radius,
                fill=COLOR_BOARD_BG, outline="", tags="snake"
            )
            # Tiny highlight dot so the eye looks glossy rather than flat
            self.canvas.create_oval(
                ex - 1, ey - 1, ex, ey, fill=COLOR_TEXT, outline="", tags="snake"
            )

    def draw_sphere(self, x1, y1, x2, y2, light, base, dark, tag):
        """Draws a food ball as a small glossy 3D sphere.

        Technique: a dark circle sits behind as the shadowed edge, a
        slightly smaller base-colored circle offset toward the top-left
        sits on top (leaving a dark crescent at the bottom-right), and a
        small bright oval near the top-left fakes a specular highlight.
        """
        self.canvas.create_oval(x1, y1, x2, y2, fill=dark, outline="", tags=tag)
        self.canvas.create_oval(
            x1, y1, x2 - 2, y2 - 2, fill=base, outline="", tags=tag
        )
        w = x2 - x1
        hx1, hy1 = x1 + w * 0.20, y1 + w * 0.18
        hx2, hy2 = x1 + w * 0.55, y1 + w * 0.50
        self.canvas.create_oval(hx1, hy1, hx2, hy2, fill=light, outline="", tags=tag)

    def draw_food(self):
        if self.food is None:
            return
        x, y = self.food
        x1, y1 = x * CELL_SIZE, y * CELL_SIZE
        x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE

        if self.food_type == "big":
            # The bonus ball is drawn larger, bulging slightly into
            # neighboring cells, so it clearly stands out from normal food.
            grow = 5
            self.draw_sphere(
                x1 - grow, y1 - grow, x2 + grow, y2 + grow,
                COLOR_BIG_FOOD_LIGHT, COLOR_BIG_FOOD, COLOR_BIG_FOOD_DARK, "food"
            )
        else:
            pad = 3
            self.draw_sphere(
                x1 + pad, y1 + pad, x2 - pad, y2 - pad,
                COLOR_FOOD_LIGHT, COLOR_FOOD, COLOR_FOOD_DARK, "food"
            )

    def update_score_labels(self):
        self.score_label.config(text=f"Score: {self.score}")
        self.highscore_label.config(text=f"High Score: {self.high_score}")
        self.menu_high_score_label.config(text=f"High Score: {self.high_score}")


