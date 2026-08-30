from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from typing import Any

from src.common.config import load_settings, project_path
from src.common.jsonl import read_jsonl, write_jsonl
from src.kg_building.graph_records import node_record, rel_record


CASE_CONTEXT_RELATIONS = {
    "AccidentType": "hasAccidentType",
    "ConstructionActivity": "occursInActivity",
    "EngineeringObject": "involvesObject",
    "EnvironmentCondition": "hasEnvironmentCondition",
    "EquipmentFacility": "involvesEquipment",
    "Consequence": "hasConsequence",
}


def _add_node(nodes: OrderedDict[str, dict], node: dict) -> dict:
    nodes.setdefault(node["id"], node)
    return nodes[node["id"]]


def _field_node(nodes: OrderedDict[str, dict], label: str, value: str, **props: Any) -> dict | None:
    value = (value or "").strip()
    if not value:
        return None
    return _add_node(nodes, node_record(label, value, **props))


def build_from_cleaned_cases(
    config_path: str | None = None,
    extraction_results: str | None = None,
    entities_output: str | None = None,
    triples_output: str | None = None,
) -> tuple[int, int]:
    settings = load_settings(config_path)
    cleaned_path = project_path(settings["paths"]["cleaned_cases"])
    extraction_path = project_path(extraction_results) if extraction_results else project_path(settings["paths"]["extraction_results"])
    entities_path = project_path(entities_output) if entities_output else project_path(settings["paths"]["entities"])
    triples_path = project_path(triples_output) if triples_output else project_path(settings["paths"]["triples"])

    if extraction_path.exists() and extraction_path.stat().st_size > 0:
        return build_from_extraction_results(settings, extraction_path, entities_path, triples_path)

    nodes: OrderedDict[str, dict] = OrderedDict()
    rels: list[dict] = []
    for case in read_jsonl(cleaned_path):
        case_node = _add_node(
            nodes,
            {
                "id": f"AccidentCase:{case['case_id']}",
                "label": "AccidentCase",
                "name": case.get("title", case["case_id"]),
                "case_id": case["case_id"],
                "source_file": case.get("source_file", ""),
                "source_case_no": case.get("source_case_no", ""),
                "date": case.get("date", "") or case.get("date_time", ""),
                "time": case.get("time", ""),
                "location": case.get("location", ""),
                "raw_text": case.get("raw_text", ""),
            },
        )
        direct_cause = None
        mappings = [
            ("accident_type", "AccidentType", "hasAccidentType", False),
            ("consequence_text", "Consequence", "hasConsequence", False),
            ("direct_cause_text", "UnsafeObjectState", "hasDirectCause", True),
        ]
        for field, label, rel_type, needs_review in mappings:
            target = _field_node(
                nodes,
                label,
                case.get(field, ""),
                source_file=case.get("source_file", ""),
                needs_review=needs_review,
            )
            if target:
                rels.append(rel_record(case_node["id"], rel_type, target["id"], evidence_text=case.get(field, "")))
                if field == "direct_cause_text":
                    direct_cause = target
        measure = _field_node(nodes, "PreventiveMeasure", case.get("measures_text", ""), source_file=case.get("source_file", ""))
        if direct_cause and measure:
            rels.append(rel_record(direct_cause["id"], "controlledBy", measure["id"], evidence_text=case.get("measures_text", "")))

    write_jsonl(entities_path, nodes.values())
    write_jsonl(triples_path, rels)
    print(f"Wrote {len(nodes)} nodes to {entities_path}")
    print(f"Wrote {len(rels)} relationships to {triples_path}")
    return len(nodes), len(rels)


