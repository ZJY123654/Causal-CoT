from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter

from src.common.config import PROJECT_ROOT, project_path


STEPS = [
    ("cleaning", ["-m", "src.data_cleaning.build_dataset"]),
    ("anonymization", ["-m", "src.privacy.anonymize_cases"]),
    ("llm_extraction", ["-m", "src.llm_extraction.extract", "--input", "data/processed/anonymized_cases.jsonl"]),
    ("kg_building", ["-m", "src.kg_building.build_graph"]),
    ("kg_fusion", ["-m", "src.kg_fusion.run_fusion"]),
    ("neo4j_export", ["-m", "src.kg_building.export_neo4j"]),
    ("causal_dataset", ["-m", "src.causal_analysis.build_causal_dataset"]),
    ("dowhy_batch", ["-m", "src.causal_analysis.run_batch_dowhy"]),
]


def run_full_experiment(progress_output: str | None = None, restart_extraction: bool = False) -> None:
    progress_path = project_path(progress_output) if progress_output else project_path("data/experiment_progress.json")
    logs_dir = project_path("data/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    total = len(STEPS)
    experiment_started_at = _now()
    experiment_started = perf_counter()
    completed_step_seconds: list[float] = []
    for index, (name, args) in enumerate(STEPS, 1):
        step_args = list(args)
        if name == "llm_extraction" and restart_extraction:
            step_args.append("--restart")
        step_started_at = _now()
        step_started = perf_counter()
        _write_progress(
            progress_path,
            name,
            index,
            total,
            "running",
            "",
            experiment_started_at=experiment_started_at,
            step_started_at=step_started_at,
            current_step_elapsed_seconds=0.0,
            total_elapsed_seconds=perf_counter() - experiment_started,
            average_completed_step_seconds=_average(completed_step_seconds),
        )
        log_path = logs_dir / f"{name}.log"
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"\n[{_now()}] START {name}\n")
            completed = subprocess.run(
                [sys.executable, *step_args],
                cwd=PROJECT_ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            log.write(f"[{_now()}] END {name} rc={completed.returncode}\n")
        step_elapsed = perf_counter() - step_started
        if completed.returncode != 0:
            _write_progress(
                progress_path,
                name,
                index,
                total,
                "failed",
                f"See {log_path}",
                experiment_started_at=experiment_started_at,
                step_started_at=step_started_at,
                current_step_elapsed_seconds=step_elapsed,
                total_elapsed_seconds=perf_counter() - experiment_started,
                average_completed_step_seconds=_average(completed_step_seconds),
            )
            raise SystemExit(completed.returncode)
        completed_step_seconds.append(step_elapsed)
        _write_progress(
            progress_path,
            name,
            index,
            total,
            "completed",
            f"See {log_path}",
            experiment_started_at=experiment_started_at,
            step_started_at=step_started_at,
            current_step_elapsed_seconds=step_elapsed,
            total_elapsed_seconds=perf_counter() - experiment_started,
            average_completed_step_seconds=_average(completed_step_seconds),
        )
    _write_progress(
        progress_path,
        "",
        total,
        total,
        "completed",
        "Full experiment completed.",
        experiment_started_at=experiment_started_at,
        step_started_at="",
        current_step_elapsed_seconds=0.0,
        total_elapsed_seconds=perf_counter() - experiment_started,
        average_completed_step_seconds=_average(completed_step_seconds),
    )


def _write_progress(
    progress_path: Path,
    step: str,
    index: int,
    total: int,
    status: str,
    message: str,
    *,
    experiment_started_at: str,
    step_started_at: str,
    current_step_elapsed_seconds: float,
    total_elapsed_seconds: float,
    average_completed_step_seconds: float,
) -> None:
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "current_step": step,
        "step_index": index,
        "total_steps": total,
        "percent_complete": round((index / total * 100) if total else 100.0, 2),
        "message": message,
        "experiment_started_at": experiment_started_at,
        "current_step_started_at": step_started_at,
        "current_step_elapsed_seconds": round(current_step_elapsed_seconds, 3),
        "current_step_elapsed_hms": _format_seconds(current_step_elapsed_seconds),
        "total_elapsed_seconds": round(total_elapsed_seconds, 3),
        "total_elapsed_hms": _format_seconds(total_elapsed_seconds),
        "average_completed_step_seconds": round(average_completed_step_seconds, 3),
        "average_completed_step_hms": _format_seconds(average_completed_step_seconds),
        "updated_at": _now(),
    }
    progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _format_seconds(seconds: float | None) -> str:
    seconds = max(float(seconds or 0), 0.0)
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete hydraulic accident KG experiment pipeline.")
    parser.add_argument("--progress-output", default=None)
    parser.add_argument("--restart-extraction", action="store_true", help="Overwrite extraction output instead of resuming.")
    args = parser.parse_args()
    run_full_experiment(args.progress_output, args.restart_extraction)


if __name__ == "__main__":
    main()
