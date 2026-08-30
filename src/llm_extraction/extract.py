from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from src.common.config import load_settings, project_path
from src.common.jsonl import append_jsonl, read_jsonl
from src.llm_extraction.client import LLMClient
from src.llm_extraction.evidence import build_evidence_spans
from src.llm_extraction.question_bank import (
    CAPABILITY_QUESTIONS,
    CULTURE_QUESTIONS,
    DIRECT_CAUSE_QUESTIONS,
    MANAGEMENT_QUESTIONS,
    PROCESS_QUESTIONS,
    Question,
)
from src.llm_extraction.templates import graph_entity_prompt, gleaning_prompt, validation_repair_prompt, yes_no_question_prompt
from src.llm_extraction.validator import OntologyValidator
from src.llm_extraction.voting import vote_json


class DryRunClient:
    """Deterministic mock client used to test the staged pipeline without API calls."""

    def json_chat(self, prompt: str) -> dict[str, Any]:
        if '"entities"' in prompt and "GraphRAG" in prompt:
            return {
                "entities": [
                    {
                        "entity_name": "事故案例",
                        "entity_type": "AccidentCase",
                        "entity_description": "清洗后的水利工程施工事故案例。",
                        "evidence_text": _first_evidence(prompt),
                        "source_span_id": "S001",
                        "relationship_hints": [],
                    }
                ]
            }
        if "补漏" in prompt:
            return {"entities": []}
        yes = any(token in prompt for token in ["直接原因", "未", "不足", "不到位", "坍塌", "坠落", "事故后果"])
        return {
            "question_id": _extract_between(prompt, '"question_id": "', '"') or "DRY_RUN",
            "answer": "yes" if yes else "no",
            "label": "规则抽取候选因素" if yes else "",
            "entity_type": _extract_between(prompt, '"entity_type": "', '"') or "UnsafeObjectState",
            "relation_type": _extract_between(prompt, '"relation_type": "', '"'),
            "evidence_text": _first_evidence(prompt) if yes else "",
            "rationale": "dry-run根据关键词生成，用于验证流程结构。" if yes else "dry-run未发现充分证据。",
            "confidence": 0.7 if yes else 0.3,
        }


