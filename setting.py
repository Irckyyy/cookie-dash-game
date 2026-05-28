"""
setting.py — All game constants, colors, tile types, and configuration.
Directly translated from the HTML/JS constants and CSS variables.
"""

import pygame

# ======================== WINDOW ========================
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 760
FPS = 60
GAME_TITLE = "Cookie Delivery Dash"

# ======================== GRID ========================
SIZE = 10          # 10×10 grid
TILE_SIZE = 44     # pixel size of each tile
TILE_GAP = 2       # gap between tiles
GRID_PADDING = 6   # padding inside grid wrapper

# Calculated grid pixel dimensions
GRID_PX = SIZE * TILE_SIZE + (SIZE - 1) * TILE_GAP + GRID_PADDING * 2

# ======================== TILE TYPES ========================
class Tile:
    EMPTY   = 0
    WALL    = 1
    HOUSE   = 2
    EXIT    = 3
    PUDDLE  = 4
    BROKEN  = 5
    START   = 6

# ======================== DIRECTIONS ========================
DIRS = [
    (1, 0),   # right
    (-1, 0),  # left
    (0, 1),   # down
    (0, -1),  # up
]


# ======================== COLORS (from CSS :root) ========================
class Colors:
    NIGHT       = (10, 14, 26)
    DEEP        = (17, 24, 39)
    CARD        = (26, 34, 53)
    BORDER      = (42, 58, 85)
    GOLD        = (245, 200, 66)
    AMBER       = (232, 160, 32)
    GREEN       = (34, 197, 94)
    RED         = (239, 68, 68)
    BLUE        = (96, 165, 250)
    PURPLE      = (167, 139, 250)
    TEXT        = (226, 232, 240)
    MUTED       = (100, 116, 139)
    WHITE       = (255, 255, 255)
    BLACK       = (0, 0, 0)

    # Tile backgrounds (from CSS)
    TILE_DEFAULT   = (13, 21, 37)
    TILE_REVEALED  = (22, 36, 58)
    TILE_HIDDEN    = (10, 14, 26)
    TILE_START     = (96, 165, 250, 38)     # rgba blue tint
    TILE_EXIT      = (34, 197, 94, 38)      # rgba green tint
    TILE_HOUSE     = (245, 200, 66, 26)     # rgba gold tint
    TILE_HOUSE_DEL = (34, 197, 94, 38)      # delivered house
    TILE_PUDDLE    = (59, 130, 246, 51)      # rgba blue
    TILE_BROKEN    = (239, 68, 68, 38)       # rgba red

    # Blended solid colors for tiles (pre-blended on dark background)
    TILE_START_SOLID   = (20, 38, 70)
    TILE_EXIT_SOLID    = (18, 43, 41)
    TILE_HOUSE_SOLID   = (34, 38, 40)
    TILE_HOUSE_DEL_SOLID = (18, 43, 41)
    TILE_PUDDLE_SOLID  = (18, 33, 62)
    TILE_BROKEN_SOLID  = (42, 25, 31)

    # Player glow
    PLAYER_GLOW = (96, 165, 250)
    AI_GLOW     = (167, 139, 250)

# ======================== DIFFICULTY ========================
class Difficulty:
    EASY   = "easy"
    MEDIUM = "medium"
    HARD   = "hard"

DIFFICULTY_CONFIG = {
    Difficulty.EASY: {
        "name": "Easy",
        "desc": "3×3 vision\nAI uses random paths + memory decay",
        "vision_radius": 1,
        "ai_speed_ms": 800,
        "ai_label": "(Stochastic)",
        "boots_durability": 3,
        "rope_durability": 3,
        "flashlight_duration": 10,
    },
    Difficulty.MEDIUM: {
        "name": "Medium",
        "desc": "2×2 vision\nAI uses deterministic greedy search",
        "vision_radius": 1,
        "ai_speed_ms": 500,
        "ai_label": "(Greedy)",
        "boots_durability": 2,
        "rope_durability": 2,
        "flashlight_duration": 7,
    },
    Difficulty.HARD: {
        "name": "Hard",
        "desc": "1×1 vision\nAI uses lookahead DFS with predictive pruning",
        "vision_radius": 0,
        "ai_speed_ms": 350,
        "ai_label": "(Lookahead)",
        "boots_durability": 1,
        "rope_durability": 1,
        "flashlight_duration": 5,
    },
}

# ======================== AI ALGORITHM DESCRIPTIONS ========================
ALGORITHM_DESCRIPTIONS = {
    Difficulty.EASY: (
        "Stochastic Random Walk",
        "AI randomly explores with 30% noise injected into\n"
        "movement decisions. Memory resets every 10 steps,\n"
        "simulating forgetfulness.",
    ),
    Difficulty.MEDIUM: (
        "Greedy Best-First Search",
        "AI always moves toward the nearest undelivered goal\n"
        "using Manhattan distance heuristic. Maintains persistent\n"
        "memory of obstacles encountered.",
    ),
    Difficulty.HARD: (
        "Heuristic Backtracking DFS",
        "AI uses depth-first search with hazard avoidance,\n"
        "cycle detection, and adaptive memory clearing.\n"
        "Falls back to random exploration when stuck.",
    ),
}

# ======================== AI ALGORITHM DESCRIPTIONS ========================
ALGORITHM_DESCRIPTIONS = {
    Difficulty.EASY: (
        "Stochastic Random Walk",
        "AI randomly explores with 30% noise injected into\n"
        "movement decisions. Memory resets every 10 steps,\n"
        "simulating forgetfulness.",
    ),
    Difficulty.MEDIUM: (
        "Greedy Best-First Search",
        "AI always moves toward the nearest undelivered goal\n"
        "using Manhattan distance heuristic. Maintains persistent\n"
        "memory of obstacles encountered.",
    ),
    Difficulty.HARD: (
        "Heuristic Backtracking DFS",
        "AI uses depth-first search with hazard avoidance,\n"
        "cycle detection, and adaptive memory clearing.\n"
        "Falls back to random exploration when stuck.",
    ),
}

# ======================== SCORING ========================
SCORE_REVEAL_TILE   = 50
SCORE_DELIVERY      = 800
PENALTY_PUDDLE      = 150
PENALTY_BROKEN      = 200
REVERT_PUDDLE       = 2    # steps pushed back
REVERT_BROKEN       = 3
BONUS_ITEM_CHANCE_PLAYER = 0.4
BONUS_ITEM_CHANCE_AI     = 0.3
DELIVERIES_NEEDED   = 3

# ======================== HOUSE POSITIONS ========================
HOUSE_POSITIONS = [
    (8, 1),
    (8, 8),
    (2, 8),
]
EXIT_POSITION = (9, 9)
START_POSITION = (0, 0)

# ======================== OBSTACLE GENERATION ========================
PUDDLE_CHANCE = 0.13
BROKEN_CHANCE = 0.09   # 0.22 - 0.13 cumulative
