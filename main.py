"""
main.py — Entry point for Cookie Dash Pygame application.
Manages the game loop, screen state machine, events, and timing.
Translated from startGame(), keyboard handler, and game intervals in the HTML source.
"""

import sys
import pygame
from setting import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, GAME_TITLE,
    Colors, GRID_PX, SIZE, TILE_SIZE, TILE_GAP, GRID_PADDING,
    DIFFICULTY_CONFIG,
)
from core.map_gen import generate_map
from core.player import Player
from core.ai import AIAgent
from ui.renderer import GridRenderer
from ui.hud import HUD
from ui.screens import ScreenManager, NotificationManager
from variants.scoring import calculate_results
from utils.helper import format_time


class Game:
    """Main game controller — state machine and pygame loop."""

    # Screen states
    TITLE      = "title"
    DIFFICULTY = "difficulty"
    PLAYING    = "game"
    END        = "end"
    REVIEW     = "review"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()

        # UI components
        self.grid_renderer = GridRenderer()
        self.hud = HUD()
        self.screen_mgr = ScreenManager()
        self.notif = NotificationManager()

        # Game state
        self.state = self.TITLE
        self.game_map = None
        self.houses = None
        self.exit_pos = None
        self.human = None
        self.ai_player = None
        self.ai_agent = None
        self.elapsed = 0
        self.game_over = False
        self.final_countdown = False
        self.final_countdown_timer = 0.0
        self.results = None
        self.review_anim_index = 1
        self.review_anim_timer = 0.0
        self.review_speeds = [0.2, 0.1, 0.05, 0.02]
        self.review_speed_labels = ["0.5x", "1x", "2x", "MAX"]
        self.review_speed_idx = 1
        self.notif = NotificationManager()

        # Timers
        self._second_timer = 0.0
        self._ai_timer = 0.0
        self._ai_speed = 0.8  # seconds per AI step

        self.shake_timer = 0.0

        self.running = True

    def start_game(self):
        """Initialize a new game session."""
        difficulty = self.screen_mgr.selected_difficulty

        # Generate map
        map_data = generate_map()
        self.game_map = map_data["grid"]
        self.houses = map_data["houses"]
        self.exit_pos = map_data["exit_pos"]

        # Initialize players
        self.human = Player(is_human=True)
        self.ai_player = Player(is_human=False)
        self.ai_agent = AIAgent(self.ai_player, self.game_map,
                                 self.houses, self.exit_pos)

        # Reveal starting vision for both
        start_visible = self.human.tiles_in_view(difficulty)
        self.human.add_revealed_tiles(start_visible)
        self.ai_player.add_revealed_tiles(
            self.ai_player.tiles_in_view(difficulty)
        )

        # Reset state
        self.elapsed = 0
        self.game_over = False
        self.final_countdown = False
        self.final_countdown_timer = 0.0
        self.results = None
        self._second_timer = 0.0
        self._ai_timer = 0.0


        # AI speed from difficulty config
        ai_speed_ms = DIFFICULTY_CONFIG[difficulty]["ai_speed_ms"]
        self._ai_speed = ai_speed_ms / 1000.0

        # Reset HUD log
        self.hud.clear_log()
        self.hud.add_log(format_time(0),
                         "🍪 Game started! Deliver cookies to all 3 houses, then find the exit!",
                         "system")

        self.state = self.PLAYING

    def _process_events(self, events_list: list):
        """Process event dicts from player/AI movement."""
        for event in events_list:
            if event["type"] in ("penalty", "delivery", "bonus", "finish"):
                self.notif.show(event.get("msg", ""))
                self.hud.add_log(format_time(self.elapsed),
                                 event.get("log", ""),
                                 event.get("log_type", "system"))
                
            if event["type"] == "penalty" and event.get("log_type") != "ai":
                self.shake_timer = 0.3  # seconds to shake screen

            if event["type"] == "finish":
                self._check_game_over()

    def _check_game_over(self):
        """Check if the game should end."""
        h_done = self.human.finished
        a_done = self.ai_player.finished

        if not h_done and not a_done:
            return

        if h_done and a_done:
            self._end_game()
            return

        # One finished — start grace period
        if not self.final_countdown:
            self.final_countdown = True
            self.final_countdown_timer = 0.0
            winner = "You" if h_done else "AI"
            self.hud.add_log(format_time(self.elapsed),
                             f"{winner} finished! Game ending in 2 seconds...",
                             "system")

    def _end_game(self):
        """End the game and calculate results."""
        self.game_over = True
        difficulty = self.screen_mgr.selected_difficulty
        self.results = calculate_results(self.human, self.ai_player, self.elapsed, difficulty)
        # Short delay before showing end screen
        self._end_delay = 1.0

    def handle_events(self):
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

            if event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

    def _handle_click(self, pos):
        """Route clicks to the active screen."""
        if self.state == self.TITLE:
            result = self.screen_mgr.handle_title_click(pos)
            if result == "difficulty":
                self.state = self.DIFFICULTY

        elif self.state == self.DIFFICULTY:
            result = self.screen_mgr.handle_difficulty_click(pos)
            if result == "game":
                self.start_game()
            elif result == "title":
                self.state = self.TITLE

        elif self.state == self.END:
            result = self.screen_mgr.handle_end_click(pos)
            if result == "title":
                self.state = self.TITLE
            elif result == "game":
                self.start_game()
            elif result == "review":
                self.state = self.REVIEW
                self.review_anim_index = 1
                self.review_anim_timer = 0.0
                self.review_paused = True

        elif self.state == self.REVIEW:
            result = self.screen_mgr.handle_review_click(pos)
            if result == "end":
                self.state = self.END
            elif result == "speed":
                self.review_speed_idx = (self.review_speed_idx + 1) % len(self.review_speeds)

    def _handle_key(self, key):
        """Handle keyboard input during gameplay."""
        if self.state == self.REVIEW:
            if key == pygame.K_SPACE:
                self.review_paused = not getattr(self, 'review_paused', True)
            elif key == pygame.K_RIGHT:
                self.review_paused = True
                max_len = max(len(self.human.path_history), len(self.ai_agent.replay_log))
                if self.review_anim_index < max_len:
                    self.review_anim_index += 1
            elif key == pygame.K_LEFT:
                self.review_paused = True
                if self.review_anim_index > 1:
                    self.review_anim_index -= 1
            return

        if self.state != self.PLAYING or self.game_over:
            return

        # Arrow keys and WASD mapping
        key_map = {
            pygame.K_UP:    (0, -1),
            pygame.K_DOWN:  (0, 1),
            pygame.K_LEFT:  (-1, 0),
            pygame.K_RIGHT: (1, 0),
            pygame.K_w:     (0, -1),
            pygame.K_s:     (0, 1),
            pygame.K_a:     (-1, 0),
            pygame.K_d:     (1, 0),
        }

        if key in key_map:
            dx, dy = key_map[key]
            difficulty = self.screen_mgr.selected_difficulty
            game_state = {"elapsed": self.elapsed}
            events = self.human.move(dx, dy, self.game_map, difficulty, game_state)
            self._process_events(events)

    def update(self, dt: float):
        """Update game logic each frame."""
        self.notif.update(dt)

        if self.shake_timer > 0:
            self.shake_timer -= dt

        if self.state == self.REVIEW:
            if not getattr(self, 'review_paused', True):
                self.review_anim_timer += dt
                speed_delay = self.review_speeds[self.review_speed_idx]
                if self.review_anim_timer >= speed_delay:
                    self.review_anim_timer -= speed_delay
                    max_len = max(len(self.human.path_history), len(self.ai_agent.replay_log))
                    if self.review_anim_index < max_len:
                        self.review_anim_index += 1
            return

        if self.state != self.PLAYING:
            return

        if self.game_over:
            # Delay before showing end screen
            if hasattr(self, '_end_delay'):
                self._end_delay -= dt
                if self._end_delay <= 0:
                    self.state = self.END
                    del self._end_delay
            return

        # Update timer (1 second tick)
        self._second_timer += dt
        if self._second_timer >= 1.0:
            self._second_timer -= 1.0
            self.elapsed += 1

        # Update AI movement
        self._ai_timer += dt
        if self._ai_timer >= self._ai_speed:
            self._ai_timer -= self._ai_speed
            difficulty = self.screen_mgr.selected_difficulty
            game_state = {"elapsed": self.elapsed}
            events = self.ai_agent.step(difficulty, game_state)
            self._process_events(events)

        # Grace period countdown
        if self.final_countdown:
            self.final_countdown_timer += dt
            if self.final_countdown_timer >= 2.0:
                self._end_game()

        self.notif.update(dt)          

    def render(self):
        """Render the current screen."""
        dt = self.clock.get_time() / 1000.0

        if self.state == self.TITLE:
            self.screen_mgr.render_title(self.screen, dt)

        elif self.state == self.DIFFICULTY:
            self.screen_mgr.render_difficulty(self.screen)

        elif self.state == self.PLAYING:
            self._render_game()

        elif self.state == self.END:
            if self.results:
                self.screen_mgr.render_end(self.screen, self.results)

        elif self.state == self.REVIEW:
            self._render_review()

        # Always render notification on top
        self.notif.render(self.screen)

        pygame.display.flip()
        

    def _render_game(self):
        """Render the gameplay screen with only human grid visible."""
        self.screen.fill(Colors.NIGHT)
        self.screen_mgr._draw_stars(self.screen)

        self.hud.render(self.screen, self.human, self.ai_player, self.elapsed, y_offset=10)

        # Calculate grid positions (centered, single grid)
        start_x = (WINDOW_WIDTH - GRID_PX) // 2
        grid_y = 90

        shake_x, shake_y = 0, 0
        if self.shake_timer > 0:
            import random
            intensity = int(self.shake_timer * 25) # More time = bigger shake
            shake_x = random.randint(-intensity, intensity)
            shake_y = random.randint(-intensity, intensity)

        # Apply the shake offset to the render coordinates
            render_x = start_x + shake_x
            render_y = grid_y + shake_y

        if self.shake_timer > 0:
            # Create a surface that supports transparency (SRCALPHA)
            flash_surf = pygame.Surface((GRID_PX, GRID_PX), pygame.SRCALPHA)
            # Calculate alpha (transparency) so it fades out smoothly
            alpha = int((self.shake_timer / 0.3) * 200) 
            flash_surf.fill((*Colors.RED, alpha)) 
            # Draw it exactly over the shaking grid
            self.screen.blit(flash_surf, (render_x, render_y))
        try:
            label_font = pygame.font.SysFont("segoeuisymbol", 16, bold=True)
        except Exception:
            label_font = pygame.font.Font(None, 18)

        pygame.draw.circle(self.screen, Colors.BLUE, (start_x + 6, grid_y - 14), 5)
        lbl = label_font.render("Your View (AI is hidden in background)", True, Colors.MUTED)
        self.screen.blit(lbl, (start_x + 18, grid_y - 22))

        self.grid_renderer.render(
            self.screen, start_x, grid_y,
            self.human, self.game_map, is_human=True
        )

        try:
            hint_font = pygame.font.SysFont("segoeuisymbol", 11)
        except Exception:
            hint_font = pygame.font.Font(None, 13)
        hint = hint_font.render("Arrow keys or WASD to move", True, Colors.MUTED)
        self.screen.blit(hint, hint.get_rect(centerx=start_x + GRID_PX // 2, top=grid_y + GRID_PX + 8))

        log_y = grid_y + GRID_PX + 30
        self.hud.render_log(self.screen, log_y, max_height=100)

    def _render_review(self):
        """Render the review screen showing both maps fully revealed with paths."""
        self.screen.fill(Colors.NIGHT)
        self.screen_mgr._draw_stars(self.screen)

        gap = 30
        total_w = GRID_PX * 2 + gap
        start_x = (WINDOW_WIDTH - total_w) // 2
        grid_y = 60

        try:
            label_font = pygame.font.SysFont("segoeuisymbol", 16, bold=True)
            hint_font = pygame.font.SysFont("segoeuisymbol", 14)
        except Exception:
            label_font = pygame.font.Font(None, 18)
            hint_font = pygame.font.Font(None, 16)

        # Human map
        pygame.draw.circle(self.screen, Colors.BLUE, (start_x + 6, grid_y - 14), 5)
        lbl = label_font.render("Your Path", True, Colors.MUTED)
        self.screen.blit(lbl, (start_x + 18, grid_y - 22))

        h_path = self.human.path_history[:min(self.review_anim_index, len(self.human.path_history))]

        self.grid_renderer.render(
            self.screen, start_x, grid_y,
            self.human, self.game_map, is_human=True, force_reveal=True,
            path_overlay=h_path, path_color=Colors.BLUE
        )

        # AI map
        ai_x = start_x + GRID_PX + gap
        pygame.draw.circle(self.screen, Colors.PURPLE, (ai_x + 6, grid_y - 14), 5)
        lbl = label_font.render("AI Path", True, Colors.MUTED)
        self.screen.blit(lbl, (ai_x + 18, grid_y - 22))

        a_log = self.ai_agent.replay_log[:min(self.review_anim_index, len(self.ai_agent.replay_log))]
        a_path = [entry['pos'] for entry in a_log]
        ai_brain_state = a_log[-1] if a_log else None

        self.grid_renderer.render(
            self.screen, ai_x, grid_y,
            self.ai_player, self.game_map, is_human=False, force_reveal=True,
            path_overlay=a_path, path_color=Colors.PURPLE,
            ai_brain_state=ai_brain_state
        )

        # Draw AI Brain panel below the AI map
        if ai_brain_state:
            panel_y = grid_y + GRID_PX + 10
            panel_rect = pygame.Rect(ai_x, panel_y, GRID_PX, 95)
            pygame.draw.rect(self.screen, Colors.DEEP, panel_rect, border_radius=8)
            pygame.draw.rect(self.screen, Colors.BORDER, panel_rect, width=2, border_radius=8)

            try:
                b_font = pygame.font.SysFont("segoeuisymbol", 12)
                t_font = pygame.font.SysFont("segoeuisymbol", 14, bold=True)
            except Exception:
                b_font = pygame.font.Font(None, 16)
                t_font = pygame.font.Font(None, 18)

            title = t_font.render("🤖 AI STATUS", True, Colors.GOLD)
            self.screen.blit(title, (ai_x + 10, panel_y + 8))
            
            target_str = str(ai_brain_state.get('target', 'None'))
            h_str = str(ai_brain_state.get('h_n', 0))
            state_str = ai_brain_state.get('state', 'Unknown')
            pruned_count = len(ai_brain_state.get('pruned', set()))
            visited_count = len(ai_brain_state.get('visited', set()))
            stuck_count = ai_brain_state.get('stuck_counter', 0)

            lines = [
                f"Goal: {target_str}   h(n): {h_str}",
                f"State: {state_str}",
                f"Pruned: {pruned_count}   Visited: {visited_count}   Backtracks: {stuck_count}"
            ]
            
            py = panel_y + 30
            for l in lines:
                l_surf = b_font.render(l, True, Colors.MUTED)
                self.screen.blit(l_surf, (ai_x + 10, py))
                py += 20

        # Draw Pause/Play status
        status_text = "Paused (Space to play, Right/Left to step)" if getattr(self, 'review_paused', False) else "Playing (Space to pause)"
        status_surf = hint_font.render(status_text, True, Colors.MUTED)
        self.screen.blit(status_surf, (WINDOW_WIDTH//2 - status_surf.get_width()//2, grid_y - 45))

        # Call screen manager to draw the review UI (back button and AI explanation)
        speed_label = self.review_speed_labels[self.review_speed_idx]
        self.screen_mgr.render_review(self.screen, self.results, speed_label)

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