def extract_cases(
    limit: int | None = None,
    config_path: str | None = None,
    dry_run: bool = False,
    output: str | None = None,
    input_path: str | None = None,
    resume: bool = True,
    progress_output: str | None = None,
) -> int:
    settings = load_settings(config_path)
    input_path = project_path(input_path) if input_path else project_path(settings["paths"]["cleaned_cases"])
    output_path = project_path(output) if output else project_path(settings["paths"]["extraction_results"])
    progress_path = project_path(progress_output) if progress_output else output_path.with_name("extraction_progress.json")
    ontology_path = project_path(settings["paths"]["ontology_schema"])
    validator = OntologyValidator(ontology_path)
    client = DryRunClient() if dry_run else LLMClient(config_path)

    llm_settings = settings.get("llm", {})
    vote_count = int(llm_settings.get("vote_count", 3))
    min_vote_margin = int(llm_settings.get("min_vote_margin", 1))
    gleaning_rounds = int(llm_settings.get("gleaning_rounds", 1))
    validation_rounds = int(llm_settings.get("validation_rounds", 1))

    ontology_types = ", ".join(sorted(validator.entity_types))
    cases = list(read_jsonl(input_path))
    if limit is not None:
        cases = cases[:limit]
    total_cases = len(cases)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    completed_ids: set[str] = set()
    completed_count = 0
    completed_elapsed_seconds = 0.0
    if resume and output_path.exists() and output_path.stat().st_size > 0:
        for row in read_jsonl(output_path):
            case_id = row.get("case_id")
            if case_id and case_id not in completed_ids:
                completed_ids.add(case_id)
                completed_count += 1
                completed_elapsed_seconds += float(row.get("timing", {}).get("elapsed_seconds") or 0)
        print(f"Resume enabled: found {completed_count} completed cases in {output_path}")
    else:
        output_path.write_text("", encoding="utf-8")

    experiment_started_at = _now()
    current_case_started_at = ""
    last_case_elapsed: float | None = None
    _write_progress(
        progress_path,
        input_path=input_path,
        output_path=output_path,
        total_cases=total_cases,
        completed_cases=completed_count,
        skipped_existing=completed_count,
        current_index=None,
        current_case_id="",
        last_completed_case_id="",
        current_case_started_at=current_case_started_at,
        last_case_elapsed_seconds=None,
        total_elapsed_seconds=completed_elapsed_seconds,
        average_case_elapsed_seconds=_average_seconds(completed_elapsed_seconds, completed_count),
        estimated_remaining_seconds=_estimated_remaining(completed_elapsed_seconds, completed_count, total_cases - completed_count),
        experiment_started_at=experiment_started_at,
        status="running",
        message="Extraction started.",
    )

    skipped_existing = completed_count
    for idx, case in enumerate(cases):
        case_id = case["case_id"]
        if resume and case_id in completed_ids:
            print(f"Skipped {idx + 1}/{total_cases}: {case_id} already completed")
            continue
        current_case_started_at = _now()
        case_started = perf_counter()
        _write_progress(
            progress_path,
            input_path=input_path,
            output_path=output_path,
            total_cases=total_cases,
            completed_cases=completed_count,
            skipped_existing=skipped_existing,
            current_index=idx + 1,
            current_case_id=case_id,
            last_completed_case_id="",
            current_case_started_at=current_case_started_at,
            last_case_elapsed_seconds=None,
            total_elapsed_seconds=completed_elapsed_seconds,
            average_case_elapsed_seconds=_average_seconds(completed_elapsed_seconds, completed_count),
            estimated_remaining_seconds=_estimated_remaining(completed_elapsed_seconds, completed_count, total_cases - completed_count),
            experiment_started_at=experiment_started_at,
            status="running",
            message=f"Extracting case {idx + 1}/{total_cases}.",
        )
        result = extract_one_case(
            case=case,
            client=client,
            validator=validator,
            ontology_types=ontology_types,
            vote_count=vote_count,
            min_vote_margin=min_vote_margin,
            gleaning_rounds=gleaning_rounds,
            validation_rounds=validation_rounds,
        )
        case_elapsed = round(perf_counter() - case_started, 3)
        result["timing"] = {
            "case_index": idx + 1,
            "total_cases": total_cases,
            "started_at": current_case_started_at,
            "completed_at": _now(),
            "elapsed_seconds": case_elapsed,
        }
        append_jsonl(output_path, result)
        completed_ids.add(case_id)
        completed_count += 1
        completed_elapsed_seconds += case_elapsed
        last_case_elapsed = case_elapsed
        remaining = total_cases - completed_count
        _write_progress(
            progress_path,
            input_path=input_path,
            output_path=output_path,
            total_cases=total_cases,
            completed_cases=completed_count,
            skipped_existing=skipped_existing,
            current_index=idx + 1,
            current_case_id=case_id,
            last_completed_case_id=case_id,
            current_case_started_at="",
            last_case_elapsed_seconds=case_elapsed,
            total_elapsed_seconds=completed_elapsed_seconds,
            average_case_elapsed_seconds=_average_seconds(completed_elapsed_seconds, completed_count),
            estimated_remaining_seconds=_estimated_remaining(completed_elapsed_seconds, completed_count, remaining),
            experiment_started_at=experiment_started_at,
            status="running",
            message=f"Completed case {idx + 1}/{total_cases}.",
        )
        print(
            f"Extracted {idx + 1}/{total_cases}: {case_id} "
            f"elapsed={case_elapsed:.1f}s avg={_average_seconds(completed_elapsed_seconds, completed_count):.1f}s "
            f"needs_review={result['needs_review']}",
            flush=True,
        )

    _write_progress(
        progress_path,
        input_path=input_path,
        output_path=output_path,
        total_cases=total_cases,
        completed_cases=completed_count,
        skipped_existing=skipped_existing,
        current_index=None,
        current_case_id="",
        last_completed_case_id="",
        current_case_started_at="",
        last_case_elapsed_seconds=last_case_elapsed,
        total_elapsed_seconds=completed_elapsed_seconds,
        average_case_elapsed_seconds=_average_seconds(completed_elapsed_seconds, completed_count),
        estimated_remaining_seconds=0.0,
        experiment_started_at=experiment_started_at,
        status="completed",
        message="Extraction completed.",
    )
    print(f"Wrote {completed_count} extraction results to {output_path}")
    return completed_count


