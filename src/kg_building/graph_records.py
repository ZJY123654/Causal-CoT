from __future__ import annotations

import hashlib
from typing import Any


def stable_id(*parts: Any) -> str:
    text = "::".join("" if p is None else str(p) for p in parts)
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def node_record(label: str, name: str, **props: Any) -> dict[str, Any]:
    return {"id": f"{label}:{stable_id(label, name)}", "label": label, "name": name, **props}


def rel_record(source_id: str, rel_type: str, target_id: str, **props: Any) -> dict[str, Any]:
    return {"source_id": source_id, "type": rel_type, "target_id": target_id, **props}
