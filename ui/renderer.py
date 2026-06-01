"""
ui/renderer.py — Handles rendering of the game grid and entities.
Translated from HTML canvas drawing logic (drawGrid, drawEntity, etc.).
Now uses pixel-art sprite assets instead of emoji text rendering.
"""

import pygame
from setting import (
    Colors, Tile, GRID_PX, SIZE, TILE_SIZE, TILE_GAP, GRID_PADDING
)
from utils.helper import manhattan, resource_path
from ui.assets import assets


class GridRenderer:
    """Renders the tile grid and entities on it."""

    def __init__(self):
        # We will initialize fonts dynamically to avoid missing system fonts
        self._small_font = None
        self._symbol_font = None
        self._emoji_font = None
        self._init_fonts()

        # Track player facing direction per entity
        self._human_facing = "down"
        self._ai_facing = "down"

    def _init_fonts(self):
        font_path = resource_path("assets/fonts/PressStart2P-Regular.ttf")
        try:
            self._small_font = pygame.font.Font(font_path, 8)
            self._symbol_font = pygame.font.Font(font_path, 12)
            self._hazard_font = pygame.font.Font(font_path, 16)
        except Exception:
            try:
                self._small_font = pygame.font.SysFont("segoeuisymbol", 12)
                self._symbol_font = pygame.font.SysFont("segoeuisymbol", 18, bold=True)
                self._hazard_font = pygame.font.SysFont("segoeuisymbol", 24, bold=True)
            except Exception:
                self._small_font = pygame.font.Font(None, 14)
                self._symbol_font = pygame.font.Font(None, 20)
                self._hazard_font = pygame.font.Font(None, 24)

        try:
            self._emoji_font = pygame.font.SysFont("segoeuisymbol", 24)
        except Exception:
            self._emoji_font = pygame.font.Font(None, 26)

    def _get_direction_from_delta(self, dx: int, dy: int) -> str:
        """Convert movement delta to a facing direction string."""
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        elif dy != 0:
            return "down" if dy > 0 else "up"
        return None  # no movement

    def _draw_tile_bg(self, surface: pygame.Surface, tile_rect: pygame.Rect,
                      tile_type: int, is_revealed: bool, key: str,
                      delivered: set, ai_brain_state: dict = None,
                      is_player_here: bool = False):
        if not is_revealed:
            # Draw the empty (dark) tile sprite
            surface.blit(assets.empty_tile, tile_rect)
            return

        # Draw the grass base for all revealed tiles
        surface.blit(assets.filled_tile, tile_rect)

        # AI Brain visualizations — tinted overlays
        if ai_brain_state and tile_type not in (Tile.WALL, Tile.PUDDLE, Tile.BROKEN):
            overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            if key in ai_brain_state.get('pruned', set()):
                overlay.fill((200, 40, 40, 80))  # Red tint for pruned
                surface.blit(overlay, tile_rect)
            elif key in ai_brain_state.get('visited', set()):
                overlay.fill((200, 200, 40, 60))  # Yellow tint for visited
                surface.blit(overlay, tile_rect)

        if ai_brain_state and is_player_here and 'Penalty' in ai_brain_state.get('state', ''):
            overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            overlay.fill((255, 50, 50, 120))
            surface.blit(overlay, tile_rect)

    def _draw_tile_entity(self, surface: pygame.Surface, tile_rect: pygame.Rect,
                          tile_type: int, is_player_here: bool, is_human: bool,
                          key: str, delivered: set, is_revealed: bool, known_hazards: set, force_reveal: bool = False, is_battery: bool = False):
        """Draw the entity sprite on top of a tile."""
        if not is_revealed and not is_player_here:
            return

        # Draw tile-specific sprites
        if is_battery:
            if assets.battery:
                sprite_rect = assets.battery.get_rect(center=tile_rect.center)
                surface.blit(assets.battery, sprite_rect)

        if tile_type == Tile.HOUSE:
            sprite = assets.delivered_house if key in delivered else assets.undelivered_house
            if sprite:
                sprite_rect = sprite.get_rect(center=tile_rect.center)
                surface.blit(sprite, sprite_rect)

        elif tile_type == Tile.PUDDLE:
            if force_reveal:
                if assets.puddle:
                    sprite_rect = assets.puddle.get_rect(center=tile_rect.center)
                    surface.blit(assets.puddle, sprite_rect)

        elif tile_type == Tile.BROKEN:
            if force_reveal:
                if assets.hole:
                    sprite_rect = assets.hole.get_rect(center=tile_rect.center)
                    surface.blit(assets.hole, sprite_rect)

        elif tile_type == Tile.EXIT:
            if assets.door:
                sprite_rect = assets.door.get_rect(center=tile_rect.center)
                surface.blit(assets.door, sprite_rect)

        elif tile_type == Tile.WALL:
            # Alternate between rock and tree based on position for variety
            x, y = [int(c) for c in key.split(",")]
            sprite = assets.tree if (x + y) % 2 == 0 else assets.rock
            if sprite:
                sprite_rect = sprite.get_rect(center=tile_rect.center)
                surface.blit(sprite, sprite_rect)

        elif tile_type == Tile.START:
            if assets.entrance:
                sprite_rect = assets.entrance.get_rect(center=tile_rect.center)
                surface.blit(assets.entrance, sprite_rect)

        if is_player_here:
            # Draw player sprite
            facing = self._human_facing if is_human else self._ai_facing
            if not is_human and assets.get("ai_head"):
                sprite = assets.get("ai_head")
            else:
                sprite = assets.get_player_sprite(facing)
            if sprite:
                sprite_rect = sprite.get_rect(center=tile_rect.center)
                # Shift up slightly so the character "stands" on the tile
                sprite_rect.y -= int(TILE_SIZE * 0.12)
                surface.blit(sprite, sprite_rect)

    def render(self, surface: pygame.Surface, x_offset: int, y_offset: int,
               player, game_map: list, is_human: bool,
               force_reveal: bool = False, path_overlay: list = None,
               path_color: tuple = None, ai_brain_state: dict = None,
               override_size: int = None, difficulty: str = None, batteries: set = None):
        """
        Render the full grid onto the given surface.
        x_offset, y_offset: top-left corner of the grid wrapper.
        force_reveal: if True, show all tiles regardless of player vision.
        path_overlay: list of (x,y) positions to highlight as a path.
        path_color: color for the path overlay lines.
        override_size: if set, scale the grid to fit this pixel size.
        """
        # Calculate tile dimensions — scaled if override_size is provided
        if override_size:
            grid_px = override_size
            grid_padding = max(4, int(GRID_PADDING * override_size / GRID_PX))
            inner = grid_px - grid_padding * 2
            tile_gap = max(1, int(TILE_GAP * override_size / GRID_PX))
            tile_size = (inner - (SIZE - 1) * tile_gap) // SIZE
        else:
            grid_px = GRID_PX
            grid_padding = GRID_PADDING
            tile_gap = TILE_GAP
            tile_size = TILE_SIZE

        # Draw grid wrapper background (brown border matching mockup)
        wrapper_rect = pygame.Rect(x_offset, y_offset, grid_px, grid_px)
        pygame.draw.rect(surface, (101, 67, 33), wrapper_rect, border_radius=6)
        pygame.draw.rect(surface, (82, 54, 27), wrapper_rect, width=4, border_radius=6)

        # Use the end of the path overlay as the player's animated position
        current_pos = path_overlay[-1] if path_overlay else player.pos

        # Update facing direction based on path or movement
        if path_overlay and len(path_overlay) >= 2:
            prev = path_overlay[-2]
            curr = path_overlay[-1]
            dx = curr[0] - prev[0]
            dy = curr[1] - prev[1]
            new_dir = self._get_direction_from_delta(dx, dy)
            if new_dir:
                if is_human:
                    self._human_facing = new_dir
                else:
                    self._ai_facing = new_dir
        elif hasattr(player, 'path_history') and len(player.path_history) >= 2:
            prev = player.path_history[-2]
            curr = player.path_history[-1]
            dx = curr[0] - prev[0]
            dy = curr[1] - prev[1]
            new_dir = self._get_direction_from_delta(dx, dy)
            if new_dir:
                if is_human:
                    self._human_facing = new_dir
                else:
                    self._ai_facing = new_dir

        current_vision_set = set()
        if difficulty and hasattr(player, 'tiles_in_view'):
            facing = self._human_facing if is_human else self._ai_facing
            current_vision_set = player.tiles_in_view(difficulty, facing)

        # Draw each tile
        for y in range(SIZE):
            for x in range(SIZE):
                key = f"{x},{y}"
                is_revealed = force_reveal or (key in player.revealed_tiles)
                tile_type = game_map[y][x]
                is_player_here = (current_pos[0] == x and current_pos[1] == y)

                # Calculate tile pixel position
                tx = x_offset + grid_padding + x * (tile_size + tile_gap)
                ty = y_offset + grid_padding + y * (tile_size + tile_gap)
                tile_rect = pygame.Rect(tx, ty, tile_size, tile_size)

                # Draw tile background (grass or dark)
                self._draw_tile_bg(surface, tile_rect, tile_type, is_revealed,
                                   key, player.delivered_houses, ai_brain_state,
                                   is_player_here)

                # Special border for typed tiles
                if is_revealed:
                    border_color = self._get_tile_border_color(
                        tile_type, is_revealed, key, player.delivered_houses
                    )
                    if border_color:
                        pygame.draw.rect(surface, border_color, tile_rect,
                                         width=1, border_radius=3)

                # Player glow effect
                if is_player_here:
                    glow_color = Colors.PLAYER_GLOW if is_human else Colors.AI_GLOW
                    glow_rect = tile_rect.inflate(4, 4)
                    pygame.draw.rect(surface, glow_color, glow_rect,
                                     width=2, border_radius=6)
                    glow_inner = tile_rect.inflate(1, 1)
                    pygame.draw.rect(surface, glow_color, glow_inner,
                                     width=1, border_radius=5)

                # Calculate if tile is in current vision radius
                is_in_vision = key in current_vision_set

                # Check flashlight
                flashlight_active = getattr(player, 'flashlight_timer', 0.0) > 0
                is_known_hazard = key in getattr(player, 'known_hazards', set())

                if is_human:
                    reveal_hazard = force_reveal or (is_in_vision and (is_known_hazard or flashlight_active))
                else:
                    reveal_hazard = force_reveal or (is_in_vision and flashlight_active)
        
                is_battery_on_tile = batteries is not None and (x, y) in batteries

                # Draw entity sprite on tile (walls, houses, exits, known hazards)
                self._draw_tile_entity(surface, tile_rect, tile_type,
                                       is_player_here, is_human,
                                       key, player.delivered_houses, is_revealed, getattr(player, 'known_hazards', set()), reveal_hazard, is_battery_on_tile)

                if is_player_here and is_human:
                    hazards = 0
                    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < SIZE and 0 <= ny < SIZE:
                            if game_map[ny][nx] in (Tile.PUDDLE, Tile.BROKEN):
                                hazards += 1
                    
                    if hazards > 0 and assets.warning:
                        import math
                        import time
                        
                        # Scale based on hazards
                        scale_factor = 0.5 + (hazards - 1) * 0.1
                        
                        # Glow/bob animation
                        t = time.time() * 5
                        bob = math.sin(t) * 3
                        
                        orig_w, orig_h = assets.warning.get_size()
                        base_w = tile_size * 0.6
                        new_w = max(1, int(base_w * scale_factor))
                        new_h = max(1, int((orig_h / orig_w) * new_w))
                        warning_scaled = pygame.transform.smoothscale(assets.warning, (new_w, new_h))
                        
                        warn_rect = warning_scaled.get_rect(center=tile_rect.center)
                        warn_rect.y -= (tile_size // 2 + new_h // 2 + int(bob))
                        
                        surface.blit(warning_scaled, warn_rect)


                # AI heuristic text overlay (review mode)
                if ai_brain_state and is_revealed and not is_player_here:
                    if tile_type in (Tile.EMPTY, Tile.START):
                        target = ai_brain_state.get('target')
                        if target:
                            h_val = str(manhattan((x, y), target))
                            h_surf = self._small_font.render(h_val, True, (255, 255, 255))
                            # Semi-transparent background for readability
                            bg_surf = pygame.Surface((h_surf.get_width() + 4, h_surf.get_height() + 2), pygame.SRCALPHA)
                            bg_surf.fill((0, 0, 0, 120))
                            bg_rect = bg_surf.get_rect(bottomright=(tile_rect.right - 2, tile_rect.bottom - 2))
                            surface.blit(bg_surf, bg_rect)
                            surface.blit(h_surf, (bg_rect.x + 2, bg_rect.y + 1))

        # Draw path overlay as continuous lines
        if path_overlay and len(path_overlay) > 1:
            line_color = path_color or (Colors.BLUE if is_human else Colors.PURPLE)
            points = []
            for px, py in path_overlay:
                ptx = x_offset + grid_padding + px * (tile_size + tile_gap) + tile_size // 2
                pty = y_offset + grid_padding + py * (tile_size + tile_gap) + tile_size // 2
                points.append((ptx, pty))

            pygame.draw.lines(surface, (*line_color, 180), False, points, width=3)

    def _get_tile_border_color(self, tile_type: int, is_revealed: bool, key: str, delivered: set):
        """Determine border color if needed (e.g., for houses)."""
        if not is_revealed:
            return None
        if tile_type == Tile.HOUSE:
            return Colors.GREEN if key in delivered else Colors.GOLD
        return None
