from __future__ import annotations

import re


def build_evidence_spans(text: str, max_span_chars: int = 360) -> list[dict[str, str]]:
    parts = [p.strip() for p in re.split(r"[\n。；;]+", text) if p.strip()]
    spans: list[dict[str, str]] = []
    for idx, part in enumerate(parts, 1):
        if len(part) > max_span_chars:
            chunks = [part[i : i + max_span_chars] for i in range(0, len(part), max_span_chars)]
            for sub_idx, chunk in enumerate(chunks, 1):
                spans.append({"span_id": f"S{idx:03d}_{sub_idx}", "text": chunk})
        else:
            spans.append({"span_id": f"S{idx:03d}", "text": part})
    return spans
