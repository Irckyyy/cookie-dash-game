"""
variants/scoring.py — End-game scoring and Performance Index (PI) calculation.
Translated from endGame() scoring logic in the HTML source.
"""

from utils.helper import format_time


from setting import ALGORITHM_DESCRIPTIONS

def calculate_results(human, ai, elapsed: int, difficulty: str) -> dict:
    """
    Calculate final game results including PI (Performance Index).
    Returns a dict with all end-screen stats.
    """
    h_time = human.finish_time if human.finish_time is not None else elapsed
    a_time = ai.finish_time if ai.finish_time is not None else elapsed

    h_total = human.score
    a_total = ai.score

    h_pi = round(h_total / h_time, 2) if h_time > 0 else 0.0
    a_pi = round(a_total / a_time, 2) if a_time > 0 else 0.0

    # Determine winner
    if human.finished and not ai.finished:
        winner_text = "You Win!"
        winner_badge = ""
    elif not human.finished and ai.finished:
        winner_text = "AI Wins!"
        winner_badge = ""
    else:
        # Both finished — compare PI
        if h_pi >= a_pi:
            winner_text = "You Win by Score!"
            winner_badge = ""
        else:
            winner_text = "AI Wins by Score!"
            winner_badge = ""

    algo_name, algo_desc = ALGORITHM_DESCRIPTIONS.get(difficulty, ("", ""))

    return {
        "winner_text": winner_text,
        "winner_badge": winner_badge,
        "human_score": h_total,
        "ai_score": a_total,
        "human_pi": f"{h_pi:.2f}",
        "ai_pi": f"{a_pi:.2f}",
        "human_time": format_time(h_time),
        "ai_time": format_time(a_time),
        "algo_name": algo_name,
        "algo_desc": algo_desc,
    }
