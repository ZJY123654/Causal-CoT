from __future__ import annotations

from statistics import mean
from typing import Any

from src.kg_fusion.utils import as_list, canonical_id, normalize_name, safe_float, unique_preserve_order


def make_canonical_entity(entity: dict[str, Any]) -> dict[str, Any]:
    label = entity.get("label") or entity.get("entity_type") or "KGNode"
    normalized = normalize_name(entity.get("normalized_name") or entity.get("name", ""), label)
    cid = canonical_id(label, normalized)
    return {
        "id": cid,
        "label": label,
        "name": normalized or entity.get("name", ""),
        "normalized_name": normalized,
        "aliases": unique_preserve_order([entity.get("name"), entity.get("normalized_name")]),
        "source_entity_ids": unique_preserve_order([entity.get("id")]),
        "source_cases": unique_preserve_order([entity.get("case_id"), *as_list(entity.get("source_cases"))]),
        "evidence_texts": unique_preserve_order([entity.get("evidence_text"), *as_list(entity.get("evidence_texts"))]),
        "source_span_ids": unique_preserve_order([entity.get("source_span_id"), *as_list(entity.get("source_span_ids"))]),
        "rationales": unique_preserve_order([entity.get("rationale"), *as_list(entity.get("rationales"))]),
        "vote_summaries": unique_preserve_order([entity.get("vote_summary"), *as_list(entity.get("vote_summaries"))]),
        "confidence_values": unique_preserve_order([entity.get("confidence"), *as_list(entity.get("confidence_values"))]),
        "needs_review": bool(entity.get("needs_review", False)),
        "fusion_status": "canonical",
    }


def merge_entity_into(canonical: dict[str, Any], entity: dict[str, Any], alignment_status: str) -> dict[str, Any]:
    canonical["aliases"] = unique_preserve_order(
        [*as_list(canonical.get("aliases")), entity.get("name"), entity.get("normalized_name")]
    )
    canonical["source_entity_ids"] = unique_preserve_order([*as_list(canonical.get("source_entity_ids")), entity.get("id")])
    canonical["source_cases"] = unique_preserve_order(
        [*as_list(canonical.get("source_cases")), entity.get("case_id"), *as_list(entity.get("source_cases"))]
    )
    canonical["evidence_texts"] = unique_preserve_order(
        [*as_list(canonical.get("evidence_texts")), entity.get("evidence_text"), *as_list(entity.get("evidence_texts"))]
    )
    canonical["source_span_ids"] = unique_preserve_order(
        [*as_list(canonical.get("source_span_ids")), entity.get("source_span_id"), *as_list(entity.get("source_span_ids"))]
    )
    canonical["rationales"] = unique_preserve_order(
        [*as_list(canonical.get("rationales")), entity.get("rationale"), *as_list(entity.get("rationales"))]
    )
    canonical["vote_summaries"] = unique_preserve_order(
        [*as_list(canonical.get("vote_summaries")), entity.get("vote_summary"), *as_list(entity.get("vote_summaries"))]
    )
    canonical["confidence_values"] = unique_preserve_order(
        [*as_list(canonical.get("confidence_values")), entity.get("confidence"), *as_list(entity.get("confidence_values"))]
    )
    canonical["needs_review"] = bool(canonical.get("needs_review")) or bool(entity.get("needs_review")) or alignment_status.startswith("review")
    confidence_values = [safe_float(value, None) for value in as_list(canonical.get("confidence_values"))]
    confidence_values = [value for value in confidence_values if value is not None]
    canonical["avg_confidence"] = mean(confidence_values) if confidence_values else 0.0
    canonical["mention_count"] = len(as_list(canonical.get("source_entity_ids")))
    return canonical

