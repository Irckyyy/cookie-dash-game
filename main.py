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
    DIFFICULTY_CONFIG, Tile
)
from core.map_gen import generate_map
from core.player import Player
from core.ai import AIAgent
from ui.renderer import GridRenderer
from ui.hud import HUD
from ui.screens import ScreenManager, NotificationManager
from variants.scoring import calculate_results
from utils.helper import format_time, resource_path
from ui.assets import assets


class Game:
    """Main game controller — state machine and pygame loop."""

    # Screen states
    TITLE      = "title"
    INTRO      = "intro"
    DIFFICULTY = "difficulty"
    PLAYING    = "game"
    END        = "end"
    REVIEW     = "review"   
    BFS_VIZ    = "bfs_viz"
    OPTIONS    = "options"
    CREDITS    = "credits"

    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()

        # Load all sprite assets (must happen after display init)
        assets.load_all(TILE_SIZE)

        try:
            pygame.mixer.music.load(resource_path("assets/sounds/MainMenu Music.wav"))
            pygame.mixer.music.set_volume(0.1)
            pygame.mixer.music.play(-1)  # Loop indefinitely

            self.sfx_click = pygame.mixer.Sound(resource_path("assets/sounds/click button.wav"))
            self.sfx_click.set_volume(0.3)

            self.sfx_delivery = pygame.mixer.Sound(resource_path("assets/sounds/successDel5.wav"))
            self.sfx_delivery.set_volume(0.3)

            self.sfx_exit = pygame.mixer.Sound(resource_path("assets/sounds/exit.wav"))
            self.sfx_exit.set_volume(0.4)

            self.sfx_road = pygame.mixer.Sound(resource_path("assets/sounds/hit road.wav"))
            self.sfx_road.set_volume(0.3)

            self.sfx_puddle = pygame.mixer.Sound(resource_path("assets/sounds/puddle.wav"))
            self.sfx_puddle.set_volume(0.3)

            self.sfx_win = pygame.mixer.Sound(resource_path("assets/sounds/winner.wav"))
            self.sfx_win.set_volume(0.15)

            self.sfx_lose = pygame.mixer.Sound(resource_path("assets/sounds/lose.wav"))
            self.sfx_lose.set_volume(0.5)

            self.sfx_bfs = pygame.mixer.Sound(resource_path("assets/sounds/bfsclick.mp3"))
            self.sfx_bfs.set_volume(0.3)

        except Exception as e:
            print(f"Error loading music: {e}")  

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

        self.bfs_anim_index = 0
        self.bfs_anim_timer = 0.0
        self.bfs_paused = False

        # Timers
        self._second_timer = 0.0
        self._ai_timer = 0.0
        self._ai_speed = 0.8  # seconds per AI step

        self.shake_timer = 0.0

        self.state = self.TITLE
        self.current_intro_slide = 2
        self.story_already_viewed = False 
        self.master_volume = 10

        self.running = True

    def set_volume(self, volume: int):
        """Dynamically adjusts the master volume of all game sounds."""
        self.master_volume = max(0, min(100, volume))
        v = self.master_volume / 100.0
        try:
            pygame.mixer.music.set_volume(0.2 * v)
            for sfx in ['sfx_click', 'sfx_delivery', 'sfx_exit', 'sfx_road', 'sfx_puddle', 'sfx_win', 'sfx_lose', 'sfx_scan']:
                s = getattr(self, sfx, None)
                if s:
                    s.set_volume(0.8 * v)
        except Exception:
            pass

    def start_game(self):
        """Initialize a new game session."""
        difficulty = self.screen_mgr.selected_difficulty

        # Generate map
        map_data = generate_map()
        self.game_map = map_data["grid"]
        self.houses = map_data["houses"]
        self.exit_pos = map_data["exit_pos"]
        self.bfs_trace = map_data.get("bfs_trace", [])
        self.safe_tiles = self.bfs_trace[-1]['visited'] if self.bfs_trace else set()
        start_pos = map_data.get("start_pos", (0, 0))

        # Initialize players
        self.human = Player(is_human=True, start_pos=start_pos)
        self.ai_player = Player(is_human=False, start_pos=start_pos)
        self.ai_agent = AIAgent(self.ai_player, self.game_map,
                                 self.houses, self.exit_pos)

        # Reveal starting vision for both
        start_visible = self.human.tiles_in_view(difficulty)
        self.human.add_revealed_tiles(start_visible)
        self.ai_player.add_revealed_tiles(
            self.ai_player.tiles_in_view(difficulty)
        )

        # Spawn batteries (flashlight pickups) on empty safe tiles
        all_safe_empty = [pos for pos in self.safe_tiles 
                          if self.game_map[pos[1]][pos[0]] == Tile.EMPTY 
                          and pos != start_pos]
        import random
        self.batteries = set(random.sample(all_safe_empty, min(3, len(all_safe_empty))))

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
                         "Game started! Deliver cookies to all 3 houses, then find the exit!",
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

            # Delivery
            if event["type"] == "delivery":
                if event.get("log_type") != "ai" and getattr(self, 'sfx_delivery', None):
                    self.sfx_delivery.play()

            # Penatly
            elif event["type"] == "penalty":
                # We only play damage sounds and shake the screen for the Human player
                if event.get("log_type") != "ai":
                    msg = event.get("msg", "").lower()
                    
                    if "puddle" in msg and getattr(self, 'sfx_puddle', None):
                        self.sfx_puddle.play()
                    elif "broken" in msg and getattr(self, 'sfx_road', None):
                        self.sfx_road.play()
                        
                    self.shake_timer = 0.3  # seconds to shake screen

            # Exit
            elif event["type"] == "finish":
                if event.get("log_type") != "ai" and getattr(self, 'sfx_exit', None):
                    self.sfx_exit.play()
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
            
            if h_done and getattr(self, 'sfx_win', None):
                self.sfx_win.play()
            elif a_done and getattr(self, 'sfx_lose', None):
                self.sfx_lose.play()

            winner = "You" if h_done else "AI"
            self.hud.add_log(format_time(self.elapsed),
                             f"{winner} finished! Game ending in 2 seconds...",
                             "system")

    def _end_game(self):
        """End the game and calculate results."""
        self.game_over = True
        
        # Lock in the official results 
        difficulty = self.screen_mgr.selected_difficulty
        self.results = calculate_results(self.human, self.ai_player, self.elapsed, difficulty)

        if self.results:
            self.results["human_raw"] = {
                "tiles": len(self.human.revealed_tiles),
                "deliveries": self.human.deliveries,
                # If your Player class tracks penalties via a dictionary or count, 
                # we fallback safely using getattr or standard properties:
                "puddles": getattr(self.human, 'puddles_hit', 0) if hasattr(self.human, 'puddles_hit') else getattr(self.human, 'puddles', 0),
                "roads": getattr(self.human, 'broken_roads_hit', 0) if hasattr(self.human, 'broken_roads_hit') else getattr(self.human, 'broken_roads', 0),
                "time": max(1, self.elapsed)
            }
            self.results["ai_raw"] = {
                "tiles": len(self.ai_player.revealed_tiles),
                "deliveries": self.ai_player.deliveries,
                "puddles": getattr(self.ai_player, 'puddles_hit', 0) if hasattr(self.ai_player, 'puddles_hit') else getattr(self.ai_player, 'puddles', 0),
                "roads": getattr(self.ai_player, 'broken_roads_hit', 0) if hasattr(self.ai_player, 'broken_roads_hit') else getattr(self.ai_player, 'broken_roads', 0),
                "time": max(1, self.ai_player.end_time if getattr(self.ai_player, 'end_time', 0) > 0 else self.elapsed)
            }

        # Auto-complete the AI's path for the Replay
        if not self.ai_player.finished and self.ai_agent:
            safeguard = 0
            # Fast-forward the AI instantly (max 500 steps to prevent freezing)
            while not self.ai_player.finished and safeguard < 500:
                self.ai_agent.step(difficulty, {"elapsed": self.elapsed})
                safeguard += 1
                
            # Tag the final frame so the Replay screen explains what happened
            if self.ai_agent.replay_log:
                self.ai_agent.replay_log[-1]['state'] = "Ghost Path (Auto-Completed)"
                self.ai_agent.replay_log[-1]['reason'] = "You won! This is the path it would have taken."

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
        # Initialize the variable at the top so it always exists!
        button_clicked = False

        if self.state == self.TITLE:
            result = self.screen_mgr.handle_title_click(pos)
            if result:
                button_clicked = True  # Play sound if a button was clicked
            if result == "difficulty":
                # ---> CHANGED: Go to intro deck if unread, otherwise skip to settings
                if not getattr(self, 'story_already_viewed', False):
                    self.state = "intro"
                    self.current_intro_slide = 2
                else:
                    self.state = self.DIFFICULTY
            elif result == "quit":
                self.running = False
            elif result == "options":
                self.state = self.OPTIONS
            elif result == "credits":
                self.state = self.CREDITS

        # ---> NEW: HANDOFF MOUSE INTERACTIONS DURING THE INTRO
        elif self.state == "intro":
            result = self.screen_mgr.handle_intro_click(pos, self.current_intro_slide)
            if result:
                button_clicked = True
            if result == "next_slide":
                self.current_intro_slide += 1
            elif result == "start_difficulty":
                self.story_already_viewed = True  # Mark it read so it only shows once!
                self.state = self.DIFFICULTY

        elif self.state == self.DIFFICULTY:
            result = self.screen_mgr.handle_difficulty_click(pos)
            
            # Check if a card was clicked to play sound on difficulty cards
            card_clicked = any(rect.collidepoint(pos) for rect in self.screen_mgr._diff_rects.values())
            if result or card_clicked:
                button_clicked = True
                
            if result == "game":
                self.start_game()
            elif result == "title":
                self.state = self.TITLE

        elif self.state == self.OPTIONS:
            result = self.screen_mgr.handle_options_click(pos)
            if result:
                button_clicked = True
            if result == "back":
                self.state = self.TITLE
            elif result == "voldown":
                self.set_volume(self.master_volume - 10)
            elif result == "volup":
                self.set_volume(self.master_volume + 10)

        elif self.state == self.CREDITS:
            result = self.screen_mgr.handle_credits_click(pos)
            if result:
                button_clicked = True
            if result == "back":
                self.state = self.TITLE

        elif self.state == self.END:
            result = self.screen_mgr.handle_end_click(pos)
            if result:
                button_clicked = True
            if result == "title":
                self.state = self.TITLE
            elif result == "game":
                self.start_game()
            elif result == "review":
                self.state = self.REVIEW
                self.review_anim_index = 1
                self.review_paused = True
            elif result == "bfs_viz":
                self.state = self.BFS_VIZ
                self.bfs_anim_index = 0
                self.bfs_paused = False

        elif self.state == self.REVIEW:
            result = self.screen_mgr.handle_review_click(pos)
            if result:
                button_clicked = True
            if result == "end":
                self.state = self.END
            elif result == "speed":
                self.review_speed_idx = (self.review_speed_idx + 1) % len(self.review_speeds)

        elif self.state == self.BFS_VIZ:
            result = self.screen_mgr.handle_bfs_viz_click(pos)
            if result:
                button_clicked = True
            if result == "end":
                self.state = self.END
            elif result == "restart":
                self.bfs_anim_index = 0
                self.bfs_anim_timer = 0.0
                self.bfs_paused = False

        if button_clicked and getattr(self, 'sfx_click', None):
            self.sfx_click.play()  

    def _handle_key(self, key):
        """Handle keyboard input during gameplay."""

        if self.state == self.INTRO:
            if key == pygame.K_SPACE:
                self.story_already_viewed = True
                self.state = self.DIFFICULTY
                if getattr(self, 'sfx_click', None):
                    self.sfx_click.play()
            return

        if self.state == self.BFS_VIZ:
            if key == pygame.K_SPACE:
                self.bfs_paused = not self.bfs_paused
            elif key == pygame.K_RIGHT:
                self.bfs_paused = True
                if self.bfs_anim_index < len(self.bfs_trace) - 1:
                    self.bfs_anim_index += 1
            elif key == pygame.K_LEFT:
                self.bfs_paused = True
                if self.bfs_anim_index > 0:
                    self.bfs_anim_index -= 1
            return

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
        
        if getattr(self, 'human', None) and getattr(self.human, 'is_backtracking', False):
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
            game_state = {"elapsed": self.elapsed, "safe_tiles": getattr(self, "safe_tiles", set())}
            events = self.human.move(dx, dy, self.game_map, difficulty, game_state)
            # Update player facing direction for sprite rendering
            dir_map = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}
            facing = dir_map.get((dx, dy))
            if facing:
                self.grid_renderer._human_facing = facing
            self._process_events(events)

            # Check battery collection
            if hasattr(self, 'batteries') and self.human.pos in self.batteries:
                self.batteries.remove(self.human.pos)
                from setting import DIFFICULTY_CONFIG
                self.human.flashlight_timer = DIFFICULTY_CONFIG[difficulty]["flashlight_duration"]
                self._process_events([{
                    "type": "bonus",
                    "msg": "Found a Battery! Flashlight active!",
                    "log": "You picked up a Battery!",
                    "log_type": "human"
                }])

    def update(self, dt: float):
        """Update game logic each frame."""
        self.notif.update(dt)

        if self.shake_timer > 0:
            self.shake_timer -= dt

        if hasattr(self, 'human') and getattr(self.human, 'is_backtracking', False):
            self.human.backtrack_timer -= dt
            if self.human.backtrack_timer <= 0:
                # Timer complete: smoothly move position back to the safe tile
                self.human.pos = self.human.backtrack_target
                self.human.is_backtracking = False
                
                # Re-reveal the visibility matrix on the safe tile
                difficulty = self.screen_mgr.selected_difficulty
                self.human.add_revealed_tiles(self.human.tiles_in_view(difficulty))
            return  # Freeze regular inputs while backing up

        # Proper AI Visual Backtracking Transition 
        if hasattr(self, 'ai_player') and getattr(self.ai_player, 'is_backtracking', False):
            self.ai_player.backtrack_timer -= dt
            if self.ai_player.backtrack_timer <= 0:
                # Timer complete: smoothly move AI position back to the safe tile
                self.ai_player.pos = self.ai_player.backtrack_target
                self.ai_player.is_backtracking = False
                
                # Re-reveal AI vision matrix
                difficulty = self.screen_mgr.selected_difficulty
                self.ai_player.add_revealed_tiles(self.ai_player.tiles_in_view(difficulty))
            return  # Freeze AI path steps while it finishes backing up

        if self.state == self.PLAYING:
            if getattr(self.human, 'flashlight_timer', 0) > 0:
                self.human.flashlight_timer -= dt
                if self.human.flashlight_timer < 0:
                    self.human.flashlight_timer = 0

        if self.state == self.BFS_VIZ:
            if not getattr(self, 'bfs_paused', False):
                self.bfs_anim_timer += dt
                if self.bfs_anim_timer >= 0.08:
                    self.bfs_anim_timer -= 0.08
                    if self.bfs_anim_index < len(self.bfs_trace) - 1:
                        self.bfs_anim_index += 1

                        if getattr(self, 'sfx_bfs', None):
                            self.sfx_bfs.play()
                            
                    else:
                        self.bfs_paused = True
            return

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
            game_state = {"elapsed": self.elapsed, "safe_tiles": self.safe_tiles}
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

        elif self.state == self.INTRO:
            self.screen_mgr.render_intro(self.screen, self.current_intro_slide)

        elif self.state == self.OPTIONS:
            self.screen_mgr.render_options(self.screen, self.master_volume)

        elif self.state == self.CREDITS:
            self.screen_mgr.render_credits(self.screen)

        elif self.state == self.DIFFICULTY:
            self.screen_mgr.render_difficulty(self.screen)

        elif self.state == self.DIFFICULTY:
            self.screen_mgr.render_difficulty(self.screen)

        elif self.state == self.PLAYING:
            self._render_game()

        elif self.state == self.END:
            if self.results:
                mouse_pos = pygame.mouse.get_pos()
                self.screen_mgr.render_end(self.screen, self.results, mouse_pos)

        elif self.state == self.REVIEW:
            self._render_review()

        elif self.state == self.BFS_VIZ:
            self._render_bfs_viz()

        # Always render notification on top
        self.notif.render(self.screen)

        pygame.display.flip()
        

    def _render_game(self):
        """Render the gameplay screen with only human grid visible."""
        self.screen_mgr._draw_sky_background(self.screen)

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
        lbl = label_font.render("Your View (AI is hidden in background)", True, Colors.WHITE)
        self.screen.blit(lbl, (start_x + 18, grid_y - 22))

        self.grid_renderer.render(
            self.screen, start_x, grid_y,
            self.human, self.game_map, is_human=True,
            difficulty=self.screen_mgr.selected_difficulty, batteries=getattr(self, 'batteries', set())
        )

        try:
            hint_font = pygame.font.SysFont("segoeuisymbol", 11)
        except Exception:
            hint_font = pygame.font.Font(None, 13)
        hint = hint_font.render("Arrow keys or WASD to move", True, Colors.WHITE)
        self.screen.blit(hint, hint.get_rect(centerx=start_x + GRID_PX // 2, top=grid_y + GRID_PX + 8))

        log_y = grid_y + GRID_PX + 30
        self.hud.render_log(self.screen, log_y, max_height=100)

    def _render_review(self):
        """Render the review screen showing both maps fully revealed with paths."""
        self.screen_mgr._draw_sky_background(self.screen)

        # Scale grids to fit everything in the window
        review_grid_px = 380
        gap = 24
        total_w = review_grid_px * 2 + gap
        start_x = (WINDOW_WIDTH - total_w) // 2
        grid_y = 50

        try:
            label_font = pygame.font.SysFont("segoeuisymbol", 15, bold=True)
            hint_font = pygame.font.SysFont("segoeuisymbol", 13)
        except Exception:
            label_font = pygame.font.Font(None, 17)
            hint_font = pygame.font.Font(None, 15)

        # Human map
        pygame.draw.circle(self.screen, Colors.BLUE, (start_x + 6, grid_y - 12), 5)
        lbl = label_font.render("Your Path", True, Colors.WHITE)
        self.screen.blit(lbl, (start_x + 16, grid_y - 20))

        h_path = self.human.path_history[:min(self.review_anim_index, len(self.human.path_history))]

        self.grid_renderer.render(
            self.screen, start_x, grid_y,
            self.human, self.game_map, is_human=True, force_reveal=True,
            path_overlay=h_path, path_color=Colors.BLUE,
            override_size=review_grid_px
        )

        # AI map
        ai_x = start_x + review_grid_px + gap
        pygame.draw.circle(self.screen, Colors.PURPLE, (ai_x + 6, grid_y - 12), 5)
        lbl = label_font.render("AI Path", True, Colors.WHITE)
        self.screen.blit(lbl, (ai_x + 16, grid_y - 20))

        a_log = self.ai_agent.replay_log[:min(self.review_anim_index, len(self.ai_agent.replay_log))]
        a_path = [entry['pos'] for entry in a_log]
        ai_brain_state = a_log[-1] if a_log else None

        self.grid_renderer.render(
            self.screen, ai_x, grid_y,
            self.ai_player, self.game_map, is_human=False, force_reveal=True,
            path_overlay=a_path, path_color=Colors.PURPLE,
            ai_brain_state=ai_brain_state,
            override_size=review_grid_px
        )

        # AI Status panel below the AI map
        panel_y = grid_y + review_grid_px + 8
        if ai_brain_state:
            panel_rect = pygame.Rect(ai_x, panel_y, review_grid_px, 80)
            pygame.draw.rect(self.screen, Colors.DEEP, panel_rect, border_radius=8)
            pygame.draw.rect(self.screen, Colors.BORDER, panel_rect, width=2, border_radius=8)

            try:
                b_font = pygame.font.SysFont("segoeuisymbol", 11)
                t_font = pygame.font.SysFont("segoeuisymbol", 13, bold=True)
            except Exception:
                b_font = pygame.font.Font(None, 15)
                t_font = pygame.font.Font(None, 17)

            title = t_font.render("AI STATUS", True, Colors.GOLD)
            self.screen.blit(title, (ai_x + 10, panel_y + 6))

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

            py = panel_y + 24
            for l in lines:
                l_surf = b_font.render(l, True, Colors.MUTED)
                self.screen.blit(l_surf, (ai_x + 10, py))
                py += 17

        # Pause/Play status
        status_text = "Paused (Space to play, Right/Left to step)" if getattr(self, 'review_paused', False) else "Playing (Space to pause)"
        status_surf = hint_font.render(status_text, True, Colors.WHITE)
        self.screen.blit(status_surf, (WINDOW_WIDTH//2 - status_surf.get_width()//2, grid_y - 35))

        # Review UI (algo card + buttons)
        speed_label = self.review_speed_labels[self.review_speed_idx]
        self.screen_mgr.render_review(self.screen, self.results, speed_label)

    def _render_bfs_viz(self):
        """Render the BFS validation visualization screen."""
        self.screen_mgr._draw_sky_background(self.screen)

        if not self.bfs_trace:
            return

        # Get current BFS state
        idx = min(self.bfs_anim_index, len(self.bfs_trace) - 1)
        state = self.bfs_trace[idx]
        visited = state['visited']
        frontier = state.get('frontier', [])
        current = state['current']
        found = state.get('found', set())
        found_this = state.get('found_this_step', None)
        new_neighbors = state.get('new_neighbors', [])

        # Grid dimensions — centered, large
        viz_grid_px = 480
        grid_x = (WINDOW_WIDTH - viz_grid_px) // 2
        grid_y = 65

        # Render the base grid with actual game assets (force reveal all)
        old_pos = self.human.pos
        self.human.pos = (-1, -1)  # Hide player
        self.grid_renderer.render(
            self.screen, grid_x, grid_y,
            self.human, self.game_map, is_human=True,
            force_reveal=True, path_overlay=None,
            override_size=viz_grid_px
        )
        self.human.pos = old_pos

        grid_padding = max(4, int(GRID_PADDING * viz_grid_px / GRID_PX))
        tile_gap = max(1, int(TILE_GAP * viz_grid_px / GRID_PX))
        tile_size = (viz_grid_px - grid_padding * 2 - (SIZE - 1) * tile_gap) // SIZE

        frontier_set = set(frontier)
        new_set = set(new_neighbors)

        try:
            h_font = pygame.font.SysFont("segoeuisymbol", 10)
            label_font = pygame.font.SysFont("segoeuisymbol", 15, bold=True)
            info_font = pygame.font.SysFont("segoeuisymbol", 14)
            title_font = pygame.font.SysFont("segoeuisymbol", 20, bold=True)
        except Exception:
            h_font = pygame.font.Font(None, 14)
            label_font = pygame.font.Font(None, 17)
            info_font = pygame.font.Font(None, 16)
            title_font = pygame.font.Font(None, 22)

        # Draw translucent color overlays for BFS state
        overlay_surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        
        for y in range(SIZE):
            for x in range(SIZE):
                pos = (x, y)
                tx = grid_x + grid_padding + x * (tile_size + tile_gap)
                ty = grid_y + grid_padding + y * (tile_size + tile_gap)
                tile_rect = pygame.Rect(tx, ty, tile_size, tile_size)

                color = None
                if pos == current:
                    color = (255, 220, 50, 150)   # Yellow
                elif pos in found:
                    color = (200, 160, 40, 150)   # Gold
                elif pos in new_set:
                    color = (50, 220, 100, 150)   # Green
                elif pos in frontier_set:
                    color = (40, 180, 180, 150)   # Teal
                elif pos in visited:
                    color = (60, 100, 160, 150)   # Blue
                
                if color:
                    overlay_surf.fill(color)
                    self.screen.blit(overlay_surf, tile_rect)

                # Flash when target found
                if found_this and pos == found_this:
                    flash = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                    flash.fill((255, 255, 255, 180))
                    self.screen.blit(flash, tile_rect)

        # Title & Explanation Background Panel
        title_bg_rect = pygame.Rect(0, 0, 600, 55)
        title_bg_rect.centerx = WINDOW_WIDTH // 2
        title_bg_rect.top = 5
        pygame.draw.rect(self.screen, (20, 25, 35, 200), title_bg_rect, border_radius=10)
        pygame.draw.rect(self.screen, Colors.BORDER, title_bg_rect, width=1, border_radius=10)

        # Title
        title = title_font.render("BFS Map Validation", True, Colors.GOLD)
        self.screen.blit(title, title.get_rect(centerx=WINDOW_WIDTH // 2, top=10))

        # Dynamic Explanation Text
        if found_this:
            action_text = f"Target Found! Validating reachability..."
            action_color = (50, 220, 100)
        elif new_neighbors:
            action_text = f"Exploring neighbors: added {len(new_neighbors)} tiles to queue."
            action_color = (200, 200, 200)
        elif not frontier:
            action_text = "Validation Complete."
            action_color = Colors.GOLD
        else:
            action_text = "Checking tile... no new unvisited neighbors."
            action_color = (180, 180, 180)

        hint = info_font.render(action_text, True, action_color)
        self.screen.blit(hint, hint.get_rect(centerx=WINDOW_WIDTH // 2, top=35))

        # Info panel below grid
        panel_y = grid_y + viz_grid_px + 12
        cx = WINDOW_WIDTH // 2

        # Status text (Paused/Playing)
        paused_text = "Paused" if self.bfs_paused else "Playing"
        status_hint = info_font.render(f"[{paused_text}] (Space: play/pause, ←→: step)", True, Colors.WHITE)
        self.screen.blit(status_hint, status_hint.get_rect(centerx=cx, top=panel_y))

        # Stats row
        panel_y += 25
        info_rect = pygame.Rect(cx - 300, panel_y, 600, 80)
        pygame.draw.rect(self.screen, Colors.DEEP, info_rect, border_radius=10)
        pygame.draw.rect(self.screen, Colors.BORDER, info_rect, width=1, border_radius=10)

        step_text = info_font.render(f"Step: {state['step']} / {len(self.bfs_trace) - 1}", True, Colors.WHITE)
        queue_text = info_font.render(f"Queue size: {len(frontier)}", True, Colors.BLUE)
        visited_text = info_font.render(f"Visited: {len(visited)}", True, (60, 100, 160))

        target_names = []
        for t in found:
            if t in self.houses:
                target_names.append(f"House {t}")
            elif t == self.exit_pos:
                target_names.append(f"Exit {t}")
        found_str = ", ".join(target_names) if target_names else "None yet"
        found_text = info_font.render(f"Targets found: {found_str}", True, Colors.GOLD)

        self.screen.blit(step_text, (info_rect.left + 16, panel_y + 8))
        self.screen.blit(queue_text, (info_rect.left + 220, panel_y + 8))
        self.screen.blit(visited_text, (info_rect.left + 420, panel_y + 8))
        self.screen.blit(found_text, (info_rect.left + 16, panel_y + 32))

        # Legend
        legend_y = panel_y + 55
        legend_items = [
            ((255, 220, 50), "Current"),
            ((50, 220, 100), "New"),
            ((40, 180, 180), "Queue"),
            ((60, 100, 160), "Visited"),
            ((200, 160, 40), "Found"),
        ]
        lx = info_rect.left + 16
        for color, label in legend_items:
            pygame.draw.rect(self.screen, color, (lx, legend_y, 14, 14), border_radius=3)
            lbl = h_font.render(label, True, Colors.WHITE)
            self.screen.blit(lbl, (lx + 18, legend_y + 1))
            lx += 110

        # Buttons
        self.screen_mgr.render_bfs_viz_buttons(self.screen)

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
