from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from src.common.config import load_settings, project_path
from src.common.jsonl import read_jsonl


def show_progress(config_path: str | None = None, input_path: str | None = None, output: str | None = None, progress: str | None = None) -> dict:
    settings = load_settings(config_path)
    paths = settings["paths"]
    input_file = project_path(input_path) if input_path else project_path(paths.get("anonymized_cases") or paths["cleaned_cases"])
    output_file = project_path(output) if output else project_path(paths["extraction_results"])
    progress_file = project_path(progress) if progress else output_file.with_name("extraction_progress.json")

    total = _count_jsonl(input_file)
    completed_ids: list[str] = []
    elapsed_values: list[float] = []
    if output_file.exists():
        for row in read_jsonl(output_file):
            if row.get("case_id"):
                completed_ids.append(str(row["case_id"]))
                elapsed_values.append(float(row.get("timing", {}).get("elapsed_seconds") or 0))
    unique_completed = list(dict.fromkeys(completed_ids))
    state = {}
    if progress_file.exists():
        state = json.loads(progress_file.read_text(encoding="utf-8"))

    completed = len(unique_completed)
    effective_total = state.get("total_cases", total) or total
    total_elapsed = float(state.get("total_elapsed_seconds") or sum(elapsed_values))
    average_elapsed = float(state.get("average_case_elapsed_seconds") or (total_elapsed / completed if completed else 0))
    estimated_remaining = float(state.get("estimated_remaining_seconds") or average_elapsed * max(effective_total - completed, 0))
    current_running = _running_seconds(state.get("current_case_started_at", ""))
    total_including_current = total_elapsed + current_running
    payload = {
        "status": state.get("status", "not_started" if completed == 0 else "running_or_interrupted"),
        "total_cases": effective_total,
        "completed_cases": completed,
        "remaining_cases": max(effective_total - completed, 0),
        "percent_complete": round((completed / effective_total * 100) if effective_total else 100.0, 2),
        "current_index": state.get("current_index"),
        "current_case_id": state.get("current_case_id", ""),
        "last_completed_case_id": unique_completed[-1] if unique_completed else state.get("last_completed_case_id", ""),
        "current_case_started_at": state.get("current_case_started_at", ""),
        "current_case_running_seconds": round(current_running, 3),
        "current_case_running_hms": _format_seconds(current_running),
        "last_case_elapsed_seconds": state.get("last_case_elapsed_seconds"),
        "total_elapsed_seconds": round(total_elapsed, 3),
        "total_elapsed_including_current_seconds": round(total_including_current, 3),
        "average_case_elapsed_seconds": round(average_elapsed, 3),
        "estimated_remaining_seconds": round(estimated_remaining, 3),
        "total_elapsed_hms": state.get("total_elapsed_hms") or _format_seconds(total_elapsed),
        "total_elapsed_including_current_hms": _format_seconds(total_including_current),
        "average_case_elapsed_hms": state.get("average_case_elapsed_hms") or _format_seconds(average_elapsed),
        "estimated_remaining_hms": state.get("estimated_remaining_hms") or _format_seconds(estimated_remaining),
        "output": str(output_file),
        "progress_file": str(progress_file),
        "updated_at": state.get("updated_at", ""),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in read_jsonl(path))


def _format_seconds(seconds: float | None) -> str:
    seconds = max(float(seconds or 0), 0.0)
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _running_seconds(started_at: str) -> float:
    if not started_at:
        return 0.0
    try:
        started = datetime.fromisoformat(started_at)
        now = datetime.now(started.tzinfo) if started.tzinfo else datetime.now()
        return max((now - started).total_seconds(), 0.0)
    except ValueError:
        return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Show staged LLM extraction checkpoint progress.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--progress", default=None)
    args = parser.parse_args()
    show_progress(args.config, args.input, args.output, args.progress)


if __name__ == "__main__":
    main()
