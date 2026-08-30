from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.causal_analysis.run_dowhy import run_dowhy_analysis
from src.common.config import load_settings, project_path


DEFAULT_BATCH_LABELS = {"SafetyManagementDefect", "UnsafeAction", "UnsafeObjectState"}


def _load_variable_map(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _reset_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def run_batch_dowhy(
    config_path: str | None = None,
    matrix_input: str | None = None,
    variable_map_input: str | None = None,
    output_json: str | None = None,
    refutation_output: str | None = None,
    report_output: str | None = None,
    outcome: str = "severe_consequence",
    min_support: int | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    settings = load_settings(config_path)
    paths = settings["paths"]
    causal_settings = settings.get("causal", {})
    matrix_path = project_path(matrix_input) if matrix_input else project_path(paths.get("causal_matrix", "data/causal/case_causal_matrix.csv"))
    map_path = project_path(variable_map_input) if variable_map_input else project_path(paths.get("causal_variable_map", "data/causal/causal_variable_map.json"))
    result_path = project_path(output_json) if output_json else project_path(paths.get("dowhy_effect_results", "data/causal/dowhy_effect_results.jsonl"))
    refute_path = project_path(refutation_output) if refutation_output else project_path(paths.get("dowhy_refutation_results", "data/causal/dowhy_refutation_results.jsonl"))
    report_path = project_path(report_output) if report_output else project_path(paths.get("causal_report", "data/causal/causal_analysis_report.md"))
    min_support = int(min_support if min_support is not None else causal_settings.get("min_treatment_support", 5))
    top_k = int(top_k if top_k is not None else causal_settings.get("batch_top_k", 20))

    data = pd.read_csv(matrix_path, encoding="utf-8-sig")
    variable_map = _load_variable_map(map_path)
    candidates = [
        item
        for item in variable_map
        if item.get("label") in DEFAULT_BATCH_LABELS and item.get("column") in data.columns
    ]
    candidates.sort(
        key=lambda item: (
            1 if item.get("is_layer_variable") else 0,
            int(data[item["column"]].sum()),
        ),
        reverse=True,
    )
    selected = [item for item in candidates if int(data[item["column"]].sum()) >= min_support][:top_k]

    _reset_file(result_path)
    _reset_file(refute_path)
    results = [
        run_dowhy_analysis(
            treatment=item["column"],
            config_path=config_path,
            matrix_input=str(matrix_path),
            variable_map_input=str(map_path),
            output_json=str(result_path),
            refutation_output=str(refute_path),
            outcome=outcome,
            min_support=min_support,
        )
        for item in selected
    ]
    _write_report(report_path, data, selected, results, min_support)
    print(f"Wrote {len(results)} DoWhy analyses to {result_path}")
    print(f"Wrote causal report to {report_path}")
    return results


def _write_report(path: Path, data: pd.DataFrame, selected: list[dict[str, Any]], results: list[dict[str, Any]], min_support: int) -> None:
    lines = [
        "# DoWhy causal analysis report",
        "",
        "This report is generated from the fused 24Model knowledge graph. Estimates are exploratory and depend on the encoded accident-case matrix.",
        "",
        f"- Cases: {len(data)}",
        f"- Outcome: `severe_consequence`",
        f"- Severe cases: {int(data['severe_consequence'].sum()) if 'severe_consequence' in data else 0}",
        f"- Minimum treatment support: {min_support}",
        f"- Selected treatments: {len(selected)}",
        "",
        "| Treatment | Label | Support | Treated severe rate | Control severe rate | Unadjusted RD | Adjusted estimate | 95% CI | Common causes | Needs review | Skip reason |",
        "|---|---|---:|---:|---:|---:|---:|---|---:|---|---|",
    ]
    for result in results:
        estimate = result.get("effect_estimate")
        estimate_text = "" if estimate is None else f"{estimate:.4f}"
        ci = result.get("bootstrap") or {}
        ci_text = ""
        if ci.get("ci95_low") is not None and ci.get("ci95_high") is not None:
            ci_text = f"[{ci['ci95_low']:.4f}, {ci['ci95_high']:.4f}]"
        treated_rate = result.get("treated_severe_rate")
        control_rate = result.get("control_severe_rate")
        rd = result.get("unadjusted_risk_difference")
        lines.append(
            f"| {result.get('treatment', '')} | {result.get('treatment_label', '')} | "
            f"{result.get('support', 0)} | "
            f"{'' if treated_rate is None else f'{treated_rate:.4f}'} | "
            f"{'' if control_rate is None else f'{control_rate:.4f}'} | "
            f"{'' if rd is None else f'{rd:.4f}'} | "
            f"{estimate_text} | {ci_text} | {result.get('common_cause_count', 0)} | "
            f"{result.get('needs_review', False)} | "
            f"{result.get('skip_reason', '')} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DoWhy causal effect analyses for high-frequency 24Model factors.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--matrix-input", default=None)
    parser.add_argument("--variable-map-input", default=None)
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--refutation-output", default=None)
    parser.add_argument("--report-output", default=None)
    parser.add_argument("--outcome", default="severe_consequence")
    parser.add_argument("--min-support", type=int, default=None)
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()
    run_batch_dowhy(
        config_path=args.config,
        matrix_input=args.matrix_input,
        variable_map_input=args.variable_map_input,
        output_json=args.output_json,
        refutation_output=args.refutation_output,
        report_output=args.report_output,
        outcome=args.outcome,
        min_support=args.min_support,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()
