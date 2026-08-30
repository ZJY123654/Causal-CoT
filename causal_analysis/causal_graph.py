from __future__ import annotations

from pathlib import Path


CORE_24MODEL_EDGES = [
    ("SafetyCultureDefect", "SafetyManagementDefect"),
    ("SafetyManagementDefect", "SafetyCapabilityDefect"),
    ("SafetyManagementDefect", "UnsafeObjectState"),
    ("SafetyCapabilityDefect", "UnsafeAction"),
    ("UnsafeAction", "severe_consequence"),
    ("UnsafeObjectState", "severe_consequence"),
    ("AccidentType", "severe_consequence"),
    ("ConstructionActivity", "UnsafeAction"),
    ("ConstructionActivity", "UnsafeObjectState"),
    ("EnvironmentCondition", "UnsafeObjectState"),
    ("EnvironmentCondition", "severe_consequence"),
]


def write_24model_dot(path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["digraph G {"]
    for source, target in CORE_24MODEL_EDGES:
        lines.append(f'  "{source}" -> "{target}";')
    lines.append("}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def treatment_graph_dot(treatment: str, outcome: str, common_causes: list[str]) -> str:
    lines = ["digraph G {"]
    lines.append(f'  "{treatment}" -> "{outcome}";')
    for cause in common_causes:
        if cause == treatment or cause == outcome:
            continue
        lines.append(f'  "{cause}" -> "{treatment}";')
        lines.append(f'  "{cause}" -> "{outcome}";')
    lines.append("}")
    return "\n".join(lines)

