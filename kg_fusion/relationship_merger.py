from __future__ import annotations

from statistics import mean
from typing import Any

from src.kg_fusion.utils import as_list, safe_float, stable_hash, unique_preserve_order


def _vote_ratio(rows: list[dict[str, Any]]) -> float:
    yes = sum(int(row.get("vote_yes_count") or 0) for row in rows)
    no = sum(int(row.get("vote_no_count") or 0) for row in rows)
    total = yes + no
    return yes / total if total else 0.0


def merge_relationships(triples: list[dict[str, Any]], id_map: dict[str, str]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for triple in triples:
        source_id = id_map.get(triple.get("source_id"), triple.get("source_id"))
        target_id = id_map.get(triple.get("target_id"), triple.get("target_id"))
        rel_type = triple.get("type")
        if not source_id or not target_id or not rel_type:
            continue
        buckets.setdefault((source_id, rel_type, target_id), []).append(triple)

    merged: list[dict[str, Any]] = []
    for (source_id, rel_type, target_id), rows in buckets.items():
        confidences = [safe_float(row.get("confidence"), None) for row in rows]
        confidences = [value for value in confidences if value is not None]
        source_cases = unique_preserve_order(
            value
            for row in rows
            for value in [row.get("case_id"), *as_list(row.get("source_cases"))]
        )
        evidence_texts = unique_preserve_order(
            value
            for row in rows
            for value in [row.get("evidence_text"), *as_list(row.get("evidence_texts"))]
        )
        merged.append(
            {
                "id": f"REL:canonical:{stable_hash(source_id, rel_type, target_id)}",
                "source_id": source_id,
                "type": rel_type,
                "target_id": target_id,
                "weight": len(rows),
                "case_count": len(source_cases),
                "evidence_count": len(evidence_texts),
                "avg_confidence": mean(confidences) if confidences else 0.0,
                "vote_yes_ratio": _vote_ratio(rows),
                "source_triple_ids": unique_preserve_order([row.get("id") for row in rows]),
                "question_ids": unique_preserve_order([row.get("question_id") for row in rows]),
                "evidence_texts": evidence_texts,
                "source_cases": source_cases,
                "validation_status": "valid"
                if all(row.get("validation_status", "valid") == "valid" for row in rows)
                else "needs_review",
                "needs_review": any(bool(row.get("needs_review")) for row in rows),
            }
        )
    return merged

