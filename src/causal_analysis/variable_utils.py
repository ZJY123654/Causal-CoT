from __future__ import annotations

import re
from typing import Any

from src.kg_fusion.utils import normalize_name, stable_hash


FEATURE_LABELS = {
    "SafetyCultureDefect": "scd",
    "SafetyManagementDefect": "smd",
    "SafetyCapabilityDefect": "scap",
    "UnsafeAction": "ua",
    "UnsafeObjectState": "uos",
    "AccidentType": "atype",
    "ConstructionActivity": "act",
    "EnvironmentCondition": "env",
}

CAUSAL_LABELS = {
    "SafetyCultureDefect",
    "SafetyManagementDefect",
    "SafetyCapabilityDefect",
    "UnsafeAction",
    "UnsafeObjectState",
}

CONTROL_LABELS = {"AccidentType", "ConstructionActivity", "EnvironmentCondition"}

LAYER_DISPLAY_NAMES = {
    "SafetyCultureDefect": "存在安全文化缺陷",
    "SafetyManagementDefect": "存在安全管理体系缺陷",
    "SafetyCapabilityDefect": "存在人的安全能力缺陷",
    "UnsafeAction": "存在人的不安全动作",
    "UnsafeObjectState": "存在物的不安全状态",
    "AccidentType": "存在事故类型信息",
    "ConstructionActivity": "存在施工活动信息",
    "EnvironmentCondition": "存在环境条件信息",
}

SEVERE_KEYWORDS = (
    "死亡",
    "抢救无效",
    "重伤",
    "较大事故",
    "重大事故",
    "特别重大事故",
    "直接经济损失",
)


def feature_column(label: str, name: str) -> str:
    prefix = FEATURE_LABELS.get(label, "x")
    return f"x_{prefix}_{stable_hash(label, normalize_name(name, label))[:10]}"


def layer_column(label: str) -> str:
    return f"layer_{label}"


def sanitize_dot_id(value: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z_]", "_", value)
    if safe and safe[0].isdigit():
        safe = f"v_{safe}"
    return safe or "v"


def is_severe_consequence(text: str) -> int:
    value = str(text or "")
    return int(any(keyword in value for keyword in SEVERE_KEYWORDS))


def entity_case_ids(entity: dict[str, Any]) -> set[str]:
    case_ids = set()
    for value in entity.get("source_cases") or []:
        if value:
            case_ids.add(str(value))
    case_id = entity.get("case_id")
    if case_id:
        case_ids.add(str(case_id))
    return case_ids
