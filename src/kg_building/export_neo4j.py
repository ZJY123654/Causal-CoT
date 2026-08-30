from __future__ import annotations

import argparse
import csv

from src.common.config import load_settings, project_path
from src.common.jsonl import read_jsonl


def export_neo4j(
    config_path: str | None = None,
    entities_input: str | None = None,
    triples_input: str | None = None,
    nodes_output: str | None = None,
    relationships_output: str | None = None,
    use_fused: bool | None = None,
) -> tuple[int, int]:
    settings = load_settings(config_path)
    canonical_entities = project_path(settings["paths"].get("canonical_entities", "data/fusion/canonical_entities.jsonl"))
    canonical_triples = project_path(settings["paths"].get("canonical_triples", "data/fusion/canonical_triples.jsonl"))
    if use_fused is None and not entities_input and not triples_input:
        use_fused = canonical_entities.exists() and canonical_triples.exists()
    if use_fused and not entities_input:
        entities_input = str(canonical_entities)
    if use_fused and not triples_input:
        triples_input = str(canonical_triples)
    entities_path = project_path(entities_input) if entities_input else project_path(settings["paths"]["entities"])
    triples_path = project_path(triples_input) if triples_input else project_path(settings["paths"]["triples"])
    nodes_csv = project_path(nodes_output) if nodes_output else project_path(settings["paths"]["neo4j_nodes"])
    rels_csv = project_path(relationships_output) if relationships_output else project_path(settings["paths"]["neo4j_relationships"])
    nodes_csv.parent.mkdir(parents=True, exist_ok=True)
    rels_csv.parent.mkdir(parents=True, exist_ok=True)

    node_rows = list(read_jsonl(entities_path))
    rel_rows = list(read_jsonl(triples_path))
    node_fields = sorted({key for row in node_rows for key in row.keys()})
    rel_fields = sorted({key for row in rel_rows for key in row.keys()})

    with nodes_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=node_fields)
        writer.writeheader()
        writer.writerows(node_rows)
    with rels_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rel_fields)
        writer.writeheader()
        writer.writerows(rel_rows)
    print(f"Wrote {len(node_rows)} nodes to {nodes_csv}")
    print(f"Wrote {len(rel_rows)} relationships to {rels_csv}")
    return len(node_rows), len(rel_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export JSONL graph records to Neo4j CSV files.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--entities-input", default=None)
    parser.add_argument("--triples-input", default=None)
    parser.add_argument("--nodes-output", default=None)
    parser.add_argument("--relationships-output", default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--use-fused", action="store_true", help="Export canonical fused graph records.")
    mode.add_argument("--raw", action="store_true", help="Export unfused graph records.")
    args = parser.parse_args()
    use_fused = True if args.use_fused else False if args.raw else None
    export_neo4j(
        args.config,
        args.entities_input,
        args.triples_input,
        args.nodes_output,
        args.relationships_output,
        use_fused=use_fused,
    )


if __name__ == "__main__":
    main()
