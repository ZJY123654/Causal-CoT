from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from src.kg_fusion.utils import normalize_name


def string_similarity(left: str, right: str) -> float:
    left_norm = normalize_name(left, None, strip_suffixes=False)
    right_norm = normalize_name(right, None, strip_suffixes=False)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return min(len(left_norm), len(right_norm)) / max(len(left_norm), len(right_norm))
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def recall_candidates(
    mention: dict[str, Any],
    canonicals: list[dict[str, Any]],
    threshold: float = 0.72,
    same_type_only: bool = True,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    label = mention.get("label") or mention.get("entity_type")
    mention_name = mention.get("normalized_name") or mention.get("name", "")
    mention_norm = normalize_name(mention_name, label)
    candidates: list[dict[str, Any]] = []
    for canonical in canonicals:
        if same_type_only and canonical.get("label") != label:
            continue
        canonical_norm = canonical.get("normalized_name") or normalize_name(canonical.get("name", ""), canonical.get("label"))
        names = [canonical_norm, canonical.get("name", ""), *canonical.get("aliases", [])]
        score = max(string_similarity(mention_norm, name) for name in names if name)
        if score >= threshold or mention_norm == canonical_norm:
            candidates.append({"canonical": canonical, "string_score": score})
    candidates.sort(key=lambda item: item["string_score"], reverse=True)
    return candidates[:top_k]

