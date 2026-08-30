from __future__ import annotations

from src.common.config import load_settings


def get_graph(config_path: str | None = None):
    settings = load_settings(config_path)
    try:
        from py2neo import Graph
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("py2neo is required for Neo4j operations. Install requirements.txt first.") from exc
    neo4j = settings["neo4j"]
    return Graph(neo4j["uri"], auth=(neo4j["user"], neo4j["password"]))
