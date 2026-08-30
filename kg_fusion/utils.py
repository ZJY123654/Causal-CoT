from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from typing import Any


WEAK_SUFFIXES = (
    "事故",
    "问题",
    "原因",
    "因素",
    "缺陷",
    "不到位",
    "不落实",
)

ALIASES_BY_TYPE: dict[str, dict[str, str]] = {
    "AccidentType": {
        "坍塌事故": "坍塌",
        "边坡坍塌": "坍塌",
        "高处坠落事故": "高处坠落",
        "触电事故": "触电",
        "起重伤害事故": "起重伤害",
        "机械伤害事故": "机械伤害",
        "涌水突泥": "涌水/突泥",
        "突泥涌水": "涌水/突泥",
    },
    "SafetyManagementDefect": {
        "安全教育不到位": "安全培训不足",
        "未开展安全培训": "安全培训不足",
        "培训不足": "安全培训不足",
        "安全培训流于形式": "安全培训不足",
        "培训流于形式": "安全培训不足",
        "隐患排查整改不落实": "隐患排查治理不到位",
        "隐患排查不到位": "隐患排查治理不到位",
        "现场监督检查不力": "现场安全监督不足",
        "安全管理不到位": "安全管理体系不完善",
    },
    "SafetyCultureDefect": {
        "重生产轻安全": "重进度轻安全",
        "重效益轻安全": "重进度轻安全",
        "安全意识淡薄": "安全责任意识淡薄",
        "安全责任意识不强": "安全责任意识淡薄",
        "安全投入不够": "安全投入不足",
    },
    "UnsafeAction": {
        "未佩戴安全带": "未系安全带",
        "未正确佩戴安全带": "未系安全带",
        "违章指挥作业": "违章指挥",
        "冒险施工": "冒险作业",
    },
    "UnsafeObjectState": {
        "防护措施缺失": "防护设施缺失",
        "临边防护缺失": "防护设施缺失",
        "设备带病运转": "设备带病运行",
        "支护不足": "支护结构不足",
    },
    "ConstructionActivity": {
        "吊装": "吊装作业",
        "起吊作业": "吊装作业",
        "混凝土浇筑": "混凝土浇筑作业",
        "基坑开挖": "基坑开挖作业",
    },
}


def stable_hash(*parts: Any) -> str:
    text = "::".join("" if part is None else str(part) for part in parts)
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def entity_type(entity: dict[str, Any]) -> str:
    return str(entity.get("entity_type") or entity.get("label") or "KGNode")


def normalize_name(name: str, label: str | None = None, strip_suffixes: bool = True) -> str:
    value = str(name or "").strip()
    value = re.sub(r"\s+", "", value)
    value = value.replace("（", "(").replace("）", ")").replace("，", ",").replace("；", ";")
    value = value.strip("。；;，,、:： \t\r\n")
    if label:
        value = ALIASES_BY_TYPE.get(label, {}).get(value, value)
    if strip_suffixes and len(value) > 4:
        for suffix in WEAK_SUFFIXES:
            if value.endswith(suffix) and len(value) - len(suffix) >= 4:
                value = value[: -len(suffix)]
                break
    if label:
        value = ALIASES_BY_TYPE.get(label, {}).get(value, value)
    return value or str(name or "").strip()


def canonical_id(label: str, normalized_name: str) -> str:
    return f"{label}:canonical:{stable_hash(label, normalized_name)}"


def as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    return [value]


def unique_preserve_order(values: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for value in values:
        key = repr(value)
        if key not in seen and value not in (None, ""):
            seen.add(key)
            out.append(value)
    return out


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

