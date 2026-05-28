"""
utils/helper.py — Utility functions used across the game.
Translated from formatTime() and manhattan() in the HTML source.
"""


import sys
import os

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller onefile bundles."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # When running normally, project root is one level up from utils
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def format_time(seconds: int) -> str:
    """Format seconds into M:SS string (matches JS formatTime)."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def manhattan(a: tuple, b: tuple) -> int:
    """Manhattan distance between two (x, y) positions."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def clamp(value, min_val, max_val):
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))
