"""
core/map_gen.py — Map generation with obstacle placement and BFS validation.
Translated from makeGrid(), generateMap(), getNeighbors(), bfsReachable() in the HTML.
"""

import random
from setting import (
    SIZE, Tile, DIRS,
    HOUSE_POSITIONS, EXIT_POSITION, START_POSITION,
    PUDDLE_CHANCE, BROKEN_CHANCE,
)


def make_grid() -> list:
    """Create an empty SIZE×SIZE grid filled with EMPTY tiles."""
    return [[Tile.EMPTY for _ in range(SIZE)] for _ in range(SIZE)]


def get_neighbors(grid: list, x: int, y: int) -> list:
    """Get walkable neighbor positions (not walls/puddles/broken, within bounds)."""
    result = []
    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < SIZE and 0 <= ny < SIZE and grid[ny][nx] not in (Tile.WALL, Tile.PUDDLE, Tile.BROKEN):
            result.append((nx, ny))
    return result


def bfs_reachable(grid: list, start: tuple, targets: list) -> bool:
    """BFS from start to check if ALL targets are reachable."""
    visited = {start}
    queue = [start]
    found = set()
    target_set = {t for t in targets}

    while queue:
        cur = queue.pop(0)
        if cur in target_set:
            found.add(cur)
        for nb in get_neighbors(grid, cur[0], cur[1]):
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)

    return all(t in found for t in targets)


def generate_map() -> dict:
    """
    Generate a valid game map with obstacles, houses, and exit.
    Retries until BFS confirms all targets are reachable from start.
    Returns dict with 'grid', 'houses', 'exit_pos'.
    """
    for _ in range(100):
        grid = make_grid()

        # Place random obstacles (~13% puddle, ~9% broken)
        for y in range(SIZE):
            for x in range(SIZE):
                r = random.random()
                if r < PUDDLE_CHANCE:
                    grid[y][x] = Tile.PUDDLE
                elif r < PUDDLE_CHANCE + BROKEN_CHANCE:
                    grid[y][x] = Tile.BROKEN

        # Clear start area
        sx, sy = START_POSITION
        grid[sy][sx] = Tile.START
        # Clear adjacent tiles to start
        if sx + 1 < SIZE:
            grid[sy][sx + 1] = Tile.EMPTY
        if sy + 1 < SIZE:
            grid[sy + 1][sx] = Tile.EMPTY

        # Place houses
        houses = []
        for hx, hy in HOUSE_POSITIONS:
            grid[hy][hx] = Tile.HOUSE
            houses.append((hx, hy))

        # Place exit
        ex, ey = EXIT_POSITION
        grid[ey][ex] = Tile.EXIT

        # Validate: BFS must reach all houses + exit from start
        all_targets = houses + [EXIT_POSITION]
        if bfs_reachable(grid, START_POSITION, all_targets):
            return {
                "grid": grid,
                "houses": houses,
                "exit_pos": EXIT_POSITION,
            }

    # Fallback: return last generated map even if not fully reachable
    return {
        "grid": grid,
        "houses": houses,
        "exit_pos": EXIT_POSITION,
    }
