"""
core/ai.py — AI agent with difficulty-based strategies.
Two-mode architecture: Normal greedy exploration + BFS fallback when stuck.
"""

import random
from collections import deque
from setting import SIZE, Tile, DIRS, DIFFICULTY_CONFIG, Difficulty
from utils.helper import manhattan


class AIAgent:
    """Controls the AI player's decision-making each step."""

    def __init__(self, player, game_map: list, houses: list, exit_pos: tuple):
        self.player = player
        self.game_map = game_map
        self.houses = houses
        self.exit_pos = exit_pos
        self._bfs_path = []          # Pre-computed BFS path to follow
        self._no_progress_count = 0  # Steps without getting closer to goal
        self._best_dist = None       # Best distance achieved to current goal
        self.replay_log = [{
            'pos': player.pos,
            'reason': 'Started at spawn.',
            'visited': set(),
            'pruned': set(),
            'target': self.exit_pos,
            'h_n': manhattan(player.pos, self.exit_pos),
            'stuck_counter': 0,
            'state': 'Started'
        }]

    def get_goals(self) -> list:
        ai = self.player
        goals = []
        for h in self.houses:
            key = f"{h[0]},{h[1]}"
            if key not in ai.delivered_houses:
                goals.append(h)
        if not goals:
            goals.append(self.exit_pos)
        else:
            # Sort remaining houses by distance to current position to avoid skipping nearby ones
            goals.sort(key=lambda h: manhattan(ai.pos, h))
        return goals

    def _get_all_neighbors(self, px, py):
        neighbors = []
        for dx, dy in DIRS:
            nx, ny = px + dx, py + dy
            if 0 <= nx < SIZE and 0 <= ny < SIZE and self.game_map[ny][nx] != Tile.WALL:
                neighbors.append((nx, ny))
        return neighbors

    def _bfs_path_to(self, start, target):
        """BFS from start to target. Returns full path (list of positions).
        Tries safe path first (avoids hazards), falls back to any path."""
        ai = self.player
        hazards = set()
        if not ai.has_boots:
            hazards.add(Tile.PUDDLE)
        if not ai.has_rope:
            hazards.add(Tile.BROKEN)

        known = getattr(ai, 'known_hazards', set())

        for avoid_hazards in [True, False]:
            visited = {start}
            queue = deque([(start, [start])])
            while queue:
                pos, path = queue.popleft()
                if pos == target:
                    return path[1:]  # Exclude start position
                for dx, dy in DIRS:
                    nx, ny = pos[0] + dx, pos[1] + dy
                    if 0 <= nx < SIZE and 0 <= ny < SIZE and (nx, ny) not in visited:
                        tile = self.game_map[ny][nx]
                        if tile == Tile.WALL:
                            continue

                        if avoid_hazards:
                            if f"{nx},{ny}" in known or tile in hazards:
                                continue

                        visited.add((nx, ny))
                        queue.append(((nx, ny), path + [(nx, ny)]))
        return []

    def _greedy_step(self, difficulty, target, all_neighbors):
        """Normal greedy exploration. Returns (chosen_pos, reason)."""
        ai = self.player
        px, py = ai.pos
        neighbors = list(all_neighbors)

        # Hard mode: avoid hazards if possible
        if difficulty == Difficulty.HARD:
            safe = [n for n in neighbors
                    if self.game_map[n[1]][n[0]] not in (Tile.PUDDLE, Tile.BROKEN)]
            if safe:
                neighbors = safe

        known = getattr(ai, 'known_hazards', set())
        available = [n for n in neighbors if f"{n[0]},{n[1]}" not in ai.memory_pruned and f"{n[0]},{n[1]}" not in known]

        if not available:
            ai.memory_pruned.clear()
            # Try again, but STILL avoid permanent hazards
            available = [n for n in neighbors if f"{n[0]},{n[1]}" not in known]
            if not available:
                available = neighbors
        neighbors = available

        # Sort by distance to target
        sorted_n = sorted(neighbors, key=lambda n: manhattan(n, target))

        reason = ""

        if difficulty == Difficulty.EASY and random.random() < 0.3 and neighbors:
            chosen = random.choice(neighbors)
            reason = "Stochastic behavior: randomly picked neighbor."
            return chosen, reason

        # Prefer not going back to last position
        last_key = f"{ai.last_pos[0]},{ai.last_pos[1]}" if ai.last_pos else None
        not_last = [n for n in sorted_n if f"{n[0]},{n[1]}" != last_key]
        candidates = not_last if not_last else sorted_n

        # Prefer unvisited tiles
        unvisited = [n for n in candidates if f"{n[0]},{n[1]}" not in ai.memory_visited]
        if unvisited:
            chosen = unvisited[0]
            if not reason:
                reason = "Moved to closest unvisited tile toward goal."
        elif candidates:
            chosen = candidates[0]
            ai.memory_pruned.add(f"{px},{py}")
            if not reason:
                reason = "All neighbors visited. Backtracking toward goal."
        else:
            sorted_n = sorted(all_neighbors, key=lambda n: manhattan(n, target))
            chosen = sorted_n[0]
            if not reason:
                reason = "Fallback: moved toward goal."

        return chosen, reason

    def step(self, difficulty: str, game_state: dict) -> list:
        ai = self.player
        if ai.finished:
            return []
        
        if not hasattr(ai, 'known_hazards'):
            ai.known_hazards = set()

        goals = self.get_goals()
        prev = getattr(self, '_prev_target', None)
        if prev in goals:
            target = prev
        else:
            target = goals[0] # Pick the closest house to start
        
        # If the target changed (because we just delivered a cookie to the old one)
        if prev != target:
            self._best_dist = None
            self._no_progress_count = 0
            self._bfs_path.clear()
            ai.memory_visited.clear()
            ai.memory_pruned.clear()
            
            self._prev_target = target

        ai.step_timer += 1
        if difficulty == Difficulty.EASY and ai.step_timer % 10 == 0:
            ai.memory_pruned.clear()

        px, py = ai.pos
        all_neighbors = self._get_all_neighbors(px, py)

        if not all_neighbors:
            return []

        # Track progress toward the goal
        current_dist = manhattan(ai.pos, target)
        if self._best_dist is None or current_dist < self._best_dist:
            self._best_dist = current_dist
            self._no_progress_count = 0
        else:
            self._no_progress_count += 1

        # Decide: use greedy exploration or BFS fallback
        # Easy mode triggers BFS sooner since randomness causes more wandering
        bfs_threshold = 15 if difficulty == Difficulty.EASY else 20
        use_bfs = self._no_progress_count >= bfs_threshold

        if use_bfs or self._bfs_path:
            # Compute or follow BFS path
            if not self._bfs_path:
                self._bfs_path = self._bfs_path_to(ai.pos, target)

            if self._bfs_path:
                chosen = self._bfs_path.pop(0)
                # Validate the BFS step is still reachable
                if chosen not in all_neighbors:
                    # Path got invalidated (revert?), recompute
                    self._bfs_path = self._bfs_path_to(ai.pos, target)
                    if self._bfs_path:
                        chosen = self._bfs_path.pop(0)
                    else:
                        chosen, reason = self._greedy_step(difficulty, target, all_neighbors)
                        reason = "BFS failed, greedy fallback."
                    reason = "Following BFS path toward goal."
                else:
                    reason = "Following BFS path toward goal."
            else:
                # BFS couldn't find a path — use greedy
                chosen, reason = self._greedy_step(difficulty, target, all_neighbors)
                reason = "No BFS path found, using greedy."
        else:
            # Normal greedy exploration
            chosen, reason = self._greedy_step(difficulty, target, all_neighbors)

            # Track stuck counter for visited tiles
            chosen_key = f"{chosen[0]},{chosen[1]}"
            if chosen_key in ai.memory_visited:
                ai.stuck_counter += 1
                threshold = 15 if difficulty == Difficulty.HARD else 8
                if ai.stuck_counter >= threshold:
                    ai.memory_pruned.clear()
                    ai.memory_visited.clear()
                    ai.stuck_counter = 0
                    # Force BFS on next step
                    self._no_progress_count = 999
                    reason = "Stuck! Will use BFS next step."
            else:
                ai.stuck_counter = 0

        # Handle failsafe cooldown
        if getattr(self, '_failsafe_cooldown', 0) > 0:
            self._failsafe_cooldown -= 1

        # Anti-oscillation failsafe (uses replay_log because path_history truncates on hazards)
        elif len(self.replay_log) >= 8:
            recent_positions = [entry['pos'] for entry in self.replay_log[-8:]]
            if len(set(recent_positions)) <= 4:
                # The AI has been bouncing in a small loop for 8 steps.
                # Force a random move to break the loop!
                unvisited = [n for n in all_neighbors if n not in set(recent_positions)]
                if unvisited:
                    chosen = random.choice(unvisited)
                else:
                    chosen = random.choice(all_neighbors)
                ai.memory_pruned.clear()
                ai.memory_visited.clear()
                self._bfs_path.clear()
                self._no_progress_count = 999  # Force BFS after jumping out
                self._failsafe_cooldown = 8    # Don't trigger failsafe again for 8 steps!
                reason = "Failsafe: Broke out of oscillation loop."

        nx, ny = chosen
        tile_type = self.game_map[ny][nx]

        # Record state
        chosen_key = f"{nx},{ny}"
        was_visited = chosen_key in ai.memory_visited
        state_str = "BFS Path" if use_bfs or self._bfs_path else ("Backtracking" if was_visited else "Exploring")

        # Update position and memory
        ai.last_pos = ai.pos
        ai.pos = (nx, ny)
        ai.path_history.append(ai.pos)
        ai.memory_visited.add(chosen_key)

        new_visible = ai.tiles_in_view(difficulty)
        ai.add_revealed_tiles(new_visible)

        self.replay_log.append({
            'pos': ai.pos,
            'reason': reason,
            'visited': set(ai.memory_visited),
            'pruned': set(ai.memory_pruned),
            'target': target,
            'h_n': manhattan(ai.pos, target),
            'stuck_counter': ai.stuck_counter,
            'state': state_str
        })

        key = f"{nx},{ny}"
        events = []

        if tile_type == Tile.PUDDLE:
            if ai.has_boots:
                ai.boots_durability -= 1
                if ai.boots_durability <= 0:
                    ai.boots_durability = 0
                    events.append({
                        "type": "penalty",
                        "msg": "AI's boots broke!",
                        "log": "AI's boots broke!",
                        "log_type": "ai",
                    })
            else:
                ai.score -= 150
                ai.penalty_count["puddle"] += 1
                ai.memory_pruned.add(key)
                ai.known_hazards.add(key)
                self._bfs_path.clear()  # Invalidate BFS path after revert
                ai.revert_steps(2)
                self.replay_log.append({
                    'pos': ai.pos,
                    'reason': "Hit a puddle! Pushed back 2 steps.",
                    'visited': set(ai.memory_visited),
                    'pruned': set(ai.memory_pruned),
                    'target': target,
                    'h_n': manhattan(ai.pos, target),
                    'stuck_counter': ai.stuck_counter,
                    'state': 'Penalty (Puddle)'
                })
                events.append({
                    "type": "penalty",
                    "msg": "AI puddle! -150pts",
                    "log": "AI stepped on a puddle! -150pts",
                    "log_type": "ai",
                })

        elif tile_type == Tile.BROKEN:
            if ai.has_rope:
                ai.rope_durability -= 1
                if ai.rope_durability <= 0:
                    ai.rope_durability = 0
                    events.append({
                        "type": "penalty",
                        "msg": "AI's rope broke!",
                        "log": "AI's rope broke!",
                        "log_type": "ai",
                    })
            else:
                ai.score -= 200
                ai.penalty_count["broken"] += 1
                ai.memory_pruned.add(key)
                ai.known_hazards.add(key)
                self._bfs_path.clear()  # Invalidate BFS path after revert
                ai.revert_steps(3)
                self.replay_log.append({
                    'pos': ai.pos,
                    'reason': "Hit a broken road! Pushed back 3 steps.",
                    'visited': set(ai.memory_visited),
                    'pruned': set(ai.memory_pruned),
                    'target': target,
                    'h_n': manhattan(ai.pos, target),
                    'stuck_counter': ai.stuck_counter,
                    'state': 'Penalty (Broken Road)'
                })
                events.append({
                    "type": "penalty",
                    "msg": "AI broken road! -200pts",
                    "log": "AI hit a broken road! -200pts",
                    "log_type": "ai",
                })

        # After penalty/revert, update progress tracking
        new_dist = manhattan(ai.pos, target)
        if new_dist < self._best_dist:
            self._best_dist = new_dist
            self._no_progress_count = 0

        if tile_type == Tile.HOUSE and key not in ai.delivered_houses:
            ai.delivered_houses.add(key)
            ai.deliveries += 1
            ai.score += 800
            # Reset progress tracking for new goal
            self._best_dist = None
            self._no_progress_count = 0
            self._bfs_path.clear()
            ai.memory_visited.clear()
            ai.memory_pruned.clear()
            events.append({
                "type": "delivery",
                "msg": f"AI delivered! ({ai.deliveries}/3)",
                "log": f"AI delivered cookie! +800pts ({ai.deliveries}/3)",
                "log_type": "ai",
            })
            if random.random() < 0.5:
                item = random.choice(["boots", "rope"])
                if item == "boots":
                    ai.boots_durability = DIFFICULTY_CONFIG[difficulty]["boots_durability"]
                    events.append({
                        "type": "bonus",
                        "msg": "Got Boots! Puddles protected!",
                        "log": "AI received Boots!",
                        "log_type": "ai",
                    })
                elif item == "rope":
                    ai.rope_durability = DIFFICULTY_CONFIG[difficulty]["rope_durability"]
                    events.append({
                        "type": "bonus",
                        "msg": "Got Rope! Roads protected!",
                        "log": "AI received Rope!",
                        "log_type": "ai",
                    })

        if tile_type == Tile.EXIT and ai.deliveries >= 3 and not ai.finished:
            ai.finished = True
            ai.finish_time = game_state.get("elapsed", 0)
            events.append({
                "type": "finish",
                "msg": "AI exited the village!",
                "log": "AI exited the village!",
                "log_type": "ai",
            })

        return events
