from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

from src.common.config import load_settings, project_path
from src.common.jsonl import read_jsonl, write_jsonl
from src.privacy.anonymizer import CaseAnonymizer, anonymize_record


def anonymize_cases(
    config_path: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
    report_path: str | None = None,
) -> int:
    settings = load_settings(config_path)
    paths = settings["paths"]
    src = project_path(input_path) if input_path else project_path(paths["cleaned_cases"])
    dst = project_path(output_path) if output_path else project_path(paths.get("anonymized_cases", "data/processed/anonymized_cases.jsonl"))
    report = project_path(report_path) if report_path else project_path(paths.get("anonymization_report", "data/privacy/anonymization_report.json"))
    rows: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    for case in read_jsonl(src):
        anonymizer = CaseAnonymizer()
        rows.append(anonymize_record(case, anonymizer))
        totals.update(anonymizer.counts)
    count = write_jsonl(dst, rows)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "input": str(src),
                "output": str(dst),
                "case_count": count,
                "mode": "irreversible",
                "replacement_counts": dict(totals),
                "mapping_saved": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {count} anonymized cases to {dst}")
    print(f"Wrote anonymization report to {report}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Create irreversible anonymized accident case JSONL.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--report", default=None)
    args = parser.parse_args()
    anonymize_cases(args.config, args.input, args.output, args.report)


if __name__ == "__main__":
    main()