def _write_progress(
    progress_path: Path,
    *,
    input_path: Path,
    output_path: Path,
    total_cases: int,
    completed_cases: int,
    skipped_existing: int,
    current_index: int | None,
    current_case_id: str,
    last_completed_case_id: str,
    current_case_started_at: str,
    last_case_elapsed_seconds: float | None,
    total_elapsed_seconds: float,
    average_case_elapsed_seconds: float,
    estimated_remaining_seconds: float,
    experiment_started_at: str,
    status: str,
    message: str,
) -> None:
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    remaining = max(total_cases - completed_cases, 0)
    payload = {
        "status": status,
        "message": message,
        "input": str(input_path),
        "output": str(output_path),
        "total_cases": total_cases,
        "completed_cases": completed_cases,
        "remaining_cases": remaining,
        "percent_complete": round((completed_cases / total_cases * 100) if total_cases else 100.0, 2),
        "skipped_existing": skipped_existing,
        "current_index": current_index,
        "current_case_id": current_case_id,
        "last_completed_case_id": last_completed_case_id,
        "current_case_started_at": current_case_started_at,
        "last_case_elapsed_seconds": last_case_elapsed_seconds,
        "total_elapsed_seconds": round(total_elapsed_seconds, 3),
        "average_case_elapsed_seconds": round(average_case_elapsed_seconds, 3),
        "estimated_remaining_seconds": round(estimated_remaining_seconds, 3),
        "total_elapsed_hms": _format_seconds(total_elapsed_seconds),
        "average_case_elapsed_hms": _format_seconds(average_case_elapsed_seconds),
        "estimated_remaining_hms": _format_seconds(estimated_remaining_seconds),
        "experiment_started_at": experiment_started_at,
        "updated_at": _now(),
    }
    progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _average_seconds(total_seconds: float, completed_count: int) -> float:
    return total_seconds / completed_count if completed_count else 0.0


def _estimated_remaining(total_seconds: float, completed_count: int, remaining_count: int) -> float:
    return _average_seconds(total_seconds, completed_count) * remaining_count if completed_count else 0.0


