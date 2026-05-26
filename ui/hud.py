"""
ui/hud.py — Heads-Up Display: scores, timer, delivery dots, log panel.
Translated from the game-header HTML and updateHUDs() JS function.
"""

import pygame
from setting import Colors, DELIVERIES_NEEDED, WINDOW_WIDTH
from utils.helper import format_time


class HUD:
    """Draws the top HUD bar with scores, timer, and delivery dots."""

    def __init__(self):
        self._title_font = None
        self._val_font = None
        self._label_font = None
        self._timer_font = None
        self._log_font = None
        self._init_fonts()
        self.log_entries = []   # list of (time_str, msg, log_type)

    def _init_fonts(self):
        try:
            self._title_font = pygame.font.SysFont("segoeuisymbol", 22, bold=True)
            self._val_font = pygame.font.SysFont("segoeuisymbol", 18, bold=True)
            self._label_font = pygame.font.SysFont("segoeuisymbol", 13)
            self._timer_font = pygame.font.SysFont("segoeuisymbol", 32, bold=True)
            self._log_font = pygame.font.SysFont("segoeuisymbol", 12)
        except Exception:
            self._title_font = pygame.font.Font(None, 24)
            self._val_font = pygame.font.Font(None, 20)
            self._label_font = pygame.font.Font(None, 15)
            self._timer_font = pygame.font.Font(None, 34)
            self._log_font = pygame.font.Font(None, 14)

    def add_log(self, time_str: str, msg: str, log_type: str = "system"):
        """Add a log entry."""
        self.log_entries.insert(0, (time_str, msg, log_type))
        # Keep max 50 entries
        if len(self.log_entries) > 50:
            self.log_entries.pop()

    def clear_log(self):
        self.log_entries.clear()

    def _draw_delivery_dots(self, surface: pygame.Surface, x: int, y: int,
                            deliveries: int):
        """Draw 3 delivery indicator dots."""
        for i in range(DELIVERIES_NEEDED):
            dot_x = x + i * 24
            dot_rect = pygame.Rect(dot_x, y, 18, 18)
            if deliveries > i:
                pygame.draw.circle(surface, Colors.GREEN,
                                   dot_rect.center, 9)
                # Draw checkmark
                check = self._label_font.render("✓", True, Colors.WHITE)
                check_rect = check.get_rect(center=dot_rect.center)
                surface.blit(check, check_rect)
            else:
                pygame.draw.circle(surface, Colors.BORDER,
                                   dot_rect.center, 9, width=2)

    def render(self, surface: pygame.Surface, human, ai, elapsed: int,
               y_offset: int = 10):
        """Render the full HUD bar."""
        max_w = min(900, WINDOW_WIDTH - 40)
        hud_x = (WINDOW_WIDTH - max_w) // 2
        hud_rect = pygame.Rect(hud_x, y_offset, max_w, 60)

        # Background
        pygame.draw.rect(surface, Colors.CARD, hud_rect, border_radius=14)
        pygame.draw.rect(surface, Colors.BORDER, hud_rect, width=1, border_radius=14)

        # === Left: Human player ===
        # Emoji
        player_emoji = self._title_font.render("🧒", True, Colors.TEXT)
        surface.blit(player_emoji, (hud_x + 14, y_offset + 16))

        # Label
        you_label = self._label_font.render("YOU", True, Colors.MUTED)
        surface.blit(you_label, (hud_x + 44, y_offset + 10))

        # Score
        h_score = self._val_font.render(str(human.score), True, Colors.BLUE)
        surface.blit(h_score, (hud_x + 44, y_offset + 28))

        # Delivery dots
        self._draw_delivery_dots(surface, hud_x + 110, y_offset + 22,
                                 human.deliveries)
        # Delivery dots
        self._draw_delivery_dots(surface, hud_x + 110, y_offset + 22,
                                 human.deliveries)

        # NEW: Draw human inventory
        self._draw_inventory(surface, hud_x + 190, y_offset + 18, human)

        # === Center: Timer ===
        timer_text = format_time(elapsed)
        timer_surf = self._timer_font.render(timer_text, True, Colors.GOLD)
        timer_rect = timer_surf.get_rect(centerx=hud_rect.centerx,
                                          top=y_offset + 8)
        surface.blit(timer_surf, timer_rect)

        time_label = self._label_font.render("TIME", True, Colors.MUTED)
        time_label_rect = time_label.get_rect(centerx=hud_rect.centerx,
                                               top=y_offset + 40)
        surface.blit(time_label, time_label_rect)

        # === Right: AI player ===
        # Delivery dots (right-aligned)
        self._draw_delivery_dots(surface, hud_x + max_w - 182, y_offset + 22,
                                 ai.deliveries)

        # Score
        a_score = self._val_font.render(str(ai.score), True, Colors.PURPLE)
        a_score_rect = a_score.get_rect(right=hud_x + max_w - 50,
                                         top=y_offset + 28)
        surface.blit(a_score, a_score_rect)

        # Label
        ai_label = self._label_font.render("AI", True, Colors.MUTED)
        ai_label_rect = ai_label.get_rect(right=hud_x + max_w - 50,
                                           top=y_offset + 10)
        surface.blit(ai_label, ai_label_rect)

        # Emoji
        ai_emoji = self._title_font.render("🤖", True, Colors.TEXT)
        surface.blit(ai_emoji, (hud_x + max_w - 40, y_offset + 16))

        # Delivery dots (right-aligned)
        self._draw_delivery_dots(surface, hud_x + max_w - 182, y_offset + 22,
                                 ai.deliveries)

        # NEW: Draw AI inventory
        self._draw_inventory(surface, hud_x + max_w - 256, y_offset + 18, ai)

    def render_log(self, surface: pygame.Surface, y_offset: int, max_height: int = 100):
        """Render the log panel below the grids."""
        max_w = min(900, WINDOW_WIDTH - 40)
        log_x = (WINDOW_WIDTH - max_w) // 2
        log_rect = pygame.Rect(log_x, y_offset, max_w, max_height)

        # Background
        pygame.draw.rect(surface, Colors.CARD, log_rect, border_radius=12)
        pygame.draw.rect(surface, Colors.BORDER, log_rect, width=1, border_radius=12)

        # Draw log entries (newest first, top to bottom)
        cy = y_offset + 8
        for i, (time_str, msg, log_type) in enumerate(self.log_entries):
            if cy + 16 > y_offset + max_height - 8:
                break

            # Choose color based on log type
            if log_type == "human":
                color = Colors.BLUE
            elif log_type == "ai":
                color = Colors.PURPLE
            elif log_type == "penalty":
                color = Colors.RED
            else:
                color = Colors.GOLD

            time_surf = self._log_font.render(time_str, True, Colors.MUTED)
            msg_surf = self._log_font.render(msg, True, color)
            surface.blit(time_surf, (log_x + 12, cy))
            surface.blit(msg_surf, (log_x + 56, cy))
            cy += 18

    def _draw_inventory(self, surface: pygame.Surface, x: int, y: int, player):
            """Draw the player's active item inventory."""
            # Box 1 (Boots)
            box1_rect = pygame.Rect(x, y, 26, 26)
            pygame.draw.rect(surface, Colors.DEEP, box1_rect, border_radius=6)
            pygame.draw.rect(surface, Colors.BORDER, box1_rect, width=1, border_radius=6)

            # Draw Boot emoji if the player has it
            if player.has_boots:
                boot_surf = self._val_font.render("👢", True, Colors.TEXT)
                surface.blit(boot_surf, boot_surf.get_rect(center=box1_rect.center))

            # Box 2 (Rope)
            box2_rect = pygame.Rect(x + 32, y, 26, 26)
            pygame.draw.rect(surface, Colors.DEEP, box2_rect, border_radius=6)
            pygame.draw.rect(surface, Colors.BORDER, box2_rect, width=1, border_radius=6)

            # Draw Rope emoji if the player has it
            if player.has_rope:
                rope_surf = self._val_font.render("🪢", True, Colors.TEXT)
                surface.blit(rope_surf, rope_surf.get_rect(center=box2_rect.center))