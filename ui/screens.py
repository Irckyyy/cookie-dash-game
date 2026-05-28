"""
ui/screens.py — Title, Difficulty Select, and End/Results screens.
Translated from the HTML screen divs and their associated UI logic.
Now uses pixel-art background assets for panels, buttons, and cards.
"""

import pygame
from setting import (
    Colors, WINDOW_WIDTH, WINDOW_HEIGHT,
    Difficulty, DIFFICULTY_CONFIG,
)
from ui.assets import assets
from utils.helper import resource_path


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
        self._cred_font = None
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

        # Sky background cache
        self._sky_surface = None

    def _init_fonts(self):
        font_path = resource_path("assets/fonts/PressStart2P-Regular.ttf")
        try:
            self._big_font = pygame.font.Font(font_path, 48)
            self._title_font = pygame.font.Font(font_path, 24)
            self._btn_font = pygame.font.Font(font_path, 12)
            self._sub_font = pygame.font.Font(font_path, 10)
            self._small_font = pygame.font.Font(font_path, 8)
            self._stat_font = pygame.font.Font(font_path, 16)
            self._cred_font = pygame.font.Font(font_path, 10)
        except Exception:
            self._big_font = pygame.font.Font(None, 74)
            self._title_font = pygame.font.Font(None, 44)
            self._btn_font = pygame.font.Font(None, 22)
            self._sub_font = pygame.font.Font(None, 16)
            self._small_font = pygame.font.Font(None, 14)
            self._stat_font = pygame.font.Font(None, 26)
            self._cred_font = pygame.font.Font(None, 18)

        try:
            self._emoji_big = pygame.font.SysFont("segoeuisymbol", 56)
        except Exception:
            self._emoji_big = pygame.font.Font(None, 58)

    def _draw_sky_background(self, surface: pygame.Surface):
        """Draw the pixel-art sky background (Frame 1), scaled to fill the window."""
        sky = assets.bg_sky
        if sky is None:
            surface.fill(Colors.NIGHT)
            self._draw_stars(surface)
            return

        # Scale Frame 1 to fill the full window
        if self._sky_surface is None or self._sky_surface.get_size() != (WINDOW_WIDTH, WINDOW_HEIGHT):
            self._sky_surface = pygame.transform.smoothscale(sky, (WINDOW_WIDTH, WINDOW_HEIGHT))

        surface.blit(self._sky_surface, (0, 0))

    def _draw_sprite_button(self, surface: pygame.Surface, btn_name: str,
                             rect: pygame.Rect, bg_color=Colors.GOLD) -> pygame.Rect:
        """Draw a button using the sprite asset, scaled to fit the given rect."""
        btn_img = assets.get_button(btn_name)
        if btn_img:
            scaled = pygame.transform.smoothscale(btn_img, (rect.width, rect.height))
            surface.blit(scaled, rect)
            return rect
        else:
            # Fallback to text button with custom color (perfect for the Red Quit button!)
            self._draw_button(surface, rect, btn_name.replace("_", " ").title(), bg_color=bg_color)
            return rect

    def _draw_button(self, surface, rect, text, primary=True, bg_color=Colors.GOLD, hover_rect=None):
        """Draw a styled button (fallback when no sprite)."""
        if primary:
            bg = bg_color
            fg = (26, 10, 0) if bg_color == Colors.GOLD else Colors.WHITE
            
            # ---> FIXED SHADOW: Now uses border_radius instead of fill() <---
            shadow_rect = rect.copy()
            shadow_rect.y += 3
            shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            
            # Draw a rounded rectangle onto the transparent surface
            pygame.draw.rect(shadow_surf, (*bg, 100), shadow_surf.get_rect(), border_radius=25)
            surface.blit(shadow_surf, shadow_rect)
        else:
            bg = Colors.CARD
            fg = Colors.TEXT
            pygame.draw.rect(surface, Colors.BORDER, rect, width=1, border_radius=25)

        pygame.draw.rect(surface, bg, rect, border_radius=25)
        text_surf = self._btn_font.render(text, True, fg)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    def _draw_main_panel(self, surface: pygame.Surface, rect: pygame.Rect):
        """Draws the clean blue panel using code, ignoring the baked Home.png."""
        # Fallback blue panel with gold border
        pygame.draw.rect(surface, (88, 138, 198), rect, border_radius=6) # Blue fill
        pygame.draw.rect(surface, Colors.GOLD, rect, width=4, border_radius=6) # Gold border
        
        # Inner shadow for depth
        inner = rect.inflate(-8, -8)
        pygame.draw.rect(surface, (60, 90, 140), inner, width=2, border_radius=4)

    # ==================== BROWN PANEL HELPER ====================
    def _draw_brown_panel(self, surface: pygame.Surface, rect: pygame.Rect):
        """Draw a brown panel with gold border matching the mockup style."""
        # Brown fill
        pygame.draw.rect(surface, (101, 67, 33), rect, border_radius=12)
        # Gold border (outer)
        pygame.draw.rect(surface, Colors.GOLD, rect, width=4, border_radius=12)
        # Inner dark brown border for depth
        inner = rect.inflate(-10, -10)
        pygame.draw.rect(surface, (82, 54, 27), inner, width=2, border_radius=8)

    # ==================== TITLE SCREEN ====================
    def render_title(self, surface: pygame.Surface, dt: float):
        """Draw the title screen with Frame 1 background and main panel."""
        self._draw_sky_background(surface)

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        # Draw the blue panel
        panel_w, panel_h = 520, 380
        panel_rect = pygame.Rect(cx - panel_w // 2, cy - panel_h // 2 - 20, panel_w, panel_h)
        self._draw_main_panel(surface, panel_rect)

        # Floating cookie animation
        self._cookie_bob += dt * 2.0 * self._cookie_dir
        if abs(self._cookie_bob) > 12:
            self._cookie_dir *= -1

        cookie_sprite = assets.get_scaled("cookie", (80, 80))
        if cookie_sprite:
            cookie_rect = cookie_sprite.get_rect(centerx=cx,
                                                  centery=panel_rect.top + 60 + int(self._cookie_bob))
            surface.blit(cookie_sprite, cookie_rect)

        title1 = self._title_font.render("Cookie Delivery", True, Colors.GOLD)
        title2 = self._title_font.render("Dash", True, Colors.GOLD)
        surface.blit(title1, title1.get_rect(centerx=cx, centery=panel_rect.top + 120))
        surface.blit(title2, title2.get_rect(centerx=cx, centery=panel_rect.top + 165))

        # Subtitle
        sub = self._sub_font.render("INTRO TO AI · CASE STUDY 1", True, (210, 190, 150))
        surface.blit(sub, sub.get_rect(centerx=cx, centery=panel_rect.top + 230))

        # Play Game button
        btn_w, btn_h = 220, 52
        self._start_rect = pygame.Rect(cx - btn_w // 2, panel_rect.top + 255, btn_w, btn_h)
        self._draw_sprite_button(surface, "play_game", self._start_rect)

        # Description text
        desc_lines = [
            "Deliver cookies to 3 houses and exit the village",
            "before the AI! Navigate with arrow keys.",
        ]
        for i, line in enumerate(desc_lines):
            desc = self._small_font.render(line, True, (210, 190, 150))
            surface.blit(desc, desc.get_rect(centerx=cx, centery=panel_rect.top + 335 + i * 18))

        # BOTTOM MENU BUTTONS
        small_btn_w, small_btn_h = 140, 48
        gap = 20
        total_w = 3 * small_btn_w + 2 * gap
        start_x = cx - total_w // 2
        
        # Position them just below the blue panel
        bottom_y = panel_rect.bottom + 15

        self._option_rect = pygame.Rect(start_x, bottom_y, small_btn_w, small_btn_h)
        self._draw_sprite_button(surface, "option", self._option_rect)

        self._credits_rect = pygame.Rect(start_x + small_btn_w + gap, bottom_y, small_btn_w, small_btn_h)
        self._draw_sprite_button(surface, "credits", self._credits_rect)

        # The quit button will use your red quit.png automatically!
        self._quit_rect = pygame.Rect(start_x + 2 * (small_btn_w + gap), bottom_y, small_btn_w, small_btn_h)
        self._draw_sprite_button(surface, "quit", self._quit_rect, bg_color=(200, 60, 60))


    def handle_title_click(self, pos: tuple) -> str:
        """Handle click on title screen. Returns next screen or None."""
        if self._start_rect and self._start_rect.collidepoint(pos):
            return "difficulty"
        if getattr(self, '_option_rect', None) and self._option_rect.collidepoint(pos):
            return "options"
        if getattr(self, '_credits_rect', None) and self._credits_rect.collidepoint(pos):
            return "credits"
        if getattr(self, '_quit_rect', None) and self._quit_rect.collidepoint(pos):
            return "quit"
        return None
        
    # ==================== INTRO STORY SLIDES ====================
    def render_intro(self, surface: pygame.Surface, current_slide: int):
        """Draw the story slide background and layer the clickable sprite precisely on top."""
        # 1. Paint the background slide image (.jpg)
        slide_img = assets._cache.get(f"story_slide_{current_slide}")
        if slide_img:
            scaled_slide = pygame.transform.smoothscale(slide_img, (WINDOW_WIDTH, WINDOW_HEIGHT))
            surface.blit(scaled_slide, (0, 0))
        else:
            surface.fill((20, 25, 35))

        cx = WINDOW_WIDTH // 2
        
        # 2. FIXED: Shifted coordinates up slightly (from WINDOW_HEIGHT - 105 to WINDOW_HEIGHT - 142)
        # to map perfectly over the embedded button artwork in your slides!
        button_y_position = WINDOW_HEIGHT - 142
        self._intro_btn_rect = pygame.Rect(cx - 86, button_y_position, 172, 50)
        
        if current_slide == 6:
            # Draw your custom 'start' button asset on slide 6 if it exists, otherwise use fallback
            start_btn = assets.get_button("start")
            if start_btn:
                scaled_start = pygame.transform.smoothscale(start_btn, (self._intro_btn_rect.width, self._intro_btn_rect.height))
                surface.blit(scaled_start, self._intro_btn_rect)
            else:
                self._draw_button(surface, self._intro_btn_rect, "START", bg_color=Colors.GOLD)
        else:
            # Draw your new custom next.png sprite over the slide layer
            next_btn = assets._cache.get("btn_next")
            if next_btn:
                scaled_btn = pygame.transform.smoothscale(next_btn, (self._intro_btn_rect.width, self._intro_btn_rect.height))
                surface.blit(scaled_btn, self._intro_btn_rect)
            else:
                # Text fallback if image can't be fetched
                self._draw_button(surface, self._intro_btn_rect, "Next", primary=True)

    def handle_intro_click(self, pos: tuple, current_slide: int) -> str:
        """Process navigation interactions on the story deck overlay."""
        if getattr(self, '_intro_btn_rect', None) and self._intro_btn_rect.collidepoint(pos):
            if current_slide >= 6:
                return "start_difficulty"
            return "next_slide"
        return None
        
    
    # ==================== OPTIONS SCREEN ====================
    def render_options(self, surface: pygame.Surface, volume: int):
        self._draw_sky_background(surface)
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

        panel_rect = pygame.Rect(cx - 260, cy - 160, 520, 300)
        # Assuming you kept _draw_main_panel for the blue box
        if hasattr(self, '_draw_main_panel'):
            self._draw_main_panel(surface, panel_rect)
        else:
            pygame.draw.rect(surface, (88, 138, 198), panel_rect, border_radius=6)
            pygame.draw.rect(surface, Colors.GOLD, panel_rect, width=4, border_radius=6)

        title = self._title_font.render("OPTIONS", True, Colors.GOLD)
        surface.blit(title, title.get_rect(centerx=cx, centery=panel_rect.top + 50))

        vol_label = self._sub_font.render("MASTER VOLUME", True, (210, 190, 150))
        surface.blit(vol_label, vol_label.get_rect(centerx=cx, centery=panel_rect.top + 120))

        # Volume controls
        vol_y = panel_rect.top + 160
        self._vol_down_rect = pygame.Rect(cx - 90, vol_y - 20, 40, 40)
        self._draw_button(surface, self._vol_down_rect, "-", primary=True)

        vol_text = self._stat_font.render(f"{volume}%", True, Colors.WHITE)
        surface.blit(vol_text, vol_text.get_rect(centerx=cx, centery=vol_y))

        self._vol_up_rect = pygame.Rect(cx + 50, vol_y - 20, 40, 40)
        self._draw_button(surface, self._vol_up_rect, "+", primary=True)

        # Back Button
        self._opt_back_rect = pygame.Rect(cx - 80, panel_rect.bottom - 70, 160, 48)
        self._draw_sprite_button(surface, "back", self._opt_back_rect)

    def handle_options_click(self, pos: tuple) -> str:
        if getattr(self, '_opt_back_rect', None) and self._opt_back_rect.collidepoint(pos):
            return "back"
        if getattr(self, '_vol_down_rect', None) and self._vol_down_rect.collidepoint(pos):
            return "voldown"
        if getattr(self, '_vol_up_rect', None) and self._vol_up_rect.collidepoint(pos):
            return "volup"
        return None

    # ==================== CREDITS SCREEN ====================
    # ==================== CREDITS SCREEN ====================
    def render_credits(self, surface: pygame.Surface):
        self._draw_sky_background(surface)
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

        panel_rect = pygame.Rect(cx - 350, cy - 280, 700, 560)
        if hasattr(self, '_draw_main_panel'):
            self._draw_main_panel(surface, panel_rect)
        else:
            pygame.draw.rect(surface, (88, 138, 198), panel_rect, border_radius=6)
            pygame.draw.rect(surface, Colors.GOLD, panel_rect, width=4, border_radius=6)

        title = self._title_font.render("CREDITS", True, Colors.GOLD)
        surface.blit(title, title.get_rect(centerx=cx, centery=panel_rect.top + 45))

        # UPDATED: Assigned specific roles based on user input, and separate roles from names
        credits_list = [
            ("Cookie Delivery Dash", Colors.GOLD),
            ("", Colors.WHITE),
            ("Lead Programmers & AI Logic:", (150, 200, 255)),
            ("Phillip Dylan Garcia", Colors.WHITE),
            ("John Eric Samillano", Colors.WHITE),
            ("", Colors.WHITE),
            ("Lead Artist & Asset Curation:", (150, 200, 255)),
            ("Clarissa May Alejandro", Colors.WHITE),
            ("", Colors.WHITE),
            ("Game Concept, QA & Testing:", (150, 200, 255)),
            ("Krisdel Ybañez", Colors.WHITE),
            ("", Colors.WHITE),
            ("Intro to Artificial Intelligence", (210, 190, 150)),
            ("Case Study 1", (210, 190, 150))
        ]

        y_offset = panel_rect.top + 80
        for line, color in credits_list:
            text = self._cred_font.render(line, True, color)
            # Add a slight shadow for depth
            shadow = self._cred_font.render(line, True, (40, 40, 60))
            surface.blit(shadow, shadow.get_rect(centerx=cx + 2, top=y_offset + 2))
            surface.blit(text, text.get_rect(centerx=cx, top=y_offset))
            y_offset += 26

        # Draw floating animated assets on the sides!
        import math
        time_ms = pygame.time.get_ticks()
        float_y1 = math.sin(time_ms / 400.0) * 10
        float_y2 = math.cos(time_ms / 350.0) * 10
        float_y3 = math.sin(time_ms / 500.0 + 1) * 10

        boy_img = assets.get("cred_boy")
        girl_img = assets.get("cred_girl")
        ai_img = assets.get("cred_ai")

        # Boy on the top left
        if boy_img:
            surface.blit(boy_img, (panel_rect.left - 80, panel_rect.top + 80 + float_y1))
        # Girl on the bottom left (flipped to face right)
        if girl_img:
            girl_flipped = pygame.transform.flip(girl_img, True, False)
            surface.blit(girl_flipped, (panel_rect.left - 80, panel_rect.centery + 20 + float_y2))
        # AI in the middle right side
        if ai_img:
            surface.blit(ai_img, (panel_rect.right - 50, panel_rect.centery - 60 + float_y3))

        self._cred_back_rect = pygame.Rect(cx - 80, panel_rect.bottom - 65, 160, 48)
        self._draw_sprite_button(surface, "back", self._cred_back_rect)

    def handle_credits_click(self, pos: tuple) -> str:
        if getattr(self, '_cred_back_rect', None) and self._cred_back_rect.collidepoint(pos):
            return "back"
        return None

    # ==================== DIFFICULTY SCREEN ====================
    def render_difficulty(self, surface: pygame.Surface):
        """Draw the difficulty selection screen with an expanded blue panel layout."""
        self._draw_sky_background(surface)

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        # ---> STRETCHED OUT: Increased width from 660 to 720 to match original proportions
        panel_w, panel_h = 720, 400
        panel_rect = pygame.Rect(cx - panel_w // 2, cy - panel_h // 2 - 25, panel_w, panel_h)
        self._draw_main_panel(surface, panel_rect)

        # Title text
        title = self._title_font.render("SELECT DIFFICULTY", True, Colors.GOLD)
        surface.blit(title, title.get_rect(centerx=cx, centery=panel_rect.top + 35))

        # Difficulty cards layout
        card_w, card_h = 176, 215
        # ---> SPACING TWEAK: Increased card gap from 16 to 24 for a stretched feel
        gap = 24
        total_w = 3 * card_w + 2 * gap
        start_x = cx - total_w // 2
        card_y = panel_rect.top + 65

        self._diff_rects.clear()
        for i, diff_key in enumerate([Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]):
            card_x = start_x + i * (card_w + gap)
            card_rect = pygame.Rect(card_x, card_y, card_w, card_h)
            self._diff_rects[diff_key] = card_rect

            # Draw the sliced mode card directly from assets
            mode_card = assets.get_mode_card(i)
            if mode_card:
                scaled_card = pygame.transform.smoothscale(mode_card, (card_w, card_h))
                surface.blit(scaled_card, card_rect)
            else:
                # Fallback layout if images fail to load
                is_selected = (diff_key == self.selected_difficulty)
                bg = (24, 39, 74) if is_selected else (14, 23, 47)
                border = Colors.GOLD if is_selected else (34, 52, 94)
                pygame.draw.rect(surface, bg, card_rect, border_radius=4)
                pygame.draw.rect(surface, border, card_rect, width=3, border_radius=4)

            # Selection highlight border frame
            is_selected = (diff_key == self.selected_difficulty)
            if is_selected:
                highlight_rect = card_rect.inflate(6, 6)
                pygame.draw.rect(surface, Colors.GOLD, highlight_rect, width=3, border_radius=6)

        # Buttons position matching the lower layout of the mockup
        btn_w, btn_h = 160, 48
        btn_y = panel_rect.bottom - 70
        # ---> SPACING TWEAK: Increased button separation gap for better alignment
        btn_gap = 60

        # Back button position
        self._back_rect = pygame.Rect(cx - btn_w - btn_gap // 2, btn_y, btn_w, btn_h)
        self._draw_sprite_button(surface, "back", self._back_rect)

        # Start button position
        self._play_rect = pygame.Rect(cx + btn_gap // 2, btn_y, btn_w, btn_h)
        self._draw_sprite_button(surface, "start", self._play_rect)

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
        """Draw the end/results screen with Frame 1 background and brown panel."""
        self._draw_sky_background(surface)

        cx = WINDOW_WIDTH // 2

        # Draw brown panel (expanded)
        panel_w, panel_h = 580, 460
        panel_rect = pygame.Rect(cx - panel_w // 2, 40, panel_w, panel_h)
        self._draw_brown_panel(surface, panel_rect)

        # Winner icon (use icon sprites)
        winner_text = results.get("winner_text", "Game Over")
        if "You" in winner_text:
            winner_icon = assets.get_icon("human")
        else:
            winner_icon = assets.get_icon("robot")

        if winner_icon:
            icon_size = 70
            scaled_icon = pygame.transform.smoothscale(winner_icon, (icon_size, icon_size))
            icon_rect = scaled_icon.get_rect(centerx=cx, centery=panel_rect.top + 55)
            surface.blit(scaled_icon, icon_rect)

        # Winner text
        winner = self._title_font.render(winner_text, True, Colors.GOLD)
        surface.blit(winner, winner.get_rect(centerx=cx, centery=panel_rect.top + 110))

        # Stats grid (2 columns × 3 rows) — symmetric layout
        stats = [
            ("YOUR SCORE", str(results.get("human_score", 0)), Colors.BLUE),
            ("AI SCORE", str(results.get("ai_score", 0)), Colors.PURPLE),
            ("YOUR PI", str(results.get("human_pi", "0")), Colors.BLUE),
            ("AI PI", str(results.get("ai_pi", "0")), Colors.PURPLE),
            ("YOUR TIME", results.get("human_time", "0:00"), Colors.BLUE),
            ("AI TIME", results.get("ai_time", "0:00"), Colors.PURPLE),
        ]

        padding = 30          # padding from panel edges
        col_gap = 12          # gap between columns
        stat_h = 55
        row_gap = 10
        stat_w = (panel_w - 2 * padding - col_gap) // 2
        stat_start_y = panel_rect.top + 145

        for idx, (label, value, color) in enumerate(stats):
            col = idx % 2
            row = idx // 2
            sx = panel_rect.left + padding + col * (stat_w + col_gap)
            sy = stat_start_y + row * (stat_h + row_gap)
            stat_rect = pygame.Rect(sx, sy, stat_w, stat_h)

            pygame.draw.rect(surface, Colors.DEEP, stat_rect, border_radius=10)
            pygame.draw.rect(surface, Colors.BORDER, stat_rect, width=1, border_radius=10)

            # Label
            lbl = self._small_font.render(label, True, Colors.MUTED)
            surface.blit(lbl, (sx + 14, sy + 8))

            # Value
            val = self._stat_font.render(value, True, color)
            surface.blit(val, (sx + 14, sy + 26))

        # Algorithm description section
        algo_y = stat_start_y + 3 * (stat_h + row_gap) + 10
        algo_name = results.get("algo_name", "")
        algo_desc = results.get("algo_desc", "")

        if algo_name and algo_y + 60 < panel_rect.bottom:
            # Divider line
            pygame.draw.line(surface, Colors.BORDER,
                            (panel_rect.left + 30, algo_y),
                            (panel_rect.right - 30, algo_y), 1)
            algo_y += 12

            algo_title = self._sub_font.render(
                f"AI Algorithm: {algo_name}", True, Colors.GOLD
            )
            surface.blit(algo_title,
                         algo_title.get_rect(centerx=cx, top=algo_y))
            algo_y += 22

            for line in algo_desc.split("\n"):
                desc = self._small_font.render(line, True, (210, 190, 150))
                surface.blit(desc, desc.get_rect(centerx=cx, top=algo_y))
                algo_y += 16

        # Buttons row using sprite buttons
        btn_w, btn_h = 130, 44
        btn_y = panel_rect.bottom + 16
        btn_gap = 12
        total_btn_w = 4 * btn_w + 3 * btn_gap
        btn_start_x = cx - total_btn_w // 2

        # Menu button
        self._menu_rect = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
        self._draw_sprite_button(surface, "menu", self._menu_rect)

        # View Maps button
        self._review_rect = pygame.Rect(btn_start_x + btn_w + btn_gap, btn_y, btn_w, btn_h)
        self._draw_sprite_button(surface, "view_maps", self._review_rect)

        # BFS Check button
        self._bfs_viz_rect = pygame.Rect(btn_start_x + 2 * (btn_w + btn_gap), btn_y, btn_w, btn_h)
        # Tweak BFS button render rect so it matches the other buttons visually (it lacks image padding)
        bfs_render_rect = pygame.Rect(0, 0, 120, 32)
        bfs_render_rect.center = self._bfs_viz_rect.center
        bfs_render_rect.y -= 2
        self._draw_sprite_button(surface, "BFS_button", bfs_render_rect)

        # Play Again button
        self._again_rect = pygame.Rect(btn_start_x + 3 * (btn_w + btn_gap), btn_y, btn_w, btn_h)
        self._draw_sprite_button(surface, "play_again", self._again_rect)

    def handle_end_click(self, pos: tuple) -> str:
        """Handle click on end screen. Returns 'title', 'game', 'review', 'bfs_viz', or None."""
        if self._menu_rect and self._menu_rect.collidepoint(pos):
            return "title"
        if self._again_rect and self._again_rect.collidepoint(pos):
            return "game"
        if self._review_rect and self._review_rect.collidepoint(pos):
            return "review"
        if getattr(self, '_bfs_viz_rect', None) and self._bfs_viz_rect.collidepoint(pos):
            return "bfs_viz"
        return None

    def render_review(self, surface: pygame.Surface, results: dict, speed_label: str = "1x"):
        """Draw UI elements for the review screen (algorithm description & back button)."""
        cx = WINDOW_WIDTH // 2

        # Position below the grids (grids end at ~430px with review_grid_px=380 + grid_y=50)
        card_w = 600
        card_h = 90
        card_y = WINDOW_HEIGHT - 160
        card_rect = pygame.Rect(cx - card_w // 2, card_y, card_w, card_h)
        pygame.draw.rect(surface, Colors.CARD, card_rect, border_radius=12)
        pygame.draw.rect(surface, Colors.BORDER, card_rect, width=1, border_radius=12)

        algo_name = results.get("algo_name", "")
        algo_desc = results.get("algo_desc", "")

        algo_title = self._sub_font.render(f"AI Algorithm: {algo_name}", True, Colors.GOLD)
        surface.blit(algo_title, algo_title.get_rect(centerx=cx, top=card_rect.top + 8))

        y = card_rect.top + 30
        for line in algo_desc.split("\n"):
            desc = self._small_font.render(line, True, (210, 190, 150))
            surface.blit(desc, desc.get_rect(centerx=cx, top=y))
            y += 15

        # Buttons
        btn_y = card_rect.bottom + 10
        btn_w, btn_h = 140, 42

        self._review_back_rect = pygame.Rect(cx - 150, btn_y, btn_w, btn_h)
        self._draw_sprite_button(surface, "back", self._review_back_rect)

        self._review_speed_rect = pygame.Rect(cx + 10, btn_y, btn_w, btn_h)
        self._draw_button(surface, self._review_speed_rect, f"Speed: {speed_label}", primary=False)

    def handle_review_click(self, pos: tuple) -> str:
        """Handle click on review screen. Returns 'end', 'speed', or None."""
        if self._review_back_rect and self._review_back_rect.collidepoint(pos):
            return "end"
        if getattr(self, '_review_speed_rect', None) and self._review_speed_rect.collidepoint(pos):
            return "speed"
        return None

    def render_bfs_viz_buttons(self, surface: pygame.Surface):
        """Draw buttons for the BFS visualization screen."""
        cx = WINDOW_WIDTH // 2
        btn_y = WINDOW_HEIGHT - 60
        btn_w, btn_h = 140, 42
        
        self._bfs_back_rect = pygame.Rect(cx - 150, btn_y, btn_w, btn_h)
        self._draw_sprite_button(surface, "back", self._bfs_back_rect)
        
        self._bfs_restart_rect = pygame.Rect(cx + 10, btn_y, btn_w, btn_h)
        self._draw_button(surface, self._bfs_restart_rect, "Restart", primary=False)

    def handle_bfs_viz_click(self, pos: tuple) -> str:
        """Handle click on BFS viz screen. Returns 'end', 'restart', or None."""
        if getattr(self, '_bfs_back_rect', None) and self._bfs_back_rect.collidepoint(pos):
            return "end"
        if getattr(self, '_bfs_restart_rect', None) and self._bfs_restart_rect.collidepoint(pos):
            return "restart"
        return None

    # ==================== STARS (fallback) ====================
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
        font_path = resource_path("assets/fonts/PressStart2P-Regular.ttf")
        try:
            self._font = pygame.font.Font(font_path, 10)
        except Exception:
            try:
                self._font = pygame.font.SysFont("segoeuisymbol", 16, bold=True)
            except Exception:
                self._font = pygame.font.Font(None, 18)

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
