from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class OntologyValidator:
    def __init__(self, ontology_path: str | Path):
        data = json.loads(Path(ontology_path).read_text(encoding="utf-8"))
        self.entity_types = {item["name"] for item in data.get("entity_classes", [])}
        self.relation_specs = {item["name"]: item for item in data.get("relation_types", [])}

    def validate_entity_decision(self, item: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        if item.get("answer") == "yes":
            if item.get("entity_type") not in self.entity_types:
                errors.append(f"非法实体类型: {item.get('entity_type')}")
            if not str(item.get("label") or "").strip():
                errors.append("yes判定缺少label")
            if not str(item.get("evidence_text") or "").strip():
                errors.append("yes判定缺少evidence_text")
            if item.get("entity_type") == "SafetyCultureDefect":
                errors.extend(self._validate_culture_evidence(item))
        return self._result(errors)

    def validate_relation(self, subject_type: str, predicate: str, object_type: str, evidence_text: str = "") -> dict[str, Any]:
        errors: list[str] = []
        spec = self.relation_specs.get(predicate)
        if not spec:
            errors.append(f"非法关系类型: {predicate}")
        else:
            if subject_type not in spec.get("subject", []):
                errors.append(f"关系{predicate}不允许起点类型{subject_type}")
            if object_type not in spec.get("object", []):
                errors.append(f"关系{predicate}不允许终点类型{object_type}")
        if not str(evidence_text or "").strip():
            errors.append("关系缺少evidence_text")
        return self._result(errors)

    def validate_graph_records(self, entities: list[dict[str, Any]], triples: list[dict[str, Any]]) -> dict[str, Any]:
        node_types = {e["id"]: e.get("label") or e.get("entity_type") for e in entities}
        errors: list[dict[str, Any]] = []
        for rel in triples:
            source_type = node_types.get(rel.get("source_id"), "")
            target_type = node_types.get(rel.get("target_id"), "")
            result = self.validate_relation(source_type, rel.get("type", ""), target_type, rel.get("evidence_text", ""))
            if not result["valid"]:
                errors.append({"relationship": rel, "errors": result["errors"]})
        return {"valid": not errors, "errors": errors}

    @staticmethod
    def _result(errors: list[str]) -> dict[str, Any]:
        return {"valid": not errors, "errors": errors, "validation_status": "valid" if not errors else "invalid"}

    @staticmethod
    def _validate_culture_evidence(item: dict[str, Any]) -> list[str]:
        evidence = str(item.get("evidence_text") or "")
        rationale = str(item.get("rationale") or "")
        label = str(item.get("label") or "")
        text = evidence + " " + rationale + " " + label
        culture_markers = [
            "抢工程进度",
            "抢工期",
            "重生产",
            "轻安全",
            "对安全重视不够",
            "安全重视不够",
            "安全投入不足",
            "置若罔闻",
            "流于形式",
            "责任意识",
            "安全文化",
            "长期",
            "未达到培训的目的",
        ]
        management_only_markers = [
            "培训不到位",
            "监督检查不力",
            "方案",
            "技术措施",
            "隐患排查",
            "安全管理不到位",
        ]
        has_culture_marker = any(marker in text for marker in culture_markers)
        management_only = any(marker in evidence for marker in management_only_markers)
        if not has_culture_marker:
            return ["安全文化缺陷缺少明确组织价值取向或长期执行取向证据"]
        if management_only and not any(marker in evidence for marker in culture_markers):
            return ["安全文化缺陷的证据仅能证明普通管理缺陷，不能证明深层安全文化原因"]
        return []
