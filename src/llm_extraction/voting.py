from __future__ import annotations

from collections import Counter
from typing import Any, Callable


def normalize_answer(value: Any) -> str:
    text = str(value or "").strip().lower()
    return "yes" if text in {"yes", "y", "1", "true", "是", "有"} else "no"


def vote_json(
    call_fn: Callable[[], dict[str, Any]],
    vote_count: int = 3,
    min_vote_margin: int = 1,
) -> dict[str, Any]:
    votes: list[dict[str, Any]] = []
    for _ in range(vote_count):
        item = call_fn()
        item["answer"] = normalize_answer(item.get("answer"))
        votes.append(item)

    counts = Counter(v["answer"] for v in votes)
    yes_count = counts.get("yes", 0)
    no_count = counts.get("no", 0)
    majority = "yes" if yes_count > no_count else "no"
    margin = abs(yes_count - no_count)
    accepted = margin >= min_vote_margin and majority == "yes"
    representative = _choose_representative(votes, majority)
    representative.update(
        {
            "answer": majority,
            "accepted": accepted,
            "needs_review": margin < min_vote_margin,
            "vote_summary": {
                "vote_count": len(votes),
                "yes": yes_count,
                "no": no_count,
                "margin": margin,
                "min_vote_margin": min_vote_margin,
            },
            "votes": votes,
        }
    )
    return representative


def _choose_representative(votes: list[dict[str, Any]], answer: str) -> dict[str, Any]:
    candidates = [v for v in votes if v.get("answer") == answer] or votes
    return max(candidates, key=lambda v: float(v.get("confidence") or 0)).copy()
