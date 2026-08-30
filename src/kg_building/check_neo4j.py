from __future__ import annotations

import argparse

from src.kg_building.neo4j_connection import get_graph


def check_neo4j(config_path: str | None = None) -> None:
    graph = get_graph(config_path)
    result = graph.run("RETURN 1 AS ok").data()
    print(f"Neo4j connection OK: {result}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Neo4j connection.")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    check_neo4j(args.config)


if __name__ == "__main__":
    main()
