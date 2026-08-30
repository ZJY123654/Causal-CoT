from __future__ import annotations

import argparse

from src.common.config import load_settings, project_path
from src.common.jsonl import read_jsonl
from src.kg_building.neo4j_connection import get_graph


def write_neo4j(config_path: str | None = None, clear: bool = False, use_fused: bool | None = None) -> tuple[int, int]:
    settings = load_settings(config_path)
    graph = get_graph(config_path)
    if clear:
        graph.run("MATCH (n) DETACH DELETE n")
    graph.run("CREATE CONSTRAINT hydraulic_node_id IF NOT EXISTS FOR (n:KGNode) REQUIRE n.id IS UNIQUE")

    canonical_entities = project_path(settings["paths"].get("canonical_entities", "data/fusion/canonical_entities.jsonl"))
    canonical_triples = project_path(settings["paths"].get("canonical_triples", "data/fusion/canonical_triples.jsonl"))
    if use_fused is None:
        if canonical_entities.exists() and canonical_triples.exists():
            nodes_path = canonical_entities
            rels_path = canonical_triples
        else:
            nodes_path = project_path(settings["paths"]["entities"])
            rels_path = project_path(settings["paths"]["triples"])
    else:
        entities_key = "canonical_entities" if use_fused else "entities"
        triples_key = "canonical_triples" if use_fused else "triples"
        nodes_path = project_path(settings["paths"][entities_key])
        rels_path = project_path(settings["paths"][triples_key])
    nodes = list(read_jsonl(nodes_path))
    rels = list(read_jsonl(rels_path))

    for node in nodes:
        props = dict(node)
        label = props.pop("label", "KGNode")
        graph.run(
            "MERGE (n:KGNode {id: $id}) "
            "SET n += $props "
            "SET n.label = $label",
            id=node["id"],
            props=props,
            label=label,
        )
    for rel in rels:
        graph.run(
            "MATCH (a:KGNode {id: $source_id}), (b:KGNode {id: $target_id}) "
            "MERGE (a)-[r:RELATED {type: $type}]->(b) "
            "SET r += $props",
            source_id=rel["source_id"],
            target_id=rel["target_id"],
            type=rel["type"],
            props=rel,
        )
    print(f"Wrote {len(nodes)} nodes and {len(rels)} relationships to Neo4j")
    return len(nodes), len(rels)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write graph records to Neo4j.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--clear", action="store_true", help="Delete all existing nodes before writing.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--use-fused", action="store_true", help="Write canonical fused graph records.")
    mode.add_argument("--raw", action="store_true", help="Write unfused graph records.")
    args = parser.parse_args()
    use_fused = True if args.use_fused else False if args.raw else None
    write_neo4j(args.config, clear=args.clear, use_fused=use_fused)


if __name__ == "__main__":
    main()
