from __future__ import annotations

import argparse
from pathlib import Path

from src.common.config import load_settings, project_path
from src.common.jsonl import write_jsonl
from src.data_cleaning.case_splitter import parse_documents


def build_dataset(config_path: str | None = None) -> int:
    settings = load_settings(config_path)
    files = settings["paths"]["input_files"]
    output = project_path(settings["paths"]["cleaned_cases"])
    min_case_chars = int(settings.get("cleaning", {}).get("min_case_chars", 80))
    cases = parse_documents(files, min_case_chars=min_case_chars)
    count = write_jsonl(output, cases)
    print(f"Wrote {count} cases to {output}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cleaned accident case JSONL dataset from Word files.")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    build_dataset(args.config)


if __name__ == "__main__":
    main()
