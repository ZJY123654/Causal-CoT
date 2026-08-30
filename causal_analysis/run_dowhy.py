from __future__ import annotations

import argparse
import json
import math
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.causal_analysis.causal_graph import treatment_graph_dot
from src.common.config import load_settings, project_path


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


def _load_variable_map(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_treatment(treatment: str, variable_map: list[dict[str, Any]]) -> dict[str, Any]:
    value = treatment.strip()
    for item in variable_map:
        if value in {item.get("column"), item.get("name"), item.get("entity_id")}:
            return item
    contains = [item for item in variable_map if value and value in str(item.get("name", ""))]
    if len(contains) == 1:
        return contains[0]
    if contains:
        names = ", ".join(item["name"] for item in contains[:10])
        raise ValueError(f"Treatment is ambiguous: {treatment}. Candidates: {names}")
    raise ValueError(f"Treatment not found in causal variable map: {treatment}")


LAYER_ORDER = {
    "SafetyCultureDefect": 0,
    "SafetyManagementDefect": 1,
    "SafetyCapabilityDefect": 2,
    "UnsafeAction": 3,
    "UnsafeObjectState": 3,
}

CONTROL_LABELS = {"ConstructionActivity", "EnvironmentCondition"}


def _is_variable_usable(data: pd.DataFrame, column: str, min_support: int) -> bool:
    if column not in data.columns:
        return False
    support = int(data[column].sum())
    return support >= min_support and (len(data) - support) >= min_support and data[column].nunique() >= 2


def _candidate_common_causes(
    treatment_info: dict[str, Any],
    variable_map: list[dict[str, Any]],
    data: pd.DataFrame,
    min_support: int,
    max_controls: int = 12,
) -> list[str]:
    treatment_column = treatment_info["column"]
    treatment_label = treatment_info.get("label")
    treatment_is_layer = bool(treatment_info.get("is_layer_variable"))
    treatment_order = LAYER_ORDER.get(treatment_label, 99)
    candidates: list[dict[str, Any]] = []

    for item in variable_map:
        column = item.get("column")
        label = item.get("label")
        if not column or column == treatment_column:
            continue
        if not _is_variable_usable(data, column, min_support):
            continue
        if label == "AccidentType":
            continue
        if label == treatment_label and (item.get("is_layer_variable") or treatment_is_layer):
            continue
        if label == treatment_label and not treatment_is_layer:
            continue
        if label in LAYER_ORDER and LAYER_ORDER[label] >= treatment_order:
            continue
        if label not in LAYER_ORDER and label not in CONTROL_LABELS:
            continue
        item_support = int(data[column].sum())
        candidates.append({**item, "support": item_support})

    candidates.sort(
        key=lambda item: (
            1 if item.get("is_layer_variable") else 0,
            item.get("support", 0),
        ),
        reverse=True,
    )
    return [item["column"] for item in candidates[:max_controls]]


def _skip_reason(data: pd.DataFrame, treatment: str, outcome: str, min_support: int) -> str:
    if treatment not in data.columns:
        return "treatment_column_missing"
    if outcome not in data.columns:
        return "outcome_column_missing"
    support = int(data[treatment].sum())
    if support < min_support:
        return f"low_support:{support}<min_support:{min_support}"
    if len(data) - support < min_support:
        return f"low_control_support:{len(data) - support}<min_support:{min_support}"
    if data[treatment].nunique() < 2:
        return "treatment_has_no_variation"
    if data[outcome].nunique() < 2:
        return "outcome_has_no_variation"
    treated = data[data[treatment] == 1]
    control = data[data[treatment] == 0]
    cells = [
        int(((data[treatment] == 1) & (data[outcome] == 1)).sum()),
        int(((data[treatment] == 1) & (data[outcome] == 0)).sum()),
        int(((data[treatment] == 0) & (data[outcome] == 1)).sum()),
        int(((data[treatment] == 0) & (data[outcome] == 0)).sum()),
    ]
    if min(cells) == 0:
        return f"separation_or_empty_cell:{cells}"
    if len(treated) < min_support or len(control) < min_support:
        return "insufficient_overlap"
    return ""


def _risk_summary(data: pd.DataFrame, treatment: str, outcome: str) -> dict[str, Any]:
    t1 = data[data[treatment] == 1]
    t0 = data[data[treatment] == 0]
    y11 = int((t1[outcome] == 1).sum())
    y10 = int((t1[outcome] == 0).sum())
    y01 = int((t0[outcome] == 1).sum())
    y00 = int((t0[outcome] == 0).sum())
    treated_rate = float(t1[outcome].mean()) if len(t1) else None
    control_rate = float(t0[outcome].mean()) if len(t0) else None
    risk_difference = None if treated_rate is None or control_rate is None else treated_rate - control_rate
    return {
        "treated_n": int(len(t1)),
        "control_n": int(len(t0)),
        "treated_severe_n": y11,
        "treated_nonsevere_n": y10,
        "control_severe_n": y01,
        "control_nonsevere_n": y00,
        "treated_severe_rate": treated_rate,
        "control_severe_rate": control_rate,
        "unadjusted_risk_difference": risk_difference,
    }


def _linear_coef(data: pd.DataFrame, treatment: str, outcome: str, common_causes: list[str]) -> float:
    columns = [treatment, *common_causes]
    x = data[columns].astype(float).to_numpy()
    x = np.column_stack([np.ones(len(x)), x])
    y = data[outcome].astype(float).to_numpy()
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    return float(coef[1])


def _bootstrap_ci(
    data: pd.DataFrame,
    treatment: str,
    outcome: str,
    common_causes: list[str],
    n_bootstrap: int = 500,
    seed: int = 2026,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    estimates: list[float] = []
    n = len(data)
    for _ in range(n_bootstrap):
        sample = data.iloc[rng.integers(0, n, n)]
        if sample[treatment].nunique() < 2 or sample[outcome].nunique() < 2:
            continue
        try:
            estimates.append(_linear_coef(sample, treatment, outcome, common_causes))
        except Exception:
            continue
    if not estimates:
        return {"bootstrap_n": 0, "ci95_low": None, "ci95_high": None, "bootstrap_se": None, "p_value_normal_approx": None}
    arr = np.asarray(estimates, dtype=float)
    se = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    point = _linear_coef(data, treatment, outcome, common_causes)
    p_value = None
    if se > 0:
        z = abs(point / se)
        p_value = float(math.erfc(z / math.sqrt(2)))
    return {
        "bootstrap_n": int(len(arr)),
        "ci95_low": float(np.quantile(arr, 0.025)),
        "ci95_high": float(np.quantile(arr, 0.975)),
        "bootstrap_se": se,
        "p_value_normal_approx": p_value,
    }


def _treatment_graph(treatment: str, outcome: str, common_causes: list[str]):
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_edge(treatment, outcome)
    for cause in common_causes:
        if cause == treatment or cause == outcome:
            continue
        graph.add_edge(cause, treatment)
        graph.add_edge(cause, outcome)
    return graph


def run_dowhy_analysis(
    treatment: str,
    config_path: str | None = None,
    matrix_input: str | None = None,
    variable_map_input: str | None = None,
    output_json: str | None = None,
    refutation_output: str | None = None,
    outcome: str = "severe_consequence",
    min_support: int | None = None,
) -> dict[str, Any]:
    settings = load_settings(config_path)
    paths = settings["paths"]
    matrix_path = project_path(matrix_input) if matrix_input else project_path(paths.get("causal_matrix", "data/causal/case_causal_matrix.csv"))
    map_path = project_path(variable_map_input) if variable_map_input else project_path(paths.get("causal_variable_map", "data/causal/causal_variable_map.json"))
    result_path = project_path(output_json) if output_json else project_path(paths.get("dowhy_effect_results", "data/causal/dowhy_effect_results.jsonl"))
    refute_path = project_path(refutation_output) if refutation_output else project_path(paths.get("dowhy_refutation_results", "data/causal/dowhy_refutation_results.jsonl"))
    min_support = int(min_support if min_support is not None else settings.get("causal", {}).get("min_treatment_support", 5))

    data = pd.read_csv(matrix_path, encoding="utf-8-sig")
    variable_map = _load_variable_map(map_path)
    treatment_info = resolve_treatment(treatment, variable_map)
    treatment_column = treatment_info["column"]
    common_causes = _candidate_common_causes(treatment_info, variable_map, data, min_support)
    analysis = {
        "treatment": treatment_info.get("name"),
        "treatment_column": treatment_column,
        "treatment_label": treatment_info.get("label"),
        "is_layer_variable": bool(treatment_info.get("is_layer_variable")),
        "outcome": outcome,
        "n": int(len(data)),
        "support": int(data[treatment_column].sum()) if treatment_column in data else 0,
        "common_causes": common_causes,
        "common_cause_count": len(common_causes),
        "needs_review": False,
        "run_success": False,
        "causal_quality_pass": False,
        "skip_reason": "",
    }
    if treatment_column in data and outcome in data:
        analysis.update(_risk_summary(data, treatment_column, outcome))

    skip_reason = _skip_reason(data, treatment_column, outcome, min_support)
    if skip_reason:
        analysis.update({"needs_review": True, "skip_reason": skip_reason})
        _append_jsonl(result_path, analysis)
        return analysis

    try:
        from dowhy import CausalModel
    except Exception as exc:
        analysis.update({"needs_review": True, "skip_reason": "dowhy_not_installed", "error": str(exc)})
        _append_jsonl(result_path, analysis)
        return analysis

    graph_dot = treatment_graph_dot(treatment_column, outcome, common_causes)
    graph = _treatment_graph(treatment_column, outcome, common_causes)
    model = CausalModel(data=data, treatment=treatment_column, outcome=outcome, graph=graph)
    estimand = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(
        estimand,
        method_name="backdoor.linear_regression",
        test_significance=True,
    )
    analysis.update(
        {
            "identified_estimand": str(estimand),
            "estimate_method": "backdoor.linear_regression",
            "effect_estimate": float(estimate.value),
            "bootstrap": _bootstrap_ci(data, treatment_column, outcome, common_causes),
            "graph": graph_dot,
            "run_success": True,
            "causal_quality_pass": bool(common_causes),
            "needs_review": not bool(common_causes),
        }
    )
    _append_jsonl(result_path, analysis)

    refutations = []
    for method in ("random_common_cause", "placebo_treatment_refuter"):
        try:
            refuter = model.refute_estimate(estimand, estimate, method_name=method)
            refutations.append(
                {
                    "treatment": treatment_info.get("name"),
                    "treatment_column": treatment_column,
                    "outcome": outcome,
                    "refuter": method,
                    "result": str(refuter),
                    "needs_review": False,
                }
            )
        except Exception as exc:
            refutations.append(
                {
                    "treatment": treatment_info.get("name"),
                    "treatment_column": treatment_column,
                    "outcome": outcome,
                    "refuter": method,
                    "error": str(exc),
                    "needs_review": True,
                }
            )
    for row in refutations:
        _append_jsonl(refute_path, row)
    return analysis


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a DoWhy causal effect analysis for one treatment.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--treatment", required=True, help="Treatment name, entity id, or variable column.")
    parser.add_argument("--matrix-input", default=None)
    parser.add_argument("--variable-map-input", default=None)
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--refutation-output", default=None)
    parser.add_argument("--outcome", default="severe_consequence")
    parser.add_argument("--min-support", type=int, default=None)
    args = parser.parse_args()
    result = run_dowhy_analysis(
        treatment=args.treatment,
        config_path=args.config,
        matrix_input=args.matrix_input,
        variable_map_input=args.variable_map_input,
        output_json=args.output_json,
        refutation_output=args.refutation_output,
        outcome=args.outcome,
        min_support=args.min_support,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
