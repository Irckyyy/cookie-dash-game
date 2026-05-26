"""
ui/screens.py — Title, Difficulty Select, and End/Results screens.
Translated from the HTML screen divs and their associated UI logic.
All rendering done with Pygame primitives and system fonts.
"""

import pygame
from setting import (
    Colors, WINDOW_WIDTH, WINDOW_HEIGHT,
    Difficulty, DIFFICULTY_CONFIG,
)


class ScreenManager:
    """Manages drawing of non-gameplay screens (title, difficulty, end)."""

    def __init__(self):
        self._big_font = None
        self._title_font = None
        self._btn_font = None
        self._sub_font = None
        self._small_font = None
        self._emoji_big = None
        self._stat_font = None
        self._init_fonts()

        # State
        self.selected_difficulty = Difficulty.EASY
        self._diff_rects = {}        # difficulty -> pygame.Rect (for click detection)
        self._play_rect = None       # play button rect
        self._back_rect = None       # back button rect
        self._start_rect = None      # start button on title
        self._menu_rect = None       # menu button on end screen
        self._again_rect = None      # play again button on end screen
        self._review_rect = None     # view maps button on end screen
        self._review_back_rect = None  # back button on review screen

        # Animation
        self._cookie_bob = 0
        self._cookie_dir = 1

    def _init_fonts(self):
        try:
            self._big_font = pygame.font.SysFont("segoeuisymbol", 72)
            self._title_font = pygame.font.SysFont("segoeuisymbol", 42, bold=True)
            self._btn_font = pygame.font.SysFont("segoeuisymbol", 20, bold=True)
            self._sub_font = pygame.font.SysFont("segoeuisymbol", 14)
            self._small_font = pygame.font.SysFont("segoeuisymbol", 12)
            self._emoji_big = pygame.font.SysFont("segoeuisymbol", 56)
            self._stat_font = pygame.font.SysFont("segoeuisymbol", 24, bold=True)
        except Exception:
            self._big_font = pygame.font.Font(None, 74)
            self._title_font = pygame.font.Font(None, 44)
            self._btn_font = pygame.font.Font(None, 22)
            self._sub_font = pygame.font.Font(None, 16)
            self._small_font = pygame.font.Font(None, 14)
            self._emoji_big = pygame.font.Font(None, 58)
            self._stat_font = pygame.font.Font(None, 26)

    def _draw_button(self, surface, rect, text, primary=True, hover_rect=None):
        """Draw a styled button."""
        if primary:
            bg = Colors.GOLD
            fg = (26, 10, 0)
            # Shadow
            shadow_rect = rect.copy()
            shadow_rect.y += 3
            shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            shadow_surf.fill((*Colors.GOLD, 100))
            surface.blit(shadow_surf, shadow_rect)
        else:
            bg = Colors.CARD
            fg = Colors.TEXT
            pygame.draw.rect(surface, Colors.BORDER, rect, width=1, border_radius=25)

        pygame.draw.rect(surface, bg, rect, border_radius=25)
        text_surf = self._btn_font.render(text, True, fg)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    # ==================== TITLE SCREEN ====================
    def render_title(self, surface: pygame.Surface, dt: float):
        """Draw the title screen."""
        surface.fill(Colors.NIGHT)
        self._draw_stars(surface)

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        # Floating cookie animation
        self._cookie_bob += dt * 2.0 * self._cookie_dir
        if abs(self._cookie_bob) > 12:
            self._cookie_dir *= -1

        cookie = self._big_font.render("🍪", True, Colors.GOLD)
        cookie_rect = cookie.get_rect(centerx=cx,
                                       centery=cy - 140 + int(self._cookie_bob))
        surface.blit(cookie, cookie_rect)

        # Title
        title1 = self._title_font.render("Girl Scout Cookie", True, Colors.GOLD)
        title2 = self._title_font.render("Night Delivery Dash", True, Colors.GOLD)
        surface.blit(title1, title1.get_rect(centerx=cx, centery=cy - 60))
        surface.blit(title2, title2.get_rect(centerx=cx, centery=cy - 15))

        # Subtitle
        sub = self._sub_font.render("INTRO TO AI · CASE STUDY 1", True, Colors.MUTED)
        surface.blit(sub, sub.get_rect(centerx=cx, centery=cy + 25))

        # Start button
        self._start_rect = pygame.Rect(cx - 90, cy + 60, 180, 48)
        self._draw_button(surface, self._start_rect, "▶  Start Game")

        # Description
        desc_lines = [
            "Deliver cookies to 3 houses and exit the village before the AI!",
            "Navigate with arrow keys or WASD.",
        ]
        for i, line in enumerate(desc_lines):
            desc = self._small_font.render(line, True, Colors.MUTED)
            surface.blit(desc, desc.get_rect(centerx=cx, centery=cy + 130 + i * 20))

    def handle_title_click(self, pos: tuple) -> str:
        """Handle click on title screen. Returns next screen or None."""
        if self._start_rect and self._start_rect.collidepoint(pos):
            return "difficulty"
        return None

    # ==================== DIFFICULTY SCREEN ====================
    def render_difficulty(self, surface: pygame.Surface):
        """Draw the difficulty selection screen."""
        surface.fill(Colors.NIGHT)
        self._draw_stars(surface)

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        # Title
        title = self._title_font.render("Choose Difficulty", True, Colors.GOLD)
        surface.blit(title, title.get_rect(centerx=cx, centery=cy - 180))

        sub = self._sub_font.render("Affects your flashlight range and AI behavior",
                                     True, Colors.MUTED)
        surface.blit(sub, sub.get_rect(centerx=cx, centery=cy - 145))

        # Difficulty cards
        card_w, card_h = 200, 160
        gap = 20
        total_w = 3 * card_w + 2 * gap
        start_x = cx - total_w // 2

        self._diff_rects.clear()
        for i, diff_key in enumerate([Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]):
            cfg = DIFFICULTY_CONFIG[diff_key]
            card_x = start_x + i * (card_w + gap)
            card_y = cy - 80
            card_rect = pygame.Rect(card_x, card_y, card_w, card_h)
            self._diff_rects[diff_key] = card_rect

            # Card background
            is_selected = (diff_key == self.selected_difficulty)
            if is_selected:
                bg = (40, 38, 20)  # gold tint
                border = Colors.GOLD
            else:
                bg = Colors.CARD
                border = Colors.BORDER

            pygame.draw.rect(surface, bg, card_rect, border_radius=16)
            pygame.draw.rect(surface, border, card_rect, width=2, border_radius=16)

            # Icon
            icon = self._big_font.render(cfg["icon"], True, Colors.TEXT)
            icon_rect = icon.get_rect(centerx=card_rect.centerx,
                                       centery=card_rect.top + 40)
            surface.blit(icon, icon_rect)

            # Name
            name = self._btn_font.render(cfg["name"], True, Colors.GOLD)
            name_rect = name.get_rect(centerx=card_rect.centerx,
                                       centery=card_rect.top + 85)
            surface.blit(name, name_rect)

            # Description lines
            desc_lines = cfg["desc"].split("\n")
            for j, line in enumerate(desc_lines):
                desc = self._small_font.render(line, True, Colors.MUTED)
                desc_rect = desc.get_rect(centerx=card_rect.centerx,
                                           centery=card_rect.top + 115 + j * 16)
                surface.blit(desc, desc_rect)

        # Buttons
        btn_y = cy + 120
        self._back_rect = pygame.Rect(cx - 170, btn_y, 140, 42)
        self._play_rect = pygame.Rect(cx + 30, btn_y, 140, 42)
        self._draw_button(surface, self._back_rect, "← Back", primary=False)
        self._draw_button(surface, self._play_rect, "Play!")

    def handle_difficulty_click(self, pos: tuple) -> str:
        """Handle click on difficulty screen. Returns 'game', 'title', or None."""
        # Check difficulty card clicks
        for diff_key, rect in self._diff_rects.items():
            if rect.collidepoint(pos):
                self.selected_difficulty = diff_key
                return None

        if self._play_rect and self._play_rect.collidepoint(pos):
            return "game"
        if self._back_rect and self._back_rect.collidepoint(pos):
            return "title"
        return None

    # ==================== END SCREEN ====================
    def render_end(self, surface: pygame.Surface, results: dict):
        """Draw the end/results screen with algorithm description."""
        surface.fill(Colors.NIGHT)
        self._draw_stars(surface)

        cx = WINDOW_WIDTH // 2

        # Result card background
        card_w, card_h = 520, 470
        card_rect = pygame.Rect(cx - card_w // 2, 30, card_w, card_h)
        pygame.draw.rect(surface, Colors.CARD, card_rect, border_radius=20)
        pygame.draw.rect(surface, Colors.BORDER, card_rect, width=1, border_radius=20)

        # Winner badge
        badge = self._emoji_big.render(results.get("winner_badge", "🏆"),
                                        True, Colors.GOLD)
        surface.blit(badge, badge.get_rect(centerx=cx, centery=card_rect.top + 45))

        # Winner text
        winner = self._title_font.render(results.get("winner_text", "Game Over"),
                                          True, Colors.GOLD)
        surface.blit(winner, winner.get_rect(centerx=cx, centery=card_rect.top + 92))

        # Stats grid (2 columns × 3 rows)
        stats = [
            ("Your Score", str(results.get("human_score", 0)), Colors.BLUE),
            ("AI Score", str(results.get("ai_score", 0)), Colors.PURPLE),
            ("Your PI", str(results.get("human_pi", "0")), Colors.BLUE),
            ("AI PI", str(results.get("ai_pi", "0")), Colors.PURPLE),
            ("Your Time", results.get("human_time", "0:00"), Colors.BLUE),
            ("AI Time", results.get("ai_time", "0:00"), Colors.PURPLE),
        ]

        stat_w = (card_w - 60) // 2
        stat_h = 50
        stat_gap = 8
        stat_start_y = card_rect.top + 125

        for idx, (label, value, color) in enumerate(stats):
            col = idx % 2
            row = idx // 2
            sx = card_rect.left + 20 + col * (stat_w + stat_gap + 10)
            sy = stat_start_y + row * (stat_h + stat_gap)
            stat_rect = pygame.Rect(sx, sy, stat_w, stat_h)

            pygame.draw.rect(surface, Colors.DEEP, stat_rect, border_radius=10)

            # Label
            lbl = self._small_font.render(label.upper(), True, Colors.MUTED)
            surface.blit(lbl, (sx + 12, sy + 6))

            # Value
            val = self._stat_font.render(value, True, color)
            surface.blit(val, (sx + 12, sy + 24))

        # Algorithm description section
        algo_y = stat_start_y + 3 * (stat_h + stat_gap) + 10
        algo_name = results.get("algo_name", "")
        algo_desc = results.get("algo_desc", "")

        if algo_name:
            # Divider line
            pygame.draw.line(surface, Colors.BORDER,
                            (card_rect.left + 30, algo_y),
                            (card_rect.right - 30, algo_y), 1)
            algo_y += 12

            algo_title = self._sub_font.render(
                f"AI Algorithm: {algo_name}", True, Colors.GOLD
            )
            surface.blit(algo_title,
                         algo_title.get_rect(centerx=cx, top=algo_y))
            algo_y += 22

            for line in algo_desc.split("\n"):
                desc = self._small_font.render(line, True, Colors.MUTED)
                surface.blit(desc, desc.get_rect(centerx=cx, top=algo_y))
                algo_y += 16

        # Buttons row: Menu | View Maps | Play Again
        btn_y = card_rect.bottom + 20
        self._menu_rect = pygame.Rect(cx - 240, btn_y, 140, 42)
        self._review_rect = pygame.Rect(cx - 70, btn_y, 140, 42)
        self._again_rect = pygame.Rect(cx + 100, btn_y, 140, 42)
        self._draw_button(surface, self._menu_rect, "Menu", primary=False)
        self._draw_button(surface, self._review_rect, "View Maps", primary=False)
        self._draw_button(surface, self._again_rect, "Play Again")

    def handle_end_click(self, pos: tuple) -> str:
        """Handle click on end screen. Returns 'title', 'game', 'review', or None."""
        if self._menu_rect and self._menu_rect.collidepoint(pos):
            return "title"
        if self._again_rect and self._again_rect.collidepoint(pos):
            return "game"
        if self._review_rect and self._review_rect.collidepoint(pos):
            return "review"
        return None

    def render_review(self, surface: pygame.Surface, results: dict, speed_label: str = "1x"):
        """Draw UI elements for the review screen (algorithm description & back button)."""
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT - 120
        
        card_w = 600
        card_h = 100
        card_rect = pygame.Rect(cx - card_w // 2, cy - 20, card_w, card_h)
        pygame.draw.rect(surface, Colors.CARD, card_rect, border_radius=12)
        pygame.draw.rect(surface, Colors.BORDER, card_rect, width=1, border_radius=12)

        algo_name = results.get("algo_name", "")
        algo_desc = results.get("algo_desc", "")

        algo_title = self._sub_font.render(f"AI Algorithm: {algo_name}", True, Colors.GOLD)
        surface.blit(algo_title, algo_title.get_rect(centerx=cx, top=card_rect.top + 10))

        y = card_rect.top + 35
        for line in algo_desc.split("\n"):
            desc = self._small_font.render(line, True, Colors.MUTED)
            surface.blit(desc, desc.get_rect(centerx=cx, top=y))
            y += 16

        # Back button
        btn_y = card_rect.bottom + 15
        self._review_back_rect = pygame.Rect(cx - 150, btn_y, 140, 42)
        self._draw_button(surface, self._review_back_rect, "← Back", primary=False)

        # Speed button
        self._review_speed_rect = pygame.Rect(cx + 10, btn_y, 140, 42)
        self._draw_button(surface, self._review_speed_rect, f"Speed: {speed_label}", primary=False)

    def handle_review_click(self, pos: tuple) -> str:
        """Handle click on review screen. Returns 'end', 'speed', or None."""
        if self._review_back_rect and self._review_back_rect.collidepoint(pos):
            return "end"
        if getattr(self, '_review_speed_rect', None) and self._review_speed_rect.collidepoint(pos):
            return "speed"
        return None

    # ==================== STARS ====================
    def _draw_stars(self, surface: pygame.Surface):
        """Draw twinkling star dots on the background."""
        import random as _r
        # Use a fixed seed for consistent star positions
        state = _r.getstate()
        _r.seed(42)
        for _ in range(80):
            x = _r.randint(0, WINDOW_WIDTH)
            y = _r.randint(0, WINDOW_HEIGHT)
            size = _r.choice([1, 1, 1, 2])
            alpha = _r.randint(60, 200)
            color = (alpha, alpha, alpha)
            if size == 1:
                surface.set_at((x, y), color)
            else:
                pygame.draw.circle(surface, color, (x, y), size)
        _r.setstate(state)


class NotificationManager:
    """Manages popup notifications (slides in from top)."""

    def __init__(self):
        self._font = None
        self._init_fonts()
        self._message = ""
        self._timer = 0.0
        self._duration = 2.5
        self._active = False

    def show(self, msg: str, duration: float = 2.5):
        """Show a notification message."""
        self._message = msg
        self._timer = 0.0
        self._duration = duration
        self._active = True    

    def _init_fonts(self):
        try:
            self._font = pygame.font.SysFont("segoeuisymbol", 16, bold=True)
        except Exception:
            self._font = pygame.font.Font(None, 18)

    def show(self, msg: str, duration: float = 2.5):
        """Show a notification message."""
        self._message = msg
        self._timer = 0.0
        self._duration = duration
        self._active = True

    def update(self, dt: float):
        """Update notification timer."""
        if self._active:
            self._timer += dt
            if self._timer >= self._duration:
                self._active = False

    def render(self, surface: pygame.Surface):
        """Render the notification if active."""
        if not self._active:
            return

        text = self._font.render(self._message, True, (26, 10, 0))
        pad_x, pad_y = 24, 10
        w = text.get_width() + pad_x * 2
        h = text.get_height() + pad_y * 2

        # Slide in animation
        target_y = 16
        if self._timer < 0.3:
            # Slide in
            progress = self._timer / 0.3
            y = int(-60 + (target_y + 60) * progress)
        elif self._timer > self._duration - 0.3:
            # Slide out
            progress = (self._timer - (self._duration - 0.3)) / 0.3
            y = int(target_y - (target_y + 60) * progress)
        else:
            y = target_y

        x = (WINDOW_WIDTH - w) // 2
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, Colors.GOLD, rect, border_radius=25)
        surface.blit(text, (x + pad_x, y + pad_y))
