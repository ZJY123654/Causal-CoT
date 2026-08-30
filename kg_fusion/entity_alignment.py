from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.kg_fusion.utils import normalize_name


def detect_conflicts(entities: list[dict[str, Any]], alignment_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    by_normalized_name: dict[str, set[str]] = defaultdict(set)
    for entity in entities:
        label = entity.get("label") or entity.get("entity_type") or "KGNode"
        normalized = normalize_name(entity.get("normalized_name") or entity.get("name", ""), label)
        by_normalized_name[normalized].add(label)
    for normalized, labels in by_normalized_name.items():
        if normalized and len(labels) > 1:
            conflicts.append(
                {
                    "conflict_type": "same_name_different_type",
                    "normalized_name": normalized,
                    "labels": sorted(labels),
                    "resolution": "not_merged_due_to_24model_type_constraint",
                }
            )
    for row in alignment_map:
        if row.get("alignment_status") == "review_low_margin":
            conflicts.append(
                {
                    "conflict_type": "low_margin_entity_alignment",
                    "source_entity_id": row.get("source_entity_id"),
                    "candidate_canonical_id": row.get("candidate_canonical_id"),
                    "string_score": row.get("string_score"),
                    "vector_score": row.get("vector_score"),
                    "combined_score": row.get("combined_score"),
                    "resolution": "created_new_canonical_and_marked_for_review",
                }
            )
    return conflicts

