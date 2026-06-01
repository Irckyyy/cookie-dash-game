"""
core/ai.py — AI agent with difficulty-based navigation strategies.

Three clearly separated algorithms based on difficulty:
  - Easy   : Stochastic Search with Memory Decay
  - Medium : Deterministic Greedy Search with Persistent Pruning
  - Hard   : Lookahead DFS with Predictive Pruning

All three share a BFS fallback when the agent gets stuck,
and a BFS map validation utility used during map generation.
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
        self._bfs_path = []          # Pre-computed BFS path when agent is stuck
        self._no_progress_count = 0  # Steps without getting closer to goal
        self._best_dist = None       # Best Manhattan distance achieved to current goal
        self._prev_target = None
        self._failsafe_cooldown = 0
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

    # =========================================================================
    # GOAL MANAGEMENT
    # =========================================================================

    def get_goals(self) -> list:
        """Return remaining delivery targets, sorted by proximity."""
        ai = self.player
        goals = []
        for h in self.houses:
            key = f"{h[0]},{h[1]}"
            if key not in ai.delivered_houses:
                goals.append(h)
        if not goals:
            goals.append(self.exit_pos)
        else:
            goals.sort(key=lambda h: manhattan(ai.pos, h))
        return goals

    # =========================================================================
    # SHARED UTILITIES
    # =========================================================================

    def _get_all_neighbors(self, px, py) -> list:
        """Return all walkable neighbors of (px, py)."""
        neighbors = []
        for dx, dy in DIRS:
            nx, ny = px + dx, py + dy
            if 0 <= nx < SIZE and 0 <= ny < SIZE and self.game_map[ny][nx] != Tile.WALL:
                neighbors.append((nx, ny))
        return neighbors

    def _filter_known_hazards(self, neighbors) -> list:
        """Remove tiles the AI already knows are hazards."""
        ai = self.player
        known = getattr(ai, 'known_hazards', set())
        safe = [n for n in neighbors if f"{n[0]},{n[1]}" not in known]
        return safe if safe else neighbors

    def _prefer_unvisited(self, candidates) -> list:
        """Sort candidates: unvisited tiles first, then by insertion order."""
        ai = self.player
        unvisited = [n for n in candidates if f"{n[0]},{n[1]}" not in ai.memory_visited]
        return unvisited if unvisited else candidates

    def _avoid_last_pos(self, candidates) -> list:
        """Prefer not backtracking to the immediately previous position."""
        ai = self.player
        if not ai.last_pos:
            return candidates
        last_key = f"{ai.last_pos[0]},{ai.last_pos[1]}"
        forward = [n for n in candidates if f"{n[0]},{n[1]}" != last_key]
        return forward if forward else candidates

    # =========================================================================
    # ALGORITHM 1 — EASY: Stochastic Search with Memory Decay
    # =========================================================================
    # The AI has a 30% chance each step of ignoring the heuristic and picking
    # a random neighbor. It also forgets known hazard locations every 10 steps
    # (memory decay), causing it to potentially repeat past mistakes.
    # This simulates an inexperienced, forgetful navigator.
    # =========================================================================

    def _stochastic_search(self, target, all_neighbors) -> tuple:
        """
        Easy difficulty algorithm.
        Stochastic Search: 30% random move + periodic memory decay.
        """
        ai = self.player
        px, py = ai.pos

        neighbors = self._filter_known_hazards(all_neighbors)
        available = [n for n in neighbors if f"{n[0]},{n[1]}" not in ai.memory_pruned]
        if not available:
            ai.memory_pruned.clear()
            available = neighbors

        # --- Memory Decay ---
        # Every 10 steps, forget known hazard positions.
        # The AI may walk into the same puddle or hole again.
        if ai.step_timer % 10 == 0:
            ai.memory_pruned.clear()

        # --- Stochastic Step ---
        # 30% chance: ignore the heuristic, pick a random neighbor.
        if random.random() < 0.3:
            chosen = random.choice(available)
            return chosen, "Stochastic: randomly picked a neighbor (30% chance)."

        # Otherwise: greedy toward target, prefer unvisited
        sorted_n = sorted(available, key=lambda n: manhattan(n, target))
        candidates = self._avoid_last_pos(sorted_n)
        candidates = self._prefer_unvisited(candidates)

        if candidates:
            chosen = candidates[0]
            return chosen, "Stochastic: greedy step toward goal."

        # Fallback
        chosen = sorted(all_neighbors, key=lambda n: manhattan(n, target))[0]
        return chosen, "Stochastic: fallback to closest neighbor."

    # =========================================================================
    # ALGORITHM 2 — MEDIUM: Deterministic Greedy Search
    # =========================================================================
    # The AI always picks the neighbor with the lowest Manhattan distance to
    # the target — no randomness. Once a tile is pruned (found to be a hazard
    # or a dead end), it is permanently blocked for the rest of the match.
    # This simulates a consistent, memory-persistent navigator.
    # =========================================================================

    def _deterministic_greedy(self, target, all_neighbors) -> tuple:
        """
        Medium difficulty algorithm.
        Deterministic Greedy Search with Persistent Pruning.
        Manhattan distance heuristic: h(n) = |x1-x2| + |y1-y2|
        """
        ai = self.player
        px, py = ai.pos

        neighbors = self._filter_known_hazards(all_neighbors)

        # --- Persistent Pruning ---
        # Pruned tiles are NEVER cleared mid-game for Medium difficulty.
        # Once a hazard or dead end is discovered, it stays blocked.
        available = [n for n in neighbors if f"{n[0]},{n[1]}" not in ai.memory_pruned]
        if not available:
            # All safe neighbors are pruned — only then do we fall back
            available = neighbors

        # --- Deterministic Greedy Step ---
        # Sort strictly by Manhattan distance. No randomness.
        sorted_n = sorted(available, key=lambda n: manhattan(n, target))
        candidates = self._avoid_last_pos(sorted_n)
        candidates = self._prefer_unvisited(candidates)

        if candidates:
            chosen = candidates[0]
            h_n = manhattan(chosen, target)
            return chosen, f"Greedy: picked tile with h(n)={h_n} (Manhattan distance)."

        # All candidates visited — mark current tile as pruned and backtrack
        ai.memory_pruned.add(f"{px},{py}")
        chosen = sorted_n[0]
        return chosen, "Greedy: backtracking — all neighbors visited, current tile pruned."

    # =========================================================================
    # ALGORITHM 3 — HARD: Lookahead DFS with Predictive Pruning
    # =========================================================================
    # Before moving to any tile, the AI scans its neighbors for hazards.
    # If a hazard is detected in the immediate surroundings, the tile is pruned
    # BEFORE the AI steps on it — no penalty incurred. This simulates a highly
    # cautious navigator that avoids danger proactively rather than reactively.
    # =========================================================================

    def _lookahead_dfs(self, target, all_neighbors) -> tuple:
        """
        Hard difficulty algorithm.
        Lookahead DFS with Predictive Pruning.
        Scans neighbors of neighbors to detect hazards before stepping.
        """
        ai = self.player
        px, py = ai.pos

        neighbors = self._filter_known_hazards(all_neighbors)
        available = [n for n in neighbors if f"{n[0]},{n[1]}" not in ai.memory_pruned]
        if not available:
            ai.memory_pruned.clear()
            available = neighbors

        # --- Predictive Pruning (Lookahead) ---
        # Before committing to a tile, scan its tile type directly.
        # If it is a hazard, prune it preemptively without stepping on it.
        safe_from_lookahead = []
        for n in available:
            nx, ny = n
            tile = self.game_map[ny][nx]
            if tile in (Tile.PUDDLE, Tile.BROKEN):
                # Detected hazard ahead — prune without penalty
                ai.memory_pruned.add(f"{nx},{ny}")
                ai.known_hazards.add(f"{nx},{ny}")
            else:
                safe_from_lookahead.append(n)

        candidates = safe_from_lookahead if safe_from_lookahead else available

        # --- DFS-style: prefer unvisited, greedy toward target ---
        sorted_n = sorted(candidates, key=lambda n: manhattan(n, target))
        candidates = self._avoid_last_pos(sorted_n)
        candidates = self._prefer_unvisited(candidates)

        if candidates:
            chosen = candidates[0]
            h_n = manhattan(chosen, target)
            return chosen, f"Lookahead DFS: predictive pruning applied, h(n)={h_n}."

        # Fallback if all neighbors are hazards or pruned
        chosen = sorted(all_neighbors, key=lambda n: manhattan(n, target))[0]
        return chosen, "Lookahead DFS: all safe tiles exhausted, forced move."

    # =========================================================================
    # BFS FALLBACK — used by all difficulty modes when stuck
    # =========================================================================
    # When the AI makes no progress toward its goal for too many steps,
    # it switches to BFS to guarantee it finds a path if one exists.
    # BFS has full map knowledge here — it is a recovery mechanism, not
    # the primary navigation strategy.
    # =========================================================================

    def _bfs_path_to(self, start, target) -> list:
        """
        BFS from start to target.
        Tries a hazard-avoiding path first; falls back to any valid path.
        Returns list of positions (excluding start).
        """
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
                    return path[1:]
                for dx, dy in DIRS:
                    nx, ny = pos[0] + dx, pos[1] + dy
                    if 0 <= nx < SIZE and 0 <= ny < SIZE and (nx, ny) not in visited:
                        tile = self.game_map[ny][nx]
                        if tile == Tile.WALL:
                            continue
                        if avoid_hazards and (f"{nx},{ny}" in known or tile in hazards):
                            continue
                        visited.add((nx, ny))
                        queue.append(((nx, ny), path + [(nx, ny)]))
        return []

    # =========================================================================
    # MAIN STEP — called every AI tick
    # =========================================================================

    def step(self, difficulty: str, game_state: dict) -> list:
        ai = self.player
        if ai.finished:
            return []

        if not hasattr(ai, 'known_hazards'):
            ai.known_hazards = set()

        # --- Determine current goal ---
        goals = self.get_goals()
        prev = self._prev_target
        target = prev if prev in goals else goals[0]

        # Reset memory when target changes (new delivery made)
        if prev != target:
            self._best_dist = None
            self._no_progress_count = 0
            self._bfs_path.clear()
            ai.memory_visited.clear()
            ai.memory_pruned.clear()
            self._prev_target = target

        ai.step_timer += 1
        px, py = ai.pos
        all_neighbors = self._get_all_neighbors(px, py)

        if not all_neighbors:
            return []

        # --- Track progress toward goal ---
        current_dist = manhattan(ai.pos, target)
        if self._best_dist is None or current_dist < self._best_dist:
            self._best_dist = current_dist
            self._no_progress_count = 0
        else:
            self._no_progress_count += 1

        # --- Choose: BFS fallback or difficulty algorithm ---
        bfs_threshold = 15 if difficulty == Difficulty.EASY else 20
        use_bfs = self._no_progress_count >= bfs_threshold

        if use_bfs or self._bfs_path:
            if not self._bfs_path:
                self._bfs_path = self._bfs_path_to(ai.pos, target)
            if self._bfs_path:
                chosen = self._bfs_path.pop(0)
                if chosen not in all_neighbors:
                    self._bfs_path = self._bfs_path_to(ai.pos, target)
                    if self._bfs_path:
                        chosen = self._bfs_path.pop(0)
                    else:
                        chosen, _ = self._route(difficulty, target, all_neighbors)
                reason = "BFS fallback: following guaranteed path to goal."
            else:
                chosen, reason = self._route(difficulty, target, all_neighbors)
                reason = "BFS fallback failed — reverting to primary algorithm."
        else:
            chosen, reason = self._route(difficulty, target, all_neighbors)

            # Stuck detection — force BFS if revisiting too often
            chosen_key = f"{chosen[0]},{chosen[1]}"
            if chosen_key in ai.memory_visited:
                ai.stuck_counter += 1
                threshold = 15 if difficulty == Difficulty.HARD else 8
                if ai.stuck_counter >= threshold:
                    ai.memory_pruned.clear()
                    ai.memory_visited.clear()
                    ai.stuck_counter = 0
                    self._no_progress_count = 999
                    reason = "Stuck detected — forcing BFS on next step."
            else:
                ai.stuck_counter = 0

        # --- Anti-oscillation failsafe ---
        if self._failsafe_cooldown > 0:
            self._failsafe_cooldown -= 1
        elif len(self.replay_log) >= 8:
            recent_positions = [entry['pos'] for entry in self.replay_log[-8:]]
            if len(set(recent_positions)) <= 4:
                unvisited = [n for n in all_neighbors if n not in set(recent_positions)]
                chosen = random.choice(unvisited) if unvisited else random.choice(all_neighbors)
                ai.memory_pruned.clear()
                ai.memory_visited.clear()
                self._bfs_path.clear()
                self._no_progress_count = 999
                self._failsafe_cooldown = 8
                reason = "Failsafe: broke out of oscillation loop."

        # --- Execute move ---
        nx, ny = chosen
        tile_type = self.game_map[ny][nx]
        chosen_key = f"{nx},{ny}"
        was_visited = chosen_key in ai.memory_visited
        state_str = "BFS Fallback" if (use_bfs or self._bfs_path) else (
            "Backtracking" if was_visited else "Exploring"
        )

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

        # --- Handle tile events ---
        events = []
        key = f"{nx},{ny}"

        if tile_type == Tile.PUDDLE:
            ai.known_hazards.add(key)
            if ai.has_boots:
                ai.boots_durability -= 1
                if ai.boots_durability <= 0:
                    ai.boots_durability = 0
                    events.append({"type": "penalty", "msg": "AI's boots broke!", "log": "AI's boots broke!", "log_type": "ai"})
            else:
                ai.score -= 150
                ai.penalty_count["puddle"] += 1
                ai.memory_pruned.add(key)
                self._bfs_path.clear()
                ai.revert_steps(2, game_state.get("safe_tiles"))
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
                events.append({"type": "penalty", "msg": "AI puddle! -150pts", "log": "AI stepped on a puddle! -150pts", "log_type": "ai"})

        elif tile_type == Tile.BROKEN:
            ai.known_hazards.add(key)
            if ai.has_rope:
                ai.rope_durability -= 1
                if ai.rope_durability <= 0:
                    ai.rope_durability = 0
                    events.append({"type": "penalty", "msg": "AI's rope broke!", "log": "AI's rope broke!", "log_type": "ai"})
            else:
                ai.score -= 200
                ai.penalty_count["broken"] += 1
                ai.memory_pruned.add(key)
                self._bfs_path.clear()
                ai.revert_steps(3, game_state.get("safe_tiles"))
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
                events.append({"type": "penalty", "msg": "AI broken road! -200pts", "log": "AI hit a broken road! -200pts", "log_type": "ai"})

        # Update progress after any revert
        new_dist = manhattan(ai.pos, target)
        if new_dist < self._best_dist:
            self._best_dist = new_dist
            self._no_progress_count = 0

        if tile_type == Tile.HOUSE and key not in ai.delivered_houses:
            ai.delivered_houses.add(key)
            ai.deliveries += 1
            ai.score += 800
            self._best_dist = None
            self._no_progress_count = 0
            self._bfs_path.clear()
            ai.memory_visited.clear()
            ai.memory_pruned.clear()
            events.append({"type": "delivery", "msg": f"AI delivered! ({ai.deliveries}/3)", "log": f"AI delivered cookie! +800pts ({ai.deliveries}/3)", "log_type": "ai"})
            item = random.choice(["boots", "rope"])
            if item == "boots":
                ai.boots_durability = DIFFICULTY_CONFIG[difficulty]["boots_durability"]
                events.append({"type": "bonus", "msg": "Got Boots! Puddles protected!", "log": "AI received Boots!", "log_type": "ai"})
            else:
                ai.rope_durability = DIFFICULTY_CONFIG[difficulty]["rope_durability"]
                events.append({"type": "bonus", "msg": "Got Rope! Roads protected!", "log": "AI received Rope!", "log_type": "ai"})

        if tile_type == Tile.EXIT and ai.deliveries >= 3 and not ai.finished:
            ai.finished = True
            ai.finish_time = game_state.get("elapsed", 0)
            events.append({"type": "finish", "msg": "AI exited the village!", "log": "AI exited the village!", "log_type": "ai"})

        return events

    # =========================================================================
    # INTERNAL ROUTER — dispatches to the correct algorithm by difficulty
    # =========================================================================

    def _route(self, difficulty, target, all_neighbors) -> tuple:
        """Dispatch to the correct algorithm based on difficulty."""
        if difficulty == Difficulty.EASY:
            return self._stochastic_search(target, all_neighbors)
        elif difficulty == Difficulty.MEDIUM:
            return self._deterministic_greedy(target, all_neighbors)
        else:
            return self._lookahead_dfs(target, all_neighbors)
