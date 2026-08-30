from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .text_normalizer import FIELD_ALIASES, normalize_text, strip_bracket_heading


CASE_PATTERNS = [
    re.compile(r"^【案例\s*(?P<num>[0-9０-９]+)】\s*(?P<title>.+)$"),
    re.compile(r"^事故案例\s*(?P<num>[0-9]+[-—][0-9]+)\s*$"),
]

SECTION_PATTERN = re.compile(r"^【(?P<name>[^】]{2,20})】\s*(?P<body>.*)$")
INLINE_FIELD_PATTERN = re.compile(r"^(?P<name>[\u4e00-\u9fa5A-Za-z0-9（）()]+)\s*[:：]\s*(?P<body>.*)$")


def _case_match(paragraph: str) -> re.Match[str] | None:
    for pattern in CASE_PATTERNS:
        match = pattern.match(paragraph)
        if match:
            return match
    return None


def split_cases(paragraphs: list[str], source_file: str, min_case_chars: int = 80) -> list[dict]:
    cases: list[dict] = []
    current: dict | None = None
    pending_case_no: str | None = None

    for para in paragraphs:
        match = _case_match(para)
        if match:
            if current:
                cases.append(current)
            num = match.group("num")
            title = match.groupdict().get("title") or ""
            pending_case_no = None if title else num
            current = {
                "source_file": source_file,
                "source_case_no": num,
                "title": title.strip(),
                "paragraphs": [para],
            }
            continue

        if current and pending_case_no and not current["title"] and len(para) <= 120:
            current["title"] = para
            current["paragraphs"].append(para)
            pending_case_no = None
            continue

        if current:
            current["paragraphs"].append(para)

    if current:
        cases.append(current)

    parsed = [parse_case(case) for case in cases]
    return [case for case in parsed if len(case.get("raw_text", "")) >= min_case_chars]


def parse_case(case: dict) -> dict:
    paragraphs = case["paragraphs"]
    fields: dict[str, str] = {}
    current_key: str | None = None

    for para in paragraphs[1:]:
        sec = SECTION_PATTERN.match(para)
        inline = INLINE_FIELD_PATTERN.match(para)
        key = None
        body = ""

        if sec and sec.group("name") in FIELD_ALIASES:
            key = FIELD_ALIASES[sec.group("name")]
            body = sec.group("body").strip()
        elif inline and inline.group("name") in FIELD_ALIASES:
            key = FIELD_ALIASES[inline.group("name")]
            body = inline.group("body").strip()

        if key:
            current_key = key
            fields[key] = _append(fields.get(key, ""), body)
        elif current_key and not _looks_like_chapter_heading(para):
            fields[current_key] = _append(fields.get(current_key, ""), strip_bracket_heading(para))

    raw_text = normalize_text("\n".join(paragraphs))
    stable = hashlib.md5(f"{case['source_file']}::{case['source_case_no']}::{case['title']}".encode("utf-8")).hexdigest()[:10]
    return {
        "case_id": f"HCA-{stable}",
        "source_file": case["source_file"],
        "source_case_no": case["source_case_no"],
        "title": case["title"],
        "accident_type": fields.get("accident_type", ""),
        "date": fields.get("date", ""),
        "time": fields.get("time", ""),
        "date_time": fields.get("date_time", ""),
        "location": fields.get("location", ""),
        "organization": fields.get("organization", ""),
        "severity_level": fields.get("severity_level", ""),
        "direct_cause_text": fields.get("direct_cause_text", ""),
        "indirect_cause_text": fields.get("indirect_cause_text", ""),
        "cause_text": fields.get("cause_text", ""),
        "process_text": fields.get("process_text", ""),
        "consequence_text": fields.get("consequence_text", ""),
        "economic_loss_text": fields.get("economic_loss_text", ""),
        "measures_text": fields.get("measures_text", ""),
        "raw_text": raw_text,
    }


def _append(old: str, new: str) -> str:
    if not new:
        return old
    return f"{old}\n{new}".strip() if old else new.strip()


def _looks_like_chapter_heading(text: str) -> bool:
    return bool(re.match(r"^第[一二三四五六七八九十0-9]+[章节篇]", text))


def parse_documents(files: list[str | Path], min_case_chars: int = 80) -> list[dict]:
    from .word_reader import read_word_paragraphs

    all_cases: list[dict] = []
    for file in files:
        path = Path(file)
        paragraphs = read_word_paragraphs(path)
        all_cases.extend(split_cases(paragraphs, path.name, min_case_chars=min_case_chars))
    return all_cases
