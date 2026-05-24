"""
core/player.py — Player class handling state, movement, vision, and scoring.
Translated from initPlayer(), movePlayer(), revertSteps(), tilesInView(),
addRevealedTiles() in the HTML source.
"""

import random
from setting import (
    SIZE, Tile, DIRS,
    SCORE_REVEAL_TILE, SCORE_DELIVERY,
    PENALTY_PUDDLE, PENALTY_BROKEN,
    REVERT_PUDDLE, REVERT_BROKEN,
    BONUS_ITEM_CHANCE_PLAYER, DELIVERIES_NEEDED,
    DIFFICULTY_CONFIG,
)


class Player:
    """Represents a player (human or AI) on the game board."""

    def __init__(self, is_human: bool):
        self.is_human = is_human
        self.pos = (0, 0)          # (x, y) position
        self.score = 0
        self.deliveries = 0
        self.delivered_houses = set()   # set of "x,y" keys
        self.revealed_tiles = {"0,0"}
        self.path_history = [(0, 0)]
        self.finished = False
        self.finish_time = None
        self.penalty_count = {"puddle": 0, "broken": 0}
        self.has_boots = False
        self.has_rope = False

        # AI-specific memory
        self.visited_tiles = {"0,0"}
        self.pruned_tiles = set()
        self.memory_visited = {"0,0"}
        self.memory_pruned = set()
        self.goal_idx = 0
        self.step_timer = 0
        self.last_pos = None
        self.stuck_counter = 0
        self.recent_positions = []   # Track last N positions for cycle detection
        self.recent_positions = []   # Track last N positions for cycle detection

    def tiles_in_view(self, difficulty: str) -> set:
        """Get set of 'x,y' keys visible from current position."""
        r = DIFFICULTY_CONFIG[difficulty]["vision_radius"]
        visible = set()
        px, py = self.pos
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = px + dx, py + dy
                if 0 <= x < SIZE and 0 <= y < SIZE:
                    visible.add(f"{x},{y}")
        return visible

    def add_revealed_tiles(self, new_tiles: set):
        """Reveal new tiles and award discovery score."""
        for key in new_tiles:
            if key not in self.revealed_tiles:
                self.revealed_tiles.add(key)
                self.score += SCORE_REVEAL_TILE

    def revert_steps(self, steps: int):
        """Push player back along their path history."""
        hist = self.path_history
        target = max(0, len(hist) - 1 - steps)
        # Remove reverted tiles from visited memory
        for i in range(target + 1, len(hist)):
            key = f"{hist[i][0]},{hist[i][1]}"
            self.memory_visited.discard(key)
        self.pos = hist[target]
        self.path_history = hist[:target + 1]

    def move(self, dx: int, dy: int, game_map: list, difficulty: str, game_state) -> list:
        """
        Attempt to move the player by (dx, dy).
        Returns a list of event dicts for the UI to process.
        """
        if self.finished:
            return []

        events = []
        px, py = self.pos
        nx, ny = px + dx, py + dy

        # Bounds check
        if nx < 0 or nx >= SIZE or ny < 0 or ny >= SIZE:
            return []

        tile_type = game_map[ny][nx]

        # Wall check
        if tile_type == Tile.WALL:
            return []

        # Move
        self.pos = (nx, ny)
        self.path_history.append(self.pos)

        # Reveal tiles
        new_visible = self.tiles_in_view(difficulty)
        self.add_revealed_tiles(new_visible)

        key = f"{nx},{ny}"

        # Obstacle check — puddle
        if tile_type == Tile.PUDDLE and not self.has_boots:
            self.score -= PENALTY_PUDDLE
            self.penalty_count["puddle"] += 1
            self.revert_steps(REVERT_PUDDLE)
            events.append({
                "type": "penalty",
                "msg": "💧 Puddle! -150pts, pushed back 2 steps",
                "log": "You stepped on a puddle! -150pts" if self.is_human else "AI stepped on a puddle! -150pts",
                "log_type": "penalty" if self.is_human else "ai",
            })

        # Obstacle check — broken road
        elif tile_type == Tile.BROKEN and not self.has_rope:
            self.score -= PENALTY_BROKEN
            self.penalty_count["broken"] += 1
            self.revert_steps(REVERT_BROKEN)
            events.append({
                "type": "penalty",
                "msg": "🪨 Broken road! -200pts, pushed back 3 steps",
                "log": "You hit a broken road! -200pts" if self.is_human else "AI hit a broken road! -200pts",
                "log_type": "penalty" if self.is_human else "ai",
            })

        # House delivery
        if tile_type == Tile.HOUSE and key not in self.delivered_houses:
            self.delivered_houses.add(key)
            self.deliveries += 1
            self.score += SCORE_DELIVERY
            who = "You" if self.is_human else "AI"
            events.append({
                "type": "delivery",
                "msg": f"🍪 {'Delivered' if self.is_human else 'AI delivered'}! +800pts ({self.deliveries}/{DELIVERIES_NEEDED})",
                "log": f"{who} delivered a cookie! +800pts ({self.deliveries}/{DELIVERIES_NEEDED})",
                "log_type": "human" if self.is_human else "ai",
            })

            # Bonus item
            chance = BONUS_ITEM_CHANCE_PLAYER if self.is_human else 0.3
            if random.random() < chance:
                if not self.has_boots:
                    self.has_boots = True
                    events.append({
                        "type": "bonus",
                        "msg": "👢 Got Boots! Puddles protected!",
                        "log": f"{who} received Boots!",
                        "log_type": "human" if self.is_human else "ai",
                    })
                elif not self.has_rope:
                    self.has_rope = True
                    events.append({
                        "type": "bonus",
                        "msg": "🪢 Got Rope! Roads protected!",
                        "log": f"{who} received Rope!",
                        "log_type": "human" if self.is_human else "ai",
                    })

        # Exit check
        if tile_type == Tile.EXIT and self.deliveries >= DELIVERIES_NEEDED and not self.finished:
            self.finished = True
            self.finish_time = game_state.get("elapsed", 0)
            who = "🎉 You" if self.is_human else "🤖 AI"
            events.append({
                "type": "finish",
                "msg": f"{who} exited the village!",
                "log": f"{who} exited the village!",
                "log_type": "human" if self.is_human else "ai",
            })

        return events
