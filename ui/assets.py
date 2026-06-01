"""
ui/assets.py — Loads, caches, and scales all game sprite assets.
Handles slicing the delivery_man sprite sheet into directional poses.
Also loads UI background assets (buttons, icons, panels, etc.) from
the assets/background folder.
"""

import os
import pygame

from utils.helper import resource_path

# Base directory for assets (relative to project root)
_BASE_DIR = resource_path("assets")
_TILES_DIR = os.path.join(_BASE_DIR, "tiles")
_SPRITES_DIR = os.path.join(_BASE_DIR, "sprites")
_BG_DIR = os.path.join(_BASE_DIR, "background")


class AssetLoader:
    """Singleton-style asset loader — call load_all() once after pygame.init()."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self._cache = {}

    # ─── public API ───────────────────────────────────────────────────

    def load_all(self, tile_size: int):
        """Load every asset and scale it to the given tile_size.
        Must be called after pygame.display.set_mode()."""
        if self._loaded:
            return
        self._tile_size = tile_size
        self._load_tiles(tile_size)
        self._load_player_sprites(tile_size)
        self._load_ui_assets()
        self._loaded = True

    def get(self, key: str, default=None):
        return self._cache.get(key, default)

    # ─── tile getters ─────────────────────────────────────────────────

    @property
    def filled_tile(self) -> pygame.Surface:
        """Grass tile (revealed empty tile background)."""
        return self._cache["filled_tile"]

    @property
    def empty_tile(self) -> pygame.Surface:
        """Dark tile (unrevealed tile background)."""
        return self._cache["empty_tile"]

    @property
    def cookie(self) -> pygame.Surface:
        return self._cache["cookie"]

    @property
    def delivered_house(self) -> pygame.Surface:
        return self._cache["delivered_house"]

    @property
    def undelivered_house(self) -> pygame.Surface:
        return self._cache["undelivered_house"]

    @property
    def door(self) -> pygame.Surface:
        return self._cache["door"]

    @property
    def entrance(self) -> pygame.Surface:
        return self._cache["entrance"]

    @property
    def puddle(self) -> pygame.Surface:
        return self._cache["puddle"]

    @property
    def hole(self) -> pygame.Surface:
        return self._cache["hole"]

    @property
    def rock(self) -> pygame.Surface:
        return self._cache["rock"]

    @property
    def tree(self) -> pygame.Surface:
        return self._cache["tree"]

    @property
    def flashlight(self) -> pygame.Surface:
        return self._cache.get("flashlight")

    @property
    def warning(self) -> pygame.Surface:
        return self._cache.get("warning")

    @property
    def battery(self) -> pygame.Surface:
        return self._cache.get("battery")

    # ─── UI background asset getters ──────────────────────────────────

    @property
    def bg_sky(self) -> pygame.Surface:
        """Sky/clouds background image."""
        return self._cache.get("bg_sky")

    @property
    def bg_home_panel(self) -> pygame.Surface:
        """Title screen panel (brown card with border)."""
        return self._cache.get("bg_home_panel")

    @property
    def bg_logo(self) -> pygame.Surface:
        """Cookie + 'Cookie Delivery Dash' logo."""
        return self._cache.get("bg_logo")

    @property
    def bg_modes(self) -> pygame.Surface:
        """Difficulty selection cards strip."""
        return self._cache.get("bg_modes")

    @property
    def bg_scoreboard(self) -> pygame.Surface:
        """Score/results panel background."""
        return self._cache.get("bg_scoreboard")

    @property
    def bg_status_bar(self) -> pygame.Surface:
        """HUD status bar during gameplay."""
        return self._cache.get("bg_status_bar")

    @property
    def bg_empty_grid(self) -> pygame.Surface:
        """Empty grid background for the playing area."""
        return self._cache.get("bg_empty_grid")

    @property
    def bg_filled_grid(self) -> pygame.Surface:
        """Filled grid background for the playing area."""
        return self._cache.get("bg_filled_grid")

    # ─── Button getters (sliced from buttons.png) ─────────────────────

    def get_button(self, name: str) -> pygame.Surface:
        """Get a button image by name: 'play_game', 'play_again', 'start',
        'back', 'menu', 'view_maps'."""
        return self._cache.get(f"btn_{name}")

    # ─── Icon getters (sliced from icons.png) ─────────────────────────

    def get_icon(self, name: str) -> pygame.Surface:
        """Get an icon image by name: 'robot', 'human', 'star', 'cloud',
        'house_color', 'house_grey', 'shop', 'door', 'tree', 'rock',
        'puddle', 'hole'."""
        return self._cache.get(f"icon_{name}")

    # ─── Difficulty card getters (sliced from Modes.png) ──────────────

    def get_mode_card(self, index: int) -> pygame.Surface:
        """Get a difficulty card image by index (0=easy, 1=medium, 2=hard)."""
        return self._cache.get(f"mode_card_{index}")

    # ─── player sprite getters ────────────────────────────────────────

    def get_player_sprite(self, direction: str) -> pygame.Surface:
        """Get player sprite for a direction: 'down', 'right', 'up', 'left'."""
        key = f"player_{direction}"
        return self._cache.get(key, self._cache.get("player_down"))

    # ─── scaled copies (for special sizes like title screen cookie) ───

    def get_scaled(self, name: str, size: tuple) -> pygame.Surface:
        """Return a cached copy of an asset scaled to (w, h)."""
        cache_key = f"{name}_{size[0]}x{size[1]}"
        if cache_key not in self._cache:
            original = self._cache.get(name)
            if original is None:
                return None
            self._cache[cache_key] = pygame.transform.smoothscale(original, size)
        return self._cache[cache_key]

    # ─── internal loading ─────────────────────────────────────────────

    def _load_image(self, path: str) -> pygame.Surface:
        """Load a single image with alpha support."""
        return pygame.image.load(path).convert_alpha()

    def _scale(self, surf: pygame.Surface, size: int) -> pygame.Surface:
        """Scale surface to size×size using smooth scaling."""
        return pygame.transform.smoothscale(surf, (size, size))

    def _load_tiles(self, tile_size: int):
        """Load and scale all tile assets."""
        # Individual tile from the filled_tiles grid (extract one cell)
        night_path = os.path.join(_BG_DIR, "night_tiles.png")
        if os.path.exists(night_path):
            filled_full = self._load_image(night_path)
        else:
            filled_full = self._load_image(os.path.join(_TILES_DIR, "filled_tiles.png"))
        
        # The grid is 10x10 cells
        cell_size = filled_full.get_width() // 10
        single_filled = filled_full.subsurface(pygame.Rect(0, 0, cell_size, cell_size))
        self._cache["filled_tile"] = self._scale(single_filled, tile_size)

        # Same for empty tiles
        empty_full = self._load_image(os.path.join(_TILES_DIR, "empty_tiles.png"))
        cell_size_e = empty_full.get_width() // 10
        single_empty = empty_full.subsurface(pygame.Rect(0, 0, cell_size_e, cell_size_e))
        self._cache["empty_tile"] = self._scale(single_empty, tile_size)

        # Individual sprite tiles — load and scale to tile_size
        tile_files = {
            "cookie":            "cookie.png",
            "delivered_house":   "delivered_house.png",
            "undelivered_house": "undelivered_house.png",
            "door":              "door.png",
            "entrance":          "entrance.png",
            "puddle":            "puddle.png",
            "hole":              "hole.png",
            "rock":              "rock.png",
            "tree":              "tree.png",
            "boots":             "boots.png",
            "rope":              "rope.png",
            "flashlight":        "flashlight.png",
            "warning":           "warning.png",
            "battery":           "battery.png",
        }

        for name, filename in tile_files.items():
            path = os.path.join(_TILES_DIR, filename)
            if os.path.exists(path):
                raw = self._load_image(path)
                # Special case: door.png has two door variants side-by-side
                # Crop just the closed door (top-left quadrant)
                if name == "door":
                    dw, dh = raw.get_size()
                    raw = raw.subsurface(pygame.Rect(0, 0, dw // 2, dh)).copy()
                self._cache[name] = self._scale(raw, tile_size)

    def _load_player_sprites(self, tile_size: int):
        """Slice the 2×2 delivery_man sprite sheet into 4 directional poses."""
        
        # Also quickly load credit images while we are at it
        credits_dir = os.path.join(_BASE_DIR, "credits")
        for char in ["boy", "girl", "ai"]:
            path = os.path.join(credits_dir, f"{char}.png")
            if os.path.exists(path):
                img = self._load_image(path)
                self._cache[f"cred_{char}"] = pygame.transform.smoothscale(img, (120, 120))
                
        # Load AI robot head
        ai_head_path = os.path.join(credits_dir, "robot_head.png")
        if os.path.exists(ai_head_path):
            raw = self._load_image(ai_head_path)
            self._cache["ai_head"] = self._scale(raw, int(tile_size * 1.1))

        path = os.path.join(_SPRITES_DIR, "delivery_man.png")
        if not os.path.exists(path):
            return

        sheet = self._load_image(path)
        w, h = sheet.get_size()
        half_w, half_h = w // 2, h // 2

        # 2×2 layout:
        # Top-left  = front (down)    Top-right  = right
        # Bot-left  = back  (up)      Bot-right  = left
        regions = {
            "down":  pygame.Rect(0,      0,      half_w, half_h),
            "left":  pygame.Rect(half_w, 0,      half_w, half_h),
            "up":    pygame.Rect(0,      half_h, half_w, half_h),
            "right": pygame.Rect(half_w, half_h, half_w, half_h),
        }

        for direction, rect in regions.items():
            sprite = sheet.subsurface(rect).copy()
            # Scale to fit within a tile, but keep it slightly larger for visibility
            sprite_size = int(tile_size * 1.1)
            scaled = pygame.transform.smoothscale(sprite, (sprite_size, sprite_size))
            self._cache[f"player_{direction}"] = scaled

    def _load_ui_assets(self):
        """Load all UI background/panel assets from the background folder."""
        # ── Sky background (Frame 1.png — the main background image) ──

        sky_path = os.path.join(_BG_DIR, "nightTimeBG.png")
        if os.path.exists(sky_path):
            self._cache["bg_sky"] = self._load_image(sky_path)

        # ── Home panel ──
        home_path = os.path.join(_BG_DIR, "Home.png")
        if os.path.exists(home_path):
            self._cache["bg_home_panel"] = self._load_image(home_path)

        # ── Logo ──
        logo_path = os.path.join(_BG_DIR, "Logo.png")
        if os.path.exists(logo_path):
            self._cache["bg_logo"] = self._load_image(logo_path)

        # ── Modes strip ──
        modes_path = os.path.join(_BG_DIR, "Modes.png")
        if os.path.exists(modes_path):
            modes_full = self._load_image(modes_path)
            self._cache["bg_modes"] = modes_full
            # Slice into 3 individual cards
            mw, mh = modes_full.get_size()
            card_w = mw // 3
            for i in range(3):
                card = modes_full.subsurface(
                    pygame.Rect(i * card_w, 0, card_w, mh)
                ).copy()
                self._cache[f"mode_card_{i}"] = card

        # ── Scoreboard panel ──
        score_path = os.path.join(_BG_DIR, "score board.png")
        if os.path.exists(score_path):
            self._cache["bg_scoreboard"] = self._load_image(score_path)

        # ── Status bar (HUD) ──
        status_path = os.path.join(_BG_DIR, "status bar.png")
        if os.path.exists(status_path):
            self._cache["bg_status_bar"] = self._load_image(status_path)

        # ── Grid backgrounds ──
        empty_grid_path = os.path.join(_BG_DIR, "empty tiles.png")
        if os.path.exists(empty_grid_path):
            self._cache["bg_empty_grid"] = self._load_image(empty_grid_path)

        filled_grid_path = os.path.join(_BG_DIR, "night_tiles.png")
        if os.path.exists(filled_grid_path):
            self._cache["bg_filled_grid"] = self._load_image(filled_grid_path)

        # ── Buttons spritesheet (350×719, 6 buttons stacked vertically) ──
        btn_path = os.path.join(_BG_DIR, "buttons.png")
        if os.path.exists(btn_path):
            btn_sheet = self._load_image(btn_path)
            bw, bh = btn_sheet.get_size()
            btn_h = bh // 6  # ~120px per button
            btn_names = ["play_game", "play_again", "start", "back", "menu", "view_maps"]
            for i, name in enumerate(btn_names):
                btn = btn_sheet.subsurface(
                    pygame.Rect(0, i * btn_h, bw, btn_h)
                ).copy()
                self._cache[f"btn_{name}"] = btn

        for custom_btn in ["quit", "option", "credits", "next", "BFS_button"]:
            path = os.path.join(_BG_DIR, f"{custom_btn}.png")
            if os.path.exists(path):
                self._cache[f"btn_{custom_btn}"] = self._load_image(path)

        # ── Icons spritesheet (1251×960, 4 columns × 3 rows) ──
        icon_path = os.path.join(_BG_DIR, "icons.png")
        if os.path.exists(icon_path):
            icon_sheet = self._load_image(icon_path)
            iw, ih = icon_sheet.get_size()
            cols, rows = 4, 3
            # Add an extra column for the 5th item in row 2 (door)
            # Actually the grid appears to be 5 items in row 2; let's handle
            # it as a 4-col x 3-row grid but with some items being wider
            # Looking at the image: 4 cols × 3 rows = 12 icons
            icon_w = iw // cols
            icon_h = ih // rows
            icon_names = [
                # Row 0: robot, human, star, cloud
                "robot", "human", "star", "cloud",
                # Row 1: house_color, house_grey, shop, door
                "house_color", "house_grey", "shop", "door",
                # Row 2: tree, rock, puddle, hole
                "tree", "rock", "puddle", "hole",
            ]
            for idx, name in enumerate(icon_names):
                col = idx % cols
                row = idx // cols
                icon = icon_sheet.subsurface(
                    pygame.Rect(col * icon_w, row * icon_h, icon_w, icon_h)
                ).copy()
                self._cache[f"icon_{name}"] = icon

        # ── Story and Intro Slide Loading ──
        for i in range(2, 7):
            slide_path = os.path.join(_BG_DIR, f"{i}.png")
            if os.path.exists(slide_path):
                self._cache[f"story_slide_{i}"] = self._load_image(slide_path)


# Module-level singleton
assets = AssetLoader()
