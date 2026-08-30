from __future__ import annotations

import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "settings.yaml"


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or (PROJECT_ROOT / ".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except Exception:  # pragma: no cover
        if path == DEFAULT_CONFIG_PATH:
            return default_settings()
        raise RuntimeError("PyYAML is required to read non-default YAML config files.")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def default_settings() -> dict[str, Any]:
    return {
        "paths": {
            "input_files": [
                "D:/水利水电工程数据库/水利水电工程建设事故/事故案例/水利水电工程建设安全事故案例汇编-1.docx",
                "D:/水利水电工程数据库/水利水电工程建设事故/事故案例/水利水电工程建设安全事故案例汇编-2.docx",
                "D:/水利水电工程数据库/水利水电工程建设事故/事故案例/水利水电工程建设安全事故案例汇编-3.doc",
                "D:/水利水电工程数据库/水利水电工程建设事故/事故案例/水利水电工程建设安全事故案例汇编-4.docx",
            ],
            "ontology_schema": "ontology/24model_hydraulic_ontology_schema.json",
            "cleaned_cases": "data/processed/cleaned_cases.jsonl",
            "anonymized_cases": "data/processed/anonymized_cases.jsonl",
            "extraction_results": "data/kg/extraction_results.jsonl",
            "entities": "data/kg/entities.jsonl",
            "triples": "data/kg/triples.jsonl",
            "fusion_dir": "data/fusion",
            "canonical_entities": "data/fusion/canonical_entities.jsonl",
            "canonical_triples": "data/fusion/canonical_triples.jsonl",
            "entity_alignment_map": "data/fusion/entity_alignment_map.jsonl",
            "fusion_conflicts": "data/fusion/conflicts.jsonl",
            "fusion_report": "data/fusion/fusion_report.json",
            "anonymization_report": "data/privacy/anonymization_report.json",
            "causal_matrix": "data/causal/case_causal_matrix.csv",
            "causal_variable_map": "data/causal/causal_variable_map.json",
            "causal_graph_dot": "data/causal/24model_causal_graph.dot",
            "dowhy_effect_results": "data/causal/dowhy_effect_results.jsonl",
            "dowhy_refutation_results": "data/causal/dowhy_refutation_results.jsonl",
            "causal_report": "data/causal/causal_analysis_report.md",
            "neo4j_nodes": "data/neo4j/neo4j_nodes.csv",
            "neo4j_relationships": "data/neo4j/neo4j_relationships.csv",
        },
        "llm": {
            "base_url": "https://yunwu.ai/v1",
            "model": "gpt-4o",
            "embedding_model": "text-embedding-3-large",
            "temperature": 0,
            "max_retries": 3,
            "vote_count": 3,
            "gleaning_rounds": 1,
            "validation_rounds": 1,
            "min_vote_margin": 1,
        },
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "zjy20020111",
        },
        "cleaning": {"min_case_chars": 80, "keep_preface": False},
        "fusion": {
            "string_threshold": 0.72,
            "vector_threshold": 0.84,
            "nil_threshold": 0.68,
            "combined_threshold": 0.80,
            "string_weight": 0.4,
            "vector_weight": 0.6,
            "same_type_only": True,
            "use_embeddings": True,
            "use_llm_conflict_resolution": False,
        },
        "causal": {"outcome": "severe_consequence", "min_treatment_support": 5, "batch_top_k": 20},
        "privacy": {"anonymization_mode": "irreversible"},
    }


def load_settings(config_path: str | Path | None = None) -> dict[str, Any]:
    load_dotenv()
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    settings = _load_yaml(path)

    settings.setdefault("llm", {})
    settings["llm"]["base_url"] = os.getenv("OPENAI_BASE_URL", settings["llm"].get("base_url", "https://yunwu.ai/v1"))
    settings["llm"]["model"] = os.getenv("OPENAI_MODEL", settings["llm"].get("model", "gpt-4o"))
    settings["llm"]["embedding_model"] = os.getenv(
        "OPENAI_EMBEDDING_MODEL", settings["llm"].get("embedding_model", "text-embedding-3-large")
    )
    settings["llm"]["api_key"] = os.getenv("OPENAI_API_KEY", "")

    settings.setdefault("neo4j", {})
    settings["neo4j"]["uri"] = os.getenv("NEO4J_URI", settings["neo4j"].get("uri", "bolt://localhost:7687"))
    settings["neo4j"]["user"] = os.getenv("NEO4J_USER", settings["neo4j"].get("user", "neo4j"))
    settings["neo4j"]["password"] = os.getenv("NEO4J_PASSWORD", settings["neo4j"].get("password", "zjy20020111"))
    return settings


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
