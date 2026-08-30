from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.causal_analysis.causal_graph import write_24model_dot
from src.causal_analysis.variable_utils import (
    CAUSAL_LABELS,
    CONTROL_LABELS,
    FEATURE_LABELS,
    entity_case_ids,
    feature_column,
    is_severe_consequence,
    layer_column,
    LAYER_DISPLAY_NAMES,
)
from src.common.config import load_settings, project_path
from src.common.jsonl import read_jsonl


CASE_RELATIONS = {
    "hasAccidentType": "AccidentType",
    "occursInActivity": "ConstructionActivity",
    "hasEnvironmentCondition": "EnvironmentCondition",
    "hasDirectCause": None,
    "hasConsequence": "Consequence",
}

CASE_PROPAGATION_RELATIONS = {
    "hasAccidentType",
    "occursInActivity",
    "hasEnvironmentCondition",
    "involvesObject",
    "involvesEquipment",
    "hasDirectCause",
    "hasCapabilityCause",
    "hasManagementCause",
    "hasCultureCause",
    "leadTo",
    "controlledBy",
    "hasConsequence",
}


def _case_lookup(entities: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    by_id = {entity["id"]: entity for entity in entities if entity.get("id")}
    accident_node_to_cases: dict[str, set[str]] = {}
    for entity in entities:
        if entity.get("label") == "AccidentCase":
            ids = entity_case_ids(entity)
            if not ids and entity.get("id"):
                ids.add(str(entity["id"]).split(":")[-1])
            accident_node_to_cases[entity["id"]] = ids
    return by_id, accident_node_to_cases


def _load_cleaned_cases(path: Path) -> dict[str, dict[str, Any]]:
    return {case["case_id"]: case for case in read_jsonl(path)}


def _init_rows(cleaned_cases: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for case_id, case in cleaned_cases.items():
        consequence_text = " ".join(
            str(case.get(field, ""))
            for field in ("consequence_text", "economic_loss_text", "raw_text")
        )
        rows[case_id] = {
            "case_id": case_id,
            "title": case.get("title", ""),
            "source_file": case.get("source_file", ""),
            "severe_consequence": is_severe_consequence(consequence_text),
        }
    return rows


def _derive_entity_cases(
    entities: list[dict[str, Any]],
    triples: list[dict[str, Any]],
    accident_node_to_cases: dict[str, set[str]],
) -> dict[str, set[str]]:
    entity_cases: dict[str, set[str]] = defaultdict(set)
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue
        entity_cases[entity_id].update(entity_case_ids(entity))
        if entity_id in accident_node_to_cases:
            entity_cases[entity_id].update(accident_node_to_cases[entity_id])

    for rel in triples:
        source_id = rel.get("source_id")
        target_id = rel.get("target_id")
        rel_cases = {str(case_id) for case_id in rel.get("source_cases") or [] if case_id}
        if rel.get("case_id"):
            rel_cases.add(str(rel["case_id"]))
        if source_id:
            rel_cases.update(accident_node_to_cases.get(source_id, set()))
        if target_id and rel_cases:
            entity_cases[target_id].update(rel_cases)
        if source_id and rel_cases:
            entity_cases[source_id].update(rel_cases)
    return entity_cases


def build_causal_dataset(
    config_path: str | None = None,
    entities_input: str | None = None,
    triples_input: str | None = None,
    output_csv: str | None = None,
    mapping_output: str | None = None,
    graph_output: str | None = None,
) -> tuple[int, int]:
    settings = load_settings(config_path)
    paths = settings["paths"]
    default_entities = paths.get("canonical_entities") or paths["entities"]
    default_triples = paths.get("canonical_triples") or paths["triples"]
    entities_path = project_path(entities_input) if entities_input else project_path(default_entities)
    triples_path = project_path(triples_input) if triples_input else project_path(default_triples)
    anonymized_cases = project_path(paths["anonymized_cases"]) if "anonymized_cases" in paths else None
    cleaned_path = anonymized_cases if anonymized_cases is not None and anonymized_cases.exists() else project_path(paths["cleaned_cases"])
    out_csv = project_path(output_csv) if output_csv else project_path(paths.get("causal_matrix", "data/causal/case_causal_matrix.csv"))
    map_path = project_path(mapping_output) if mapping_output else project_path(paths.get("causal_variable_map", "data/causal/causal_variable_map.json"))
    dot_path = project_path(graph_output) if graph_output else project_path(paths.get("causal_graph_dot", "data/causal/24model_causal_graph.dot"))

    entities = list(read_jsonl(entities_path))
    triples = list(read_jsonl(triples_path))
    cleaned_cases = _load_cleaned_cases(cleaned_path)
    rows = _init_rows(cleaned_cases)
    by_id, accident_node_to_cases = _case_lookup(entities)
    entity_cases = _derive_entity_cases(entities, triples, accident_node_to_cases)
    variable_map: dict[str, dict[str, Any]] = {}
    case_feature_evidence: dict[tuple[str, str], list[str]] = defaultdict(list)

    for entity in entities:
        label = entity.get("label")
        if label not in FEATURE_LABELS:
            continue
        column = feature_column(label, entity.get("name", ""))
        variable_map.setdefault(
            column,
            {
                "column": column,
                "label": label,
                "name": entity.get("name", ""),
                "entity_id": entity.get("id", ""),
                "role": "causal_factor" if label in CAUSAL_LABELS else "control",
            },
        )
        for case_id in entity_cases.get(entity.get("id"), set()) or entity_case_ids(entity):
            if case_id in rows:
                rows[case_id][column] = 1

    for rel in triples:
        source_id = rel.get("source_id")
        target_id = rel.get("target_id")
        target = by_id.get(target_id, {})
        source_cases = set(rel.get("source_cases") or [])
        if rel.get("case_id"):
            source_cases.add(str(rel["case_id"]))
        source_cases.update(accident_node_to_cases.get(source_id, set()))
        if not source_cases:
            continue
        if rel.get("type") == "hasConsequence":
            evidence = " ".join(rel.get("evidence_texts") or [rel.get("evidence_text", ""), target.get("name", "")])
            for case_id in source_cases:
                if case_id in rows and is_severe_consequence(evidence):
                    rows[case_id]["severe_consequence"] = 1
            continue
        label = target.get("label")
        if label not in FEATURE_LABELS:
            continue
        column = feature_column(label, target.get("name", ""))
        variable_map.setdefault(
            column,
            {
                "column": column,
                "label": label,
                "name": target.get("name", ""),
                "entity_id": target.get("id", ""),
                "role": "causal_factor" if label in CAUSAL_LABELS else "control",
            },
        )
        evidence = " ".join(rel.get("evidence_texts") or [rel.get("evidence_text", "")]).strip()
        for case_id in source_cases:
            if case_id in rows:
                rows[case_id][column] = 1
                if evidence:
                    case_feature_evidence[(case_id, column)].append(evidence)

    feature_columns = sorted(variable_map)
    layer_columns = sorted(layer_column(label) for label in FEATURE_LABELS)
    for row in rows.values():
        for column in feature_columns:
            row.setdefault(column, 0)
        for label in FEATURE_LABELS:
            layer_col = layer_column(label)
            label_feature_columns = [
                column
                for column, spec in variable_map.items()
                if spec.get("label") == label and not spec.get("is_layer_variable")
            ]
            row[layer_col] = int(any(row.get(column, 0) for column in label_feature_columns))
            row[f"count_{label}"] = int(sum(row.get(column, 0) for column in label_feature_columns))
            variable_map.setdefault(
                layer_col,
                {
                    "column": layer_col,
                    "label": label,
                    "name": LAYER_DISPLAY_NAMES.get(label, f"存在{label}"),
                    "entity_id": "",
                    "role": "causal_factor" if label in CAUSAL_LABELS else "control",
                    "is_layer_variable": True,
                },
            )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    dataframe = pd.DataFrame(rows.values())
    fixed = ["case_id", "title", "source_file", "severe_consequence"]
    count_columns = [f"count_{label}" for label in sorted(FEATURE_LABELS)]
    dataframe = dataframe[fixed + layer_columns + count_columns + feature_columns]
    dataframe.to_csv(out_csv, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(json.dumps(list(variable_map.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    write_24model_dot(dot_path)
    print(f"Wrote {len(dataframe)} cases and {len(variable_map)} causal variables to {out_csv}")
    print(f"Wrote variable map to {map_path}")
    print(f"Wrote 24Model causal graph to {dot_path}")
    return len(dataframe), len(variable_map)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build case-level causal matrix from fused 24Model KG records.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--entities-input", default=None)
    parser.add_argument("--triples-input", default=None)
    parser.add_argument("--output-csv", default=None)
    parser.add_argument("--mapping-output", default=None)
    parser.add_argument("--graph-output", default=None)
    args = parser.parse_args()
    build_causal_dataset(
        config_path=args.config,
        entities_input=args.entities_input,
        triples_input=args.triples_input,
        output_csv=args.output_csv,
        mapping_output=args.mapping_output,
        graph_output=args.graph_output,
    )


if __name__ == "__main__":
    main()