def _format_seconds(seconds: float | None) -> str:
    seconds = max(float(seconds or 0), 0.0)
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def extract_one_case(
    case: dict[str, Any],
    client: Any,
    validator: OntologyValidator,
    ontology_types: str,
    vote_count: int,
    min_vote_margin: int,
    gleaning_rounds: int,
    validation_rounds: int,
) -> dict[str, Any]:
    case_text = case.get("raw_text", "")

    evidence_spans = build_evidence_spans(case_text)
    entity_result = client.json_chat(graph_entity_prompt(case_text, ontology_types))
    discovered_entities = _clean_entities(entity_result.get("entities", []))

    for _ in range(gleaning_rounds):
        known = json.dumps(discovered_entities, ensure_ascii=False)
        more = client.json_chat(gleaning_prompt(case_text, known, ontology_types)).get("entities", [])
        discovered_entities = _merge_entities(discovered_entities, _clean_entities(more))

    direct_decisions = _vote_questions(
        client,
        case_text,
        DIRECT_CAUSE_QUESTIONS,
        "",
        vote_count,
        min_vote_margin,
        validator,
        validation_rounds,
    )
    accepted_direct = [item for item in direct_decisions if item.get("accepted")]

    capability_decisions: list[dict[str, Any]] = []
    management_decisions: list[dict[str, Any]] = []
    culture_decisions: list[dict[str, Any]] = []
    for direct in accepted_direct:
        context = _context_from_decision("直接原因", direct)
        capability_decisions.extend(
            _vote_questions(client, case_text, CAPABILITY_QUESTIONS, context, vote_count, min_vote_margin, validator, validation_rounds)
        )
        management_decisions.extend(
            _vote_questions(client, case_text, MANAGEMENT_QUESTIONS, context, vote_count, min_vote_margin, validator, validation_rounds)
        )

    accepted_management = [item for item in management_decisions if item.get("accepted")]
    if accepted_management:
        context = _management_context(accepted_management)
        culture_decisions.extend(
            _vote_questions(client, case_text, CULTURE_QUESTIONS, context, vote_count, min_vote_margin, validator, validation_rounds)
        )

    direct_decisions = _dedupe_decisions(direct_decisions)
    capability_decisions = _dedupe_decisions(capability_decisions)
    management_decisions = _dedupe_decisions(management_decisions)
    culture_decisions = _dedupe_decisions(culture_decisions)

    process_decisions = _vote_questions(
        client,
        case_text,
        PROCESS_QUESTIONS,
        "请围绕已确认的事故原因、事故过程和改进措施判断。",
        vote_count,
        min_vote_margin,
        validator,
        validation_rounds,
    )

    entities, triples = _decisions_to_graph(case, discovered_entities, direct_decisions, capability_decisions, management_decisions, culture_decisions, process_decisions)
    graph_validation = validator.validate_graph_records(entities, triples)
    needs_review = (not graph_validation["valid"]) or any(d.get("needs_review") for d in [*direct_decisions, *capability_decisions, *management_decisions, *culture_decisions, *process_decisions])

    return {
        "case_id": case["case_id"],
        "source_file": case.get("source_file", ""),
        "title": case.get("title", ""),
        "stages": {
            "stage_0_evidence_spans": evidence_spans,
            "stage_1_entities": discovered_entities,
            "stage_2_direct_causes": direct_decisions,
            "stage_3_capability_causes": capability_decisions,
            "stage_3_management_causes": management_decisions,
            "stage_3_culture_causes": culture_decisions,
            "stage_4_process_and_controls": process_decisions,
            "stage_5_graph_entities": entities,
            "stage_5_graph_triples": triples,
        },
        "votes": _collect_votes(direct_decisions, capability_decisions, management_decisions, culture_decisions, process_decisions),
        "validation": graph_validation,
        "needs_review": needs_review,
    }


