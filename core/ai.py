"""
core/ai.py — AI agent with difficulty-based strategies.
Translated from aiStep(), aiGetGoals() in the HTML source.
"""

import random
from setting import SIZE, Tile, DIRS, DIFFICULTY_CONFIG, Difficulty
from utils.helper import manhattan

class AIAgent:
    """Controls the AI player's decision-making each step."""

    def __init__(self, player, game_map: list, houses: list, exit_pos: tuple):
        self.player = player
        self.game_map = game_map
        self.houses = houses
        self.exit_pos = exit_pos
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
        return goals

    def _get_all_neighbors(self, px, py):
        neighbors = []
        for dx, dy in DIRS:
            nx, ny = px + dx, py + dy
            if 0 <= nx < SIZE and 0 <= ny < SIZE and self.game_map[ny][nx] != Tile.WALL:
                neighbors.append((nx, ny))
        return neighbors

    def _detect_cycle(self) -> bool:
        ai = self.player
        if not hasattr(ai, 'recent_positions'):
            ai.recent_positions = []
        
        ai.recent_positions.append(ai.pos)
        if len(ai.recent_positions) > 10:
            ai.recent_positions.pop(0)
            
        recent = ai.recent_positions
        if len(recent) >= 6:
            # Check for 2-step loop: A -> B -> A -> B -> A -> B
            if recent[-1] == recent[-3] == recent[-5] and \
               recent[-2] == recent[-4] == recent[-6]:
                return True
        if len(recent) >= 9:
            # Check for 3-step loop: A -> B -> C -> A -> B -> C
            if recent[-1] == recent[-4] == recent[-7] and \
               recent[-2] == recent[-5] == recent[-8] and \
               recent[-3] == recent[-6] == recent[-9]:
                return True
        return False

    def step(self, difficulty: str, game_state: dict) -> list:
        ai = self.player
        if ai.finished:
            return []

        goals = self.get_goals()
        target = goals[0]
        px, py = ai.pos
        all_neighbors = self._get_all_neighbors(px, py)

        reason = ""
        if self._detect_cycle():
            ai.memory_visited.clear()
            ai.memory_pruned.clear()
            ai.recent_positions.clear()
            ai.stuck_counter = 0

            not_last = [n for n in all_neighbors if n != ai.last_pos]
            pool = not_last if not_last else all_neighbors
            pool.sort(key=lambda n: manhattan(n, target))
            top = pool[:min(2, len(pool))]
            chosen = random.choice(top)
            reason = "Cycle detected! Cleared memory and picked randomly to escape."
        else:
            neighbors = list(all_neighbors)
            if difficulty == Difficulty.HARD:
                safe = [n for n in neighbors
                        if self.game_map[n[1]][n[0]] not in (Tile.PUDDLE, Tile.BROKEN)]
                if safe:
                    neighbors = safe

            available = [n for n in neighbors if f"{n[0]},{n[1]}" not in ai.memory_pruned]
            if not available:
                ai.memory_pruned.clear()
                available = neighbors
            neighbors = available

            sorted_n = sorted(neighbors, key=lambda n: manhattan(n, target))

            if difficulty == Difficulty.EASY:
                if random.random() < 0.3 and sorted_n:
                    sorted_n = [random.choice(sorted_n)]
                    reason = "Stochastic behavior: randomly picked neighbor."
                ai.step_timer += 1
                if ai.step_timer % 10 == 0:
                    ai.memory_pruned.clear()

            last_key = f"{ai.last_pos[0]},{ai.last_pos[1]}" if ai.last_pos else None
            not_last = [n for n in sorted_n if f"{n[0]},{n[1]}" != last_key]
            candidates = not_last if not_last else sorted_n

            unvisited = [n for n in candidates if f"{n[0]},{n[1]}" not in ai.memory_visited]
            if unvisited:
                chosen = unvisited[0]
            elif candidates:
                chosen = candidates[0]
                if difficulty == Difficulty.HARD:
                    ai.memory_pruned.add(f"{px},{py}")
            else:
                return []

            chosen_key = f"{chosen[0]},{chosen[1]}"
            if not reason:
                if chosen_key in ai.memory_visited:
                    reason = "All safe neighbors visited. Backtracking to closest."
                else:
                    reason = "Moved to closest unvisited tile toward goal."

            if chosen_key in ai.memory_visited:
                ai.stuck_counter += 1
                threshold = 20 if difficulty == Difficulty.HARD else 6
                if ai.stuck_counter >= threshold:
                    ai.memory_visited.clear()
                    ai.stuck_counter = 0
                    top = sorted_n[:min(2, len(sorted_n))]
                    chosen = random.choice(top) if top else chosen
                    reason = "Stuck threshold reached! Picked randomly to break loop."
            else:
                ai.stuck_counter = 0

        nx, ny = chosen
        tile_type = self.game_map[ny][nx]

        ai.last_pos = ai.pos
        ai.pos = (nx, ny)
        ai.path_history.append(ai.pos)
        ai.memory_visited.add(f"{nx},{ny}")

        new_visible = ai.tiles_in_view(difficulty)
        ai.add_revealed_tiles(new_visible)

        chosen_key = f"{nx},{ny}"
        state_str = "Backtracking" if chosen_key in ai.memory_visited else "Exploring"
        if "Cycle" in reason or "Stuck" in reason:
            state_str = "Escaping Loop"

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

        if tile_type == Tile.PUDDLE and not ai.has_boots:
            ai.score -= 150
            ai.penalty_count["puddle"] += 1
            ai.memory_pruned.add(key)
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
                "msg": "🤖 AI puddle! -150pts",
                "log": "AI stepped on a puddle! -150pts",
                "log_type": "ai",
            })

        elif tile_type == Tile.BROKEN and not ai.has_rope:
            ai.score -= 200
            ai.penalty_count["broken"] += 1
            ai.memory_pruned.add(key)
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
                "msg": "🤖 AI broken road! -200pts",
                "log": "AI hit a broken road! -200pts",
                "log_type": "ai",
            })

        if tile_type == Tile.HOUSE and key not in ai.delivered_houses:
            ai.delivered_houses.add(key)
            ai.deliveries += 1
            ai.score += 800
            events.append({
                "type": "delivery",
                "msg": f"🤖 AI delivered! ({ai.deliveries}/3)",
                "log": f"AI delivered cookie! +800pts ({ai.deliveries}/3)",
                "log_type": "ai",
            })
            if random.random() < 0.3:
                if not ai.has_boots:
                    ai.has_boots = True
                elif not ai.has_rope:
                    ai.has_rope = True

        if tile_type == Tile.EXIT and ai.deliveries >= 3 and not ai.finished:
            ai.finished = True
            ai.finish_time = game_state.get("elapsed", 0)
            events.append({
                "type": "finish",
                "msg": "🤖 AI exited the village!",
                "log": "🤖 AI exited the village!",
                "log_type": "ai",
            })

        return events