def build_from_extraction_results(settings: dict, extraction_path, entities_path, triples_path) -> tuple[int, int]:
    schema_path = project_path(settings["paths"]["ontology_schema"])
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    valid_labels = {
        str(item.get("name"))
        for item in schema.get("entity_classes", [])
        if isinstance(item, dict) and item.get("name")
    }
    nodes: OrderedDict[str, dict] = OrderedDict()
    rels: list[dict] = []
    for result in read_jsonl(extraction_path):
        case_id = str(result.get("case_id") or "").strip()
        source_file = result.get("source_file", "")
        stages = result.get("stages", {})
        expected_case_node_id = f"AccidentCase:{case_id}"
        case_entity_ids: list[str] = []
        for node in stages.get("stage_5_graph_entities", []):
            if node.get("id"):
                label = str(node.get("label") or node.get("entity_type") or "").strip()
                if label not in valid_labels:
                    continue
                # Accident cases are provenance anchors, not extractable mentions.
                # Keep exactly the node tied to the current case_id.
                if label == "AccidentCase" and node.get("id") != expected_case_node_id:
                    continue
                if case_id:
                    node.setdefault("case_id", case_id)
                    source_cases = list(node.get("source_cases") or [])
                    if case_id not in source_cases:
                        source_cases.append(case_id)
                    node["source_cases"] = source_cases
                if source_file:
                    node.setdefault("source_file", source_file)
                nodes.setdefault(node["id"], node)
                case_entity_ids.append(node["id"])
        if case_id and expected_case_node_id not in nodes:
            nodes[expected_case_node_id] = {
                "id": expected_case_node_id,
                "label": "AccidentCase",
                "name": result.get("title") or case_id,
                "case_id": case_id,
                "source_file": source_file,
                "source_cases": [case_id],
            }
        local_relation_keys: set[tuple[str, str, str]] = set()
        for rel in stages.get("stage_5_graph_triples", []):
            if rel.get("source_id") and rel.get("target_id") and rel.get("type"):
                if case_id:
                    rel.setdefault("case_id", case_id)
                    source_cases = list(rel.get("source_cases") or [])
                    if case_id not in source_cases:
                        source_cases.append(case_id)
                    rel["source_cases"] = source_cases
                if source_file:
                    rel.setdefault("source_file", source_file)
                rels.append(rel)
                local_relation_keys.add((rel["source_id"], rel["type"], rel["target_id"]))

        # Context entities are extracted from this case and therefore have a
        # deterministic case-membership relation. Materialize these ontology
        # edges even when the LLM relation stage focuses on causal pairs.
        for entity_id in case_entity_ids:
            entity = nodes.get(entity_id, {})
            relation_type = CASE_CONTEXT_RELATIONS.get(entity.get("label"))
            relation_key = (expected_case_node_id, relation_type or "", entity_id)
            if not relation_type or relation_key in local_relation_keys:
                continue
            evidence_texts = entity.get("evidence_texts") or []
            evidence_text = entity.get("evidence_text") or (evidence_texts[0] if evidence_texts else "")
            relation = rel_record(
                expected_case_node_id,
                relation_type,
                entity_id,
                evidence_text=evidence_text,
            )
            relation["case_id"] = case_id
            relation["source_cases"] = [case_id]
            if source_file:
                relation["source_file"] = source_file
            rels.append(relation)

    rels = [
        rel
        for rel in rels
        if rel.get("source_id") in nodes and rel.get("target_id") in nodes
    ]

    write_jsonl(entities_path, nodes.values())
    write_jsonl(triples_path, rels)
    print(f"Wrote {len(nodes)} nodes from extraction results to {entities_path}")
    print(f"Wrote {len(rels)} relationships from extraction results to {triples_path}")
    return len(nodes), len(rels)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build basic graph records from cleaned cases.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--extraction-results", default=None, help="Optional staged extraction JSONL path.")
    parser.add_argument("--entities-output", default=None, help="Optional entities JSONL output path.")
    parser.add_argument("--triples-output", default=None, help="Optional triples JSONL output path.")
    args = parser.parse_args()
    build_from_cleaned_cases(args.config, args.extraction_results, args.entities_output, args.triples_output)


if __name__ == "__main__":
    main()