def _vote_questions(
    client: Any,
    case_text: str,
    questions: list[Question],
    context: str,
    vote_count: int,
    min_vote_margin: int,
    validator: OntologyValidator,
    validation_rounds: int,
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for question in questions:
        prompt = yes_no_question_prompt(case_text, question, context)
        decision = vote_json(lambda prompt=prompt: client.json_chat(prompt), vote_count=vote_count, min_vote_margin=min_vote_margin)
        validation = validator.validate_entity_decision(decision)
        repair_history: list[dict[str, Any]] = []
        rounds_left = validation_rounds
        while not validation["valid"] and rounds_left > 0:
            repair_prompt = validation_repair_prompt(
                case_text,
                json.dumps(decision, ensure_ascii=False),
                "; ".join(validation["errors"]),
            )
            repaired = client.json_chat(repair_prompt)
            repaired.setdefault("question_id", question.question_id)
            repaired.setdefault("entity_type", question.target_type)
            repaired.setdefault("relation_type", question.relation_type or "")
            repair_history.append({"before": _decision_snapshot(decision), "after": _decision_snapshot(repaired), "errors": validation["errors"]})
            decision = repaired
            validation = validator.validate_entity_decision(decision)
            rounds_left -= 1
        decision["validation"] = validation
        decision["validation_status"] = validation["validation_status"]
        decision["repair_history"] = repair_history
        if not validation["valid"]:
            decision["needs_review"] = True
        decisions.append(decision)
    return decisions


def _decisions_to_graph(case: dict[str, Any], discovered_entities: list[dict[str, Any]], *groups: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from src.kg_building.graph_records import node_record, rel_record

    nodes: dict[str, dict[str, Any]] = {}
    rels: list[dict[str, Any]] = []
    case_node = {
        "id": f"AccidentCase:{case['case_id']}",
        "label": "AccidentCase",
        "name": case.get("title", case["case_id"]),
        "case_id": case["case_id"],
        "source_file": case.get("source_file", ""),
    }
    nodes[case_node["id"]] = case_node

    for ent in discovered_entities:
        name = ent.get("entity_name") or ent.get("name")
        label = ent.get("entity_type") or ent.get("label")
        if name and label:
            node = node_record(
                label,
                name,
                evidence_text=ent.get("evidence_text", ""),
                source_span_id=ent.get("source_span_id", ""),
                rationale=ent.get("entity_description", ""),
                normalized_name=name,
            )
            nodes.setdefault(node["id"], node)

    direct_nodes: list[dict[str, Any]] = []
    direct_action_nodes: list[dict[str, Any]] = []
    last_management_nodes: list[dict[str, Any]] = []
    for group in groups:
        for decision in group:
            if not decision.get("accepted"):
                continue
            label = decision.get("label") or decision.get("yes_label") or decision.get("question_id")
            entity_type = decision.get("entity_type")
            node = node_record(
                entity_type,
                label,
                evidence_text=decision.get("evidence_text", ""),
                source_span_id="",
                vote_summary=json.dumps(decision.get("vote_summary", {}), ensure_ascii=False),
                rationale=decision.get("rationale", ""),
                normalized_name=label,
                validation_status=decision.get("validation_status", ""),
                needs_review=decision.get("needs_review", False),
            )
            nodes.setdefault(node["id"], node)
            rel_type = decision.get("relation_type")
            if rel_type == "hasDirectCause":
                rels.append(_decision_rel(case_node["id"], rel_type, node["id"], decision))
                direct_nodes.append(node)
                if entity_type == "UnsafeAction":
                    direct_action_nodes.append(node)
            elif rel_type == "hasCapabilityCause" and direct_action_nodes:
                rels.append(_decision_rel(direct_action_nodes[-1]["id"], rel_type, node["id"], decision))
            elif rel_type == "hasManagementCause":
                source = direct_nodes[-1]["id"] if direct_nodes else case_node["id"]
                rels.append(_decision_rel(source, rel_type, node["id"], decision))
                last_management_nodes.append(node)
            elif rel_type == "hasCultureCause" and last_management_nodes:
                rels.append(_decision_rel(last_management_nodes[-1]["id"], rel_type, node["id"], decision))
            elif rel_type == "leadTo" and direct_nodes:
                rels.append(_decision_rel(direct_nodes[-1]["id"], rel_type, node["id"], decision))
            elif rel_type == "controlledBy" and direct_nodes:
                rels.append(_decision_rel(direct_nodes[-1]["id"], rel_type, node["id"], decision))
    return list(nodes.values()), rels


def _decision_rel(source_id: str, rel_type: str, target_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    from src.kg_building.graph_records import rel_record

    return rel_record(
        source_id,
        rel_type,
        target_id,
        question_id=decision.get("question_id", ""),
        answer=decision.get("answer", ""),
        evidence_text=decision.get("evidence_text", ""),
        vote_yes_count=decision.get("vote_summary", {}).get("yes", 0),
        vote_no_count=decision.get("vote_summary", {}).get("no", 0),
        validation_status=decision.get("validation_status", ""),
        needs_review=decision.get("needs_review", False),
    )


def _decision_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": item.get("question_id", ""),
        "answer": item.get("answer", ""),
        "label": item.get("label", ""),
        "entity_type": item.get("entity_type", ""),
        "relation_type": item.get("relation_type", ""),
        "evidence_text": item.get("evidence_text", ""),
        "confidence": item.get("confidence", None),
        "needs_review": item.get("needs_review", False),
    }


def _clean_entities(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in items:
        name = (item.get("entity_name") or item.get("name") or "").strip()
        entity_type = (item.get("entity_type") or item.get("label") or "").strip()
        evidence = (item.get("evidence_text") or "").strip()
        if name and entity_type and evidence:
            item["entity_name"] = name
            item["entity_type"] = entity_type
            item["evidence_text"] = evidence
            cleaned.append(item)
    return cleaned


def _merge_entities(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = {(item.get("entity_name"), item.get("entity_type")) for item in left}
    merged = list(left)
    for item in right:
        key = (item.get("entity_name"), item.get("entity_type"))
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged


def _dedupe_decisions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    passthrough: list[dict[str, Any]] = []
    for item in items:
        if not item.get("accepted"):
            passthrough.append(item)
            continue
        label = _canonical_label(item.get("entity_type", ""), item.get("label", ""))
        item["label"] = label
        key = (
            item.get("question_id", ""),
            item.get("entity_type", ""),
            item.get("relation_type", ""),
            label,
        )
        current = best.get(key)
        if current is None or _decision_score(item) > _decision_score(current):
            best[key] = item
    return passthrough + list(best.values())


def _canonical_label(entity_type: str, label: str) -> str:
    label = (label or "").strip()
    if entity_type != "SafetyCultureDefect":
        return label
    if any(token in label for token in ["抢", "进度", "工期", "生产"]):
        return "重进度轻安全"
    if any(token in label for token in ["投入", "保障", "防护", "资源"]):
        return "安全投入不足"
    if any(token in label for token in ["责任", "重视", "置若罔闻", "执行"]):
        return "安全责任意识淡薄"
    return label


def _decision_score(item: dict[str, Any]) -> float:
    votes = item.get("vote_summary", {})
    return float(votes.get("yes", 0)) + float(item.get("confidence") or 0)


def _management_context(items: list[dict[str, Any]]) -> str:
    lines = ["已确认的安全管理体系缺陷如下。请只在原文存在明确深层组织价值取向证据时，才继续判定安全文化缺陷："]
    for item in items:
        lines.append(f"- {item.get('label', '')}: {item.get('evidence_text', '')}")
    return "\n".join(lines)


def _context_from_decision(prefix: str, decision: dict[str, Any]) -> str:
    return f"{prefix}: {decision.get('label', '')}; 证据: {decision.get('evidence_text', '')}"


def _collect_votes(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"question_id": item.get("question_id"), "vote_summary": item.get("vote_summary"), "accepted": item.get("accepted")}
        for group in groups
        for item in group
    ]


def _extract_between(text: str, left: str, right: str) -> str:
    start = text.find(left)
    if start < 0:
        return ""
    start += len(left)
    end = text.find(right, start)
    return text[start:end] if end >= 0 else ""


def _first_evidence(text: str) -> str:
    marker = "事故文本："
    value = text.split(marker, 1)[-1].strip() if marker in text else text.strip()
    for part in value.replace("\n", "。").split("。"):
        part = part.strip()
        if 6 <= len(part) <= 120:
            return part
    return value[:120]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run staged 24Model question-guided LLM extraction.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N cases.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic mock responses without API calls.")
    parser.add_argument("--input", default=None, help="Optional input cases JSONL path, relative to project root if not absolute.")
    parser.add_argument("--output", default=None, help="Optional output JSONL path, relative to project root if not absolute.")
    parser.add_argument("--progress-output", default=None, help="Optional progress JSON path, relative to project root if not absolute.")
    parser.add_argument("--restart", action="store_true", help="Overwrite existing output instead of resuming completed cases.")
    args = parser.parse_args()
    extract_cases(
        limit=args.limit,
        config_path=args.config,
        dry_run=args.dry_run,
        output=args.output,
        input_path=args.input,
        resume=not args.restart,
        progress_output=args.progress_output,
    )


if __name__ == "__main__":
    main()
