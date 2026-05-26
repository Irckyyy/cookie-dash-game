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


def bfs_reachable_traced(grid: list, start: tuple, targets: list):
    """BFS with full trace recording for visualization.
    Returns (reachable: bool, trace: list of dicts).
    Each trace entry records: step number, current tile, frontier, visited set,
    and any targets found at that step."""
    visited = {start}
    queue = [start]
    found = set()
    target_set = set(targets)
    trace = []
    step = 0

    # Record initial state
    trace.append({
        'step': step,
        'current': start,
        'frontier': list(queue),
        'visited': set(visited),
        'found': set(found),
        'found_this_step': None,
    })

    while queue:
        cur = queue.pop(0)
        step += 1
        found_now = None

        if cur in target_set and cur not in found:
            found.add(cur)
            found_now = cur

        new_neighbors = []
        for nb in get_neighbors(grid, cur[0], cur[1]):
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
                new_neighbors.append(nb)

        trace.append({
            'step': step,
            'current': cur,
            'frontier': list(queue[:]),
            'visited': set(visited),
            'found': set(found),
            'found_this_step': found_now,
            'new_neighbors': new_neighbors,
        })

    return all(t in found for t in targets), trace


def generate_map() -> dict:
    """
    Generate a valid game map with obstacles, houses, and exit.
    Retries until BFS confirms all targets are reachable from start.
    Returns dict with 'grid', 'houses', 'start_pos', 'exit_pos', 'bfs_trace'.
    """
    for _ in range(100):
        grid = make_grid()

        # Generate all coordinates and shuffle them
        all_coords = [(x, y) for x in range(SIZE) for y in range(SIZE)]
        random.shuffle(all_coords)

        # Pick critical locations so they never overlap
        start_pos = all_coords.pop()
        exit_pos = all_coords.pop()
        houses = [all_coords.pop() for _ in range(3)]

        # Place start, exit, houses
        sx, sy = start_pos
        grid[sy][sx] = Tile.START
        
        ex, ey = exit_pos
        grid[ey][ex] = Tile.EXIT

        for hx, hy in houses:
            grid[hy][hx] = Tile.HOUSE

        # Clear adjacent tiles to start to give the player some breathing room
        for dx, dy in DIRS:
            nx, ny = sx + dx, sy + dy
            if 0 <= nx < SIZE and 0 <= ny < SIZE and (nx, ny) in all_coords:
                all_coords.remove((nx, ny))

        # Place random obstacles in the remaining empty coordinates
        for x, y in all_coords:
            r = random.random()
            if r < PUDDLE_CHANCE:
                grid[y][x] = Tile.PUDDLE
            elif r < PUDDLE_CHANCE + BROKEN_CHANCE:
                grid[y][x] = Tile.BROKEN

        # Validate: BFS must reach all houses + exit from start
        all_targets = houses + [exit_pos]
        reachable, bfs_trace = bfs_reachable_traced(grid, start_pos, all_targets)
        if reachable:
            return {
                "grid": grid,
                "houses": houses,
                "start_pos": start_pos,
                "exit_pos": exit_pos,
                "bfs_trace": bfs_trace,
            }

    # Fallback: return last generated map even if not fully reachable
    return {
        "grid": grid,
        "houses": houses,
        "start_pos": start_pos,
        "exit_pos": exit_pos,
        "bfs_trace": bfs_trace,
    }
