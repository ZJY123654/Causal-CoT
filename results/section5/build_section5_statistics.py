import csv
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - pos) + ordered[high] * (pos - low)


def parse_refuter(result: str) -> tuple[float, float, float]:
    estimated = re.search(r"Estimated effect:([-+0-9.eE]+)", result)
    new = re.search(r"New effect:([-+0-9.eE]+)", result)
    p_value = re.search(r"p value:([-+0-9.eE]+)", result)
    return (
        float(estimated.group(1)) if estimated else math.nan,
        float(new.group(1)) if new else math.nan,
        float(p_value.group(1)) if p_value else math.nan,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cases = read_jsonl(PROJECT_ROOT / "data/processed/anonymized_cases.jsonl")
    extractions = read_jsonl(PROJECT_ROOT / "data/kg/extraction_results.jsonl")
    raw_entities = read_jsonl(PROJECT_ROOT / "data/kg/entities.jsonl")
    raw_triples = read_jsonl(PROJECT_ROOT / "data/kg/triples.jsonl")
    canonical_entities = read_jsonl(PROJECT_ROOT / "data/fusion/canonical_entities.jsonl")
    canonical_triples = read_jsonl(PROJECT_ROOT / "data/fusion/canonical_triples.jsonl")
    alignments = read_jsonl(PROJECT_ROOT / "data/fusion/entity_alignment_map.jsonl")
    conflicts = read_jsonl(PROJECT_ROOT / "data/fusion/conflicts.jsonl")
    effects = read_jsonl(PROJECT_ROOT / "data/causal/dowhy_effect_results.jsonl")
    refutations = read_jsonl(PROJECT_ROOT / "data/causal/dowhy_refutation_results.jsonl")
    fusion_report = json.loads((PROJECT_ROOT / "data/fusion/fusion_report.json").read_text(encoding="utf-8"))
    privacy_report = json.loads((PROJECT_ROOT / "data/privacy/anonymization_report.json").read_text(encoding="utf-8"))
    extraction_progress = json.loads((PROJECT_ROOT / "data/kg/extraction_progress.json").read_text(encoding="utf-8"))
    experiment_progress = json.loads((PROJECT_ROOT / "data/experiment_progress.json").read_text(encoding="utf-8"))

    durations = [float(row.get("timing", {}).get("elapsed_seconds", 0.0)) for row in extractions]
    durations = [value for value in durations if value > 0]
    votes = [vote for row in extractions for vote in row.get("votes", [])]
    vote_patterns = Counter(
        ((vote.get("vote_summary") or {}).get("yes", 0), (vote.get("vote_summary") or {}).get("no", 0))
        for vote in votes
    )

    entity_raw_counts = Counter(row.get("label", "Unknown") for row in raw_entities)
    entity_canonical_counts = Counter(row.get("label", "Unknown") for row in canonical_entities)
    entity_case_coverage: dict[str, set[str]] = defaultdict(set)
    for row in canonical_entities:
        entity_case_coverage[row.get("label", "Unknown")].update(row.get("source_cases", []))

    entity_rows = []
    for label in sorted(set(entity_raw_counts) | set(entity_canonical_counts)):
        raw_count = entity_raw_counts[label]
        canonical_count = entity_canonical_counts[label]
        entity_rows.append(
            {
                "entity_type": label,
                "raw_count": raw_count,
                "canonical_count": canonical_count,
                "merged_or_reduced": raw_count - canonical_count,
                "reduction_percent": round((raw_count - canonical_count) / raw_count * 100, 2) if raw_count else 0,
                "case_coverage": len(entity_case_coverage[label]),
            }
        )

    relation_raw_counts = Counter(row.get("type", "Unknown") for row in raw_triples)
    relation_canonical_counts = Counter(row.get("type", "Unknown") for row in canonical_triples)
    relation_case_coverage: dict[str, set[str]] = defaultdict(set)
    for row in canonical_triples:
        relation_case_coverage[row.get("type", "Unknown")].update(row.get("source_cases", []))

    relation_rows = []
    for relation_type in sorted(set(relation_raw_counts) | set(relation_canonical_counts)):
        raw_count = relation_raw_counts[relation_type]
        canonical_count = relation_canonical_counts[relation_type]
        relation_rows.append(
            {
                "relation_type": relation_type,
                "raw_count": raw_count,
                "canonical_count": canonical_count,
                "merged_or_reduced": raw_count - canonical_count,
                "reduction_percent": round((raw_count - canonical_count) / raw_count * 100, 2) if raw_count else 0,
                "case_coverage": len(relation_case_coverage[relation_type]),
            }
        )

    factor_labels = {
        "SafetyCultureDefect",
        "SafetyManagementDefect",
        "SafetyCapabilityDefect",
        "UnsafeAction",
        "UnsafeObjectState",
    }
    top_factor_rows = []
    for row in canonical_entities:
        if row.get("label") not in factor_labels:
            continue
        top_factor_rows.append(
            {
                "entity_type": row.get("label"),
                "factor": row.get("name"),
                "case_count": len(set(row.get("source_cases", []))),
                "mention_count": len(row.get("source_entity_ids", [])),
                "evidence_count": len(row.get("evidence_texts", [])),
                "needs_review": bool(row.get("needs_review", False)),
            }
        )
    top_factor_rows.sort(key=lambda row: (-row["case_count"], -row["mention_count"], row["factor"]))

    preventive_rows = []
    for row in canonical_entities:
        if row.get("label") != "PreventiveMeasure":
            continue
        preventive_rows.append(
            {
                "preventive_measure": row.get("name"),
                "case_count": len(set(row.get("source_cases", []))),
                "mention_count": len(row.get("source_entity_ids", [])),
                "evidence_count": len(row.get("evidence_texts", [])),
            }
        )
    preventive_rows.sort(key=lambda row: (-row["case_count"], -row["mention_count"], row["preventive_measure"]))

    alignment_counts = Counter(row.get("alignment_status", "Unknown") for row in alignments)
    conflict_counts = Counter(row.get("conflict_type", "Unknown") for row in conflicts)

    effect_rows = []
    for row in effects:
        bootstrap = row.get("bootstrap", {})
        effect_rows.append(
            {
                "treatment": row.get("treatment"),
                "label": row.get("treatment_label"),
                "support": row.get("support"),
                "treated_n": row.get("treated_n"),
                "control_n": row.get("control_n"),
                "unadjusted_rd": row.get("unadjusted_risk_difference"),
                "adjusted_ate": row.get("effect_estimate"),
                "ci95_low": bootstrap.get("ci95_low"),
                "ci95_high": bootstrap.get("ci95_high"),
                "p_value": bootstrap.get("p_value_normal_approx"),
                "common_cause_count": row.get("common_cause_count"),
                "run_success": bool(row.get("run_success", False)),
                "needs_review": bool(row.get("needs_review", False)),
                "skip_reason": row.get("skip_reason", ""),
            }
        )

    refuter_values: dict[str, list[dict]] = defaultdict(list)
    for row in refutations:
        estimated, new, p_value = parse_refuter(row.get("result", ""))
        refuter = row.get("refuter", "Unknown")
        diagnostic = abs(estimated - new) if refuter == "random_common_cause" else abs(new)
        refuter_values[refuter].append({"diagnostic": diagnostic, "p_value": p_value})

    refuter_rows = []
    for refuter, rows in sorted(refuter_values.items()):
        diagnostics = [row["diagnostic"] for row in rows if not math.isnan(row["diagnostic"])]
        p_values = [row["p_value"] for row in rows if not math.isnan(row["p_value"])]
        refuter_rows.append(
            {
                "refuter": refuter,
                "record_count": len(rows),
                "diagnostic_min": min(diagnostics),
                "diagnostic_max": max(diagnostics),
                "diagnostic_mean": statistics.fmean(diagnostics),
                "p_value_min": min(p_values),
                "p_value_max": max(p_values),
            }
        )

    severe_count = 0
    matrix_path = PROJECT_ROOT / "data/causal/case_causal_matrix.csv"
    with matrix_path.open("r", encoding="utf-8-sig", newline="") as handle:
        matrix_rows = list(csv.DictReader(handle))
    for row in matrix_rows:
        severe_count += int(float(row.get("severe_consequence", 0)))

    raw_needs_review_entities = sum(bool(row.get("needs_review", False)) for row in raw_entities)
    raw_needs_review_triples = sum(bool(row.get("needs_review", False)) for row in raw_triples)
    canonical_needs_review_entities = sum(bool(row.get("needs_review", False)) for row in canonical_entities)
    canonical_needs_review_triples = sum(bool(row.get("needs_review", False)) for row in canonical_triples)
    valid_cases = sum(bool(row.get("validation", {}).get("valid", False)) for row in extractions)

    summary = {
        "case_count": len(cases),
        "extraction_case_count": len(extractions),
        "severe_case_count": severe_count,
        "severe_case_percent": severe_count / len(matrix_rows) * 100,
        "raw_entity_count": len(raw_entities),
        "raw_triple_count": len(raw_triples),
        "raw_entities_per_case": len(raw_entities) / len(cases),
        "raw_triples_per_case": len(raw_triples) / len(cases),
        "canonical_entity_count": len(canonical_entities),
        "canonical_triple_count": len(canonical_triples),
        "merged_entity_count": fusion_report.get("merged_entity_count"),
        "entity_reduction_percent": (len(raw_entities) - len(canonical_entities)) / len(raw_entities) * 100,
        "triple_reduction_count": len(raw_triples) - len(canonical_triples),
        "triple_reduction_percent": (len(raw_triples) - len(canonical_triples)) / len(raw_triples) * 100,
        "fusion_conflict_count": len(conflicts),
        "alignment_status_counts": dict(alignment_counts),
        "conflict_type_counts": dict(conflict_counts),
        "raw_needs_review_entities": raw_needs_review_entities,
        "raw_needs_review_triples": raw_needs_review_triples,
        "canonical_needs_review_entities": canonical_needs_review_entities,
        "canonical_needs_review_triples": canonical_needs_review_triples,
        "valid_case_outputs": valid_cases,
        "vote_decision_count": len(votes),
        "accepted_vote_decision_count": sum(bool(vote.get("accepted", False)) for vote in votes),
        "unanimous_vote_count": sum(
            (vote.get("vote_summary") or {}).get("margin", 0) == 3 for vote in votes
        ),
        "split_vote_count": sum(
            (vote.get("vote_summary") or {}).get("margin", 0) == 1 for vote in votes
        ),
        "vote_pattern_counts": {f"yes_{yes}_no_{no}": count for (yes, no), count in vote_patterns.items()},
        "llm_total_seconds": extraction_progress.get("total_elapsed_seconds"),
        "llm_total_hms": extraction_progress.get("total_elapsed_hms"),
        "full_pipeline_seconds": experiment_progress.get("total_elapsed_seconds"),
        "full_pipeline_hms": experiment_progress.get("total_elapsed_hms"),
        "case_time_mean_seconds": statistics.fmean(durations),
        "case_time_median_seconds": statistics.median(durations),
        "case_time_q1_seconds": percentile(durations, 0.25),
        "case_time_q3_seconds": percentile(durations, 0.75),
        "case_time_p95_seconds": percentile(durations, 0.95),
        "case_time_min_seconds": min(durations),
        "case_time_max_seconds": max(durations),
        "anonymization_replacements": privacy_report.get("replacement_counts", {}),
        "causal_candidate_count": len(effects),
        "causal_estimated_count": sum(bool(row.get("run_success", False)) for row in effects),
        "causal_skipped_count": sum(not bool(row.get("run_success", False)) for row in effects),
        "causal_significant_count": sum(
            bool(row.get("run_success", False))
            and row.get("bootstrap", {}).get("ci95_low", -1) > 0
            for row in effects
        ),
        "refutation_record_count": len(refutations),
    }

    (OUTPUT_DIR / "section5_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    kg_scale_rows = [
        {"indicator": "Accident cases", "value": len(cases), "source": "anonymized_cases.jsonl"},
        {"indicator": "Raw entities", "value": len(raw_entities), "source": "entities.jsonl"},
        {"indicator": "Raw relations", "value": len(raw_triples), "source": "triples.jsonl"},
        {"indicator": "Canonical entities", "value": len(canonical_entities), "source": "canonical_entities.jsonl"},
        {"indicator": "Canonical relations", "value": len(canonical_triples), "source": "canonical_triples.jsonl"},
        {"indicator": "Merged entities", "value": fusion_report.get("merged_entity_count"), "source": "fusion_report.json"},
        {"indicator": "Fusion conflicts retained", "value": len(conflicts), "source": "conflicts.jsonl"},
        {"indicator": "LLM extraction time (s)", "value": extraction_progress.get("total_elapsed_seconds"), "source": "extraction_progress.json"},
        {"indicator": "Full pipeline time (s)", "value": experiment_progress.get("total_elapsed_seconds"), "source": "experiment_progress.json"},
    ]

    write_csv(OUTPUT_DIR / "table_kg_scale.csv", kg_scale_rows, ["indicator", "value", "source"])
    write_csv(
        OUTPUT_DIR / "table_entity_distribution.csv",
        entity_rows,
        ["entity_type", "raw_count", "canonical_count", "merged_or_reduced", "reduction_percent", "case_coverage"],
    )
    write_csv(
        OUTPUT_DIR / "table_relation_distribution.csv",
        relation_rows,
        ["relation_type", "raw_count", "canonical_count", "merged_or_reduced", "reduction_percent", "case_coverage"],
    )
    write_csv(
        OUTPUT_DIR / "table_top_causal_factors.csv",
        top_factor_rows[:30],
        ["entity_type", "factor", "case_count", "mention_count", "evidence_count", "needs_review"],
    )
    write_csv(
        OUTPUT_DIR / "table_top_preventive_measures.csv",
        preventive_rows[:20],
        ["preventive_measure", "case_count", "mention_count", "evidence_count"],
    )
    write_csv(
        OUTPUT_DIR / "table_causal_effects.csv",
        effect_rows,
        [
            "treatment", "label", "support", "treated_n", "control_n", "unadjusted_rd",
            "adjusted_ate", "ci95_low", "ci95_high", "p_value", "common_cause_count",
            "run_success", "needs_review", "skip_reason",
        ],
    )
    write_csv(
        OUTPUT_DIR / "table_refutation_summary.csv",
        refuter_rows,
        ["refuter", "record_count", "diagnostic_min", "diagnostic_max", "diagnostic_mean", "p_value_min", "p_value_max"],
    )


if __name__ == "__main__":
    main()
