from __future__ import annotations

from typing import Any


def select_or_nil(
    ranked_candidates: list[dict[str, Any]],
    combined_threshold: float = 0.80,
    nil_threshold: float = 0.68,
) -> tuple[dict[str, Any] | None, str]:
    if not ranked_candidates:
        return None, "nil_no_candidate"
    best = ranked_candidates[0]
    combined = float(best.get("combined_score", best.get("string_score", 0.0)))
    if combined >= combined_threshold:
        return best, "matched"
    if combined < nil_threshold:
        return None, "nil_low_score"
    return None, "review_low_margin"

