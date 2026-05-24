"""
ui/renderer.py — Handles rendering of the game grid and entities.
Translated from HTML canvas drawing logic (drawGrid, drawEntity, etc.).
"""

import pygame
from setting import (
    Colors, Tile, GRID_PX, SIZE, TILE_SIZE, TILE_GAP, GRID_PADDING
)
from utils.helper import manhattan


class GridRenderer:
    """Renders the tile grid and entities on it."""

    def __init__(self):
        # We will initialize fonts dynamically to avoid missing system fonts
        self._small_font = None
        self._symbol_font = None
        self._emoji_font = None
        self._init_fonts()
        self._use_emoji = True

    def _init_fonts(self):
        try:
            self._small_font = pygame.font.SysFont("segoeuisymbol", 12)
            self._symbol_font = pygame.font.SysFont("segoeuisymbol", 18, bold=True)
            self._emoji_font = pygame.font.SysFont("segoeuisymbol", 24)
        except Exception:
            self._small_font = pygame.font.Font(None, 14)
            self._symbol_font = pygame.font.Font(None, 20)
            self._emoji_font = pygame.font.Font(None, 26)
            self._use_emoji = False

    def _get_tile_bg(self, tile_type: int, is_revealed: bool, key: str, delivered: set):
        """Determine background color for a tile."""
        if not is_revealed:
            return Colors.TILE_HIDDEN

        if tile_type == Tile.HOUSE:
            if key in delivered:
                return Colors.TILE_HOUSE_DEL_SOLID  # Delivered house
            return Colors.TILE_HOUSE_SOLID      # Undelivered house

        bg_map = {
            Tile.EMPTY: Colors.TILE_REVEALED,
            Tile.WALL: Colors.BORDER,
            Tile.PUDDLE: Colors.TILE_PUDDLE_SOLID,
            Tile.BROKEN: Colors.TILE_BROKEN_SOLID,
            Tile.EXIT: Colors.TILE_EXIT_SOLID,
        }
        return bg_map.get(tile_type, Colors.TILE_REVEALED)

    def _get_tile_border_color(self, tile_type: int, is_revealed: bool, key: str, delivered: set):
        """Determine border color if needed (e.g., for houses)."""
        if not is_revealed:
            return None
        if tile_type == Tile.HOUSE:
            return Colors.GREEN if key in delivered else Colors.GOLD
        if tile_type == Tile.WALL:
            return Colors.BORDER
        return None

    def _get_tile_text(self, tile_type: int, is_player_here: bool, is_human: bool,
                       key: str, delivered: set):
        """Returns (text_string, text_color) for a tile."""
        if is_player_here:
            if self._use_emoji:
                return ("👧", Colors.TEXT) if is_human else ("🤖", Colors.TEXT)
            else:
                return ("You", Colors.BLUE) if is_human else ("AI", Colors.PURPLE)

        # Draw tile content
        if tile_type == Tile.HOUSE:
            if key in delivered:
                return ("✅", Colors.GREEN) if self._use_emoji else ("Done", Colors.GREEN)
            return ("🏠", Colors.GOLD) if self._use_emoji else ("House", Colors.GOLD)

        elif tile_type == Tile.PUDDLE:
            return ("💧", Colors.BLUE) if self._use_emoji else ("~", Colors.BLUE)

        elif tile_type == Tile.BROKEN:
            return ("🪨", Colors.TEXT) if self._use_emoji else ("X", Colors.TEXT)

        elif tile_type == Tile.EXIT:
            return ("🚪", Colors.GOLD) if self._use_emoji else ("EXIT", Colors.GOLD)

        return None, None

    def render(self, surface: pygame.Surface, x_offset: int, y_offset: int,
               player, game_map: list, is_human: bool,
               force_reveal: bool = False, path_overlay: list = None,
               path_color: tuple = None, ai_brain_state: dict = None):
        """
        Render the full grid onto the given surface.
        x_offset, y_offset: top-left corner of the grid wrapper.
        force_reveal: if True, show all tiles regardless of player vision.
        path_overlay: list of (x,y) positions to highlight as a path.
        path_color: color for the path overlay lines.
        """
        # Draw grid wrapper background
        wrapper_rect = pygame.Rect(x_offset, y_offset, GRID_PX, GRID_PX)
        pygame.draw.rect(surface, Colors.DEEP, wrapper_rect, border_radius=12)
        pygame.draw.rect(surface, Colors.BORDER, wrapper_rect, width=2, border_radius=12)

        # Use the end of the path overlay as the player's animated position
        current_pos = path_overlay[-1] if path_overlay else player.pos

        # Draw each tile
        for y in range(SIZE):
            for x in range(SIZE):
                key = f"{x},{y}"
                is_revealed = force_reveal or (key in player.revealed_tiles)
                tile_type = game_map[y][x]
                is_player_here = (current_pos[0] == x and current_pos[1] == y)

                # Calculate tile pixel position
                tx = x_offset + GRID_PADDING + x * (TILE_SIZE + TILE_GAP)
                ty = y_offset + GRID_PADDING + y * (TILE_SIZE + TILE_GAP)
                tile_rect = pygame.Rect(tx, ty, TILE_SIZE, TILE_SIZE)

                # Background
                bg = self._get_tile_bg(tile_type, is_revealed, key,
                                       player.delivered_houses)
                
                # AI Brain visualizations
                if ai_brain_state and tile_type not in (Tile.WALL, Tile.PUDDLE, Tile.BROKEN):
                    if key in ai_brain_state.get('pruned', set()):
                        bg = (100, 40, 40)  # Red tint for pruned
                    elif key in ai_brain_state.get('visited', set()):
                        bg = (100, 100, 40) # Yellow tint for visited
                        
                if ai_brain_state and is_player_here and 'Penalty' in ai_brain_state.get('state', ''):
                    bg = (200, 50, 50)  # Flash red when hitting hazard

                pygame.draw.rect(surface, bg, tile_rect, border_radius=5)

                # Special border for typed tiles
                if is_revealed:
                    border_color = self._get_tile_border_color(
                        tile_type, is_revealed, key, player.delivered_houses
                    )
                    if border_color:
                        pygame.draw.rect(surface, border_color, tile_rect,
                                         width=1, border_radius=5)

                # Player glow effect
                if is_player_here:
                    glow_color = Colors.PLAYER_GLOW if is_human else Colors.AI_GLOW
                    glow_rect = tile_rect.inflate(4, 4)
                    pygame.draw.rect(surface, glow_color, glow_rect,
                                     width=2, border_radius=6)
                    glow_inner = tile_rect.inflate(1, 1)
                    pygame.draw.rect(surface, glow_color, glow_inner,
                                     width=1, border_radius=5)

                # Text on tile
                if is_revealed or is_player_here:
                    text, color = self._get_tile_text(
                        tile_type, is_player_here, is_human,
                        key, player.delivered_houses
                    )
                    font = self._emoji_font if (self._use_emoji and text and len(text) <= 2) else self._symbol_font
                    
                    if ai_brain_state and not text and tile_type in (Tile.EMPTY, Tile.START):
                        target = ai_brain_state.get('target')
                        if target:
                            text = str(manhattan((x, y), target))
                            color = (120, 120, 120)  # Muted gray for heuristics
                            font = self._small_font
                    if text:
                        if len(text) > 1 and not self._use_emoji and font == self._emoji_font:
                            font = self._small_font
                        try:
                            text_surf = font.render(text, True, color)
                            text_rect = text_surf.get_rect(center=tile_rect.center)
                            surface.blit(text_surf, text_rect)
                        except Exception:
                            pass

        # Draw path overlay as continuous lines
        if path_overlay and len(path_overlay) > 1:
            line_color = path_color or (Colors.BLUE if is_human else Colors.PURPLE)
            points = []
            for px, py in path_overlay:
                tx = x_offset + GRID_PADDING + px * (TILE_SIZE + TILE_GAP) + TILE_SIZE // 2
                ty = y_offset + GRID_PADDING + py * (TILE_SIZE + TILE_GAP) + TILE_SIZE // 2
                points.append((tx, ty))
            
            pygame.draw.lines(surface, (*line_color, 180), False, points, width=3)
