"""评委系统模块"""

from app.judges.stage_one import score_image_with_all_judges
from app.judges.stage_two import run_debate_for_entry

__all__ = [
    "score_image_with_all_judges",
    "run_debate_for_entry",
]

