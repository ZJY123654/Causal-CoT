from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.common.config import load_settings, project_path
from src.common.jsonl import read_jsonl, write_jsonl
from src.kg_fusion.entity_alignment import detect_conflicts
from src.kg_fusion.entity_merger import make_canonical_entity, merge_entity_into
from src.kg_fusion.nil_detection import select_or_nil
from src.kg_fusion.relationship_merger import merge_relationships
from src.kg_fusion.string_recall import recall_candidates
from src.kg_fusion.utils import entity_type, normalize_name, stable_hash
from src.kg_fusion.vector_rerank import EmbeddingReranker


def _settings_value(settings: dict[str, Any], key: str, default: Any) -> Any:
    return settings.get("fusion", {}).get(key, default)


def _alignment_row(
    entity: dict[str, Any],
    canonical: dict[str, Any],
    status: str,
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "source_entity_id": entity.get("id"),
        "source_name": entity.get("name"),
        "source_type": entity_type(entity),
        "canonical_id": canonical.get("id"),
        "canonical_name": canonical.get("name"),
        "alignment_status": status,
    }
    if candidate:
        row.update(
            {
                "candidate_canonical_id": candidate.get("canonical", {}).get("id"),
                "string_score": candidate.get("string_score"),
                "vector_score": candidate.get("vector_score"),
                "combined_score": candidate.get("combined_score"),
            }
        )
    return row


def fuse_graph(
    config_path: str | None = None,
    entities_input: str | None = None,
    triples_input: str | None = None,
    output_dir: str | None = None,
    dry_run: bool = False,
    use_embeddings: bool | None = None,
) -> dict[str, Any]:
    settings = load_settings(config_path)
    entities_path = project_path(entities_input) if entities_input else project_path(settings["paths"]["entities"])
    triples_path = project_path(triples_input) if triples_input else project_path(settings["paths"]["triples"])
    fusion_dir = project_path(output_dir) if output_dir else project_path(settings["paths"].get("fusion_dir", "data/fusion"))
    fusion_dir.mkdir(parents=True, exist_ok=True)

    fusion_settings = settings.get("fusion", {})
    string_threshold = float(fusion_settings.get("string_threshold", 0.72))
    combined_threshold = float(fusion_settings.get("combined_threshold", 0.80))
    nil_threshold = float(fusion_settings.get("nil_threshold", 0.68))
    same_type_only = bool(fusion_settings.get("same_type_only", True))
    if use_embeddings is None:
        use_embeddings = not dry_run and bool(fusion_settings.get("use_embeddings", True))

    entities = list(read_jsonl(entities_path))
    triples = list(read_jsonl(triples_path))
    canonicals: list[dict[str, Any]] = []
    id_map: dict[str, str] = {}
    alignment_map: list[dict[str, Any]] = []

    reranker = EmbeddingReranker(
        config_path=config_path,
        cache_path=fusion_dir / "embedding_cache.json",
        enabled=use_embeddings,
        string_weight=float(fusion_settings.get("string_weight", 0.4)),
        vector_weight=float(fusion_settings.get("vector_weight", 0.6)),
    )

    for entity in entities:
        label = entity_type(entity)
        entity["label"] = label
        entity["normalized_name"] = normalize_name(entity.get("normalized_name") or entity.get("name", ""), label)

        if label == "AccidentCase":
            canonical = make_canonical_entity(entity)
            case_key = entity.get("case_id") or next(iter(entity.get("source_cases") or []), None) or entity.get("id")
            canonical["id"] = f"AccidentCase:canonical:{stable_hash('AccidentCase', case_key)}"
            canonical["name"] = entity.get("name", "")
            canonical["normalized_name"] = normalize_name(entity.get("name", ""), label, strip_suffixes=False)
            canonicals.append(canonical)
            id_map[entity["id"]] = canonical["id"]
            alignment_map.append(_alignment_row(entity, canonical, "preserved_case_identity"))
            continue

        candidates = recall_candidates(entity, canonicals, string_threshold, same_type_only=same_type_only)
        ranked = reranker.rerank(entity["normalized_name"], candidates)
        selected, status = select_or_nil(ranked, combined_threshold, nil_threshold)

        if selected:
            canonical = selected["canonical"]
            merge_entity_into(canonical, entity, status)
            candidate_for_row = selected
        else:
            canonical = make_canonical_entity(entity)
            if status == "review_low_margin":
                canonical["needs_review"] = True
            canonicals.append(canonical)
            candidate_for_row = ranked[0] if ranked else None

        id_map[entity["id"]] = canonical["id"]
        alignment_map.append(_alignment_row(entity, canonical, status, candidate_for_row))

    reranker.save_cache()
    canonical_triples = merge_relationships(triples, id_map)
    conflicts = detect_conflicts(entities, alignment_map)
    report = {
        "entities_input": str(entities_path),
        "triples_input": str(triples_path),
        "raw_entity_count": len(entities),
        "raw_triple_count": len(triples),
        "canonical_entity_count": len(canonicals),
        "canonical_triple_count": len(canonical_triples),
        "merged_entity_count": len(entities) - len(canonicals),
        "conflict_count": len(conflicts),
        "use_embeddings": bool(reranker.enabled),
        "same_type_only": same_type_only,
        "thresholds": {
            "string_threshold": string_threshold,
            "combined_threshold": combined_threshold,
            "nil_threshold": nil_threshold,
        },
    }

    write_jsonl(fusion_dir / "canonical_entities.jsonl", canonicals)
    write_jsonl(fusion_dir / "canonical_triples.jsonl", canonical_triples)
    write_jsonl(fusion_dir / "entity_alignment_map.jsonl", alignment_map)
    write_jsonl(fusion_dir / "conflicts.jsonl", conflicts)
    (fusion_dir / "fusion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Fuse extracted KG entities and relationships into canonical records.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--entities-input", default=None)
    parser.add_argument("--triples-input", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Run without embedding API calls.")
    parser.add_argument("--no-embeddings", action="store_true", help="Disable embedding reranking.")
    parser.add_argument("--use-llm-conflict-resolution", action="store_true", help="Reserved for future LLM conflict repair.")
    args = parser.parse_args()
    fuse_graph(
        config_path=args.config,
        entities_input=args.entities_input,
        triples_input=args.triples_input,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        use_embeddings=False if args.no_embeddings else None,
    )


if __name__ == "__main__":
    main()
