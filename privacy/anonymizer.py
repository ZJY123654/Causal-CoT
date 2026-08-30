from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


SENSITIVE_FIELDS = {
    "title",
    "organization",
    "severity_level",
    "location",
    "direct_cause_text",
    "indirect_cause_text",
    "cause_text",
    "process_text",
    "consequence_text",
    "economic_loss_text",
    "measures_text",
    "raw_text",
    "evidence_text",
    "rationale",
    "description",
    "context",
    "source_sentence",
    "original_mention",
}

ORG_PATTERNS = [
    (re.compile(r"(?P<prefix>^|[，。；、\s]|在|由|为|和|（|\()(?P<org>[^在，。；、\s（）()]{2,40}?(?:有限责任公司|有限公司|集团有限公司|集团公司|工程局有限公司|工程局|施工局|联营体|项目经理部|项目部))"), "施工单位"),
    (re.compile(r"(?P<prefix>^|[，。；、\s]|在|由|为|和|（|\()(?P<org>[^在，。；、\s（）()]{2,40}?(?:监理有限公司|监理公司|监理部))"), "监理单位"),
    (re.compile(r"(?P<prefix>^|[，。；、\s]|在|由|为|和|（|\()(?P<org>[^在，。；、\s（）()]{2,40}?(?:建设管理局|建设单位|业主单位))"), "建设单位"),
]

PROJECT_PATTERNS = [
    re.compile(r"[\u4e00-\u9fffA-Za-z0-9（）()·\-]{2,30}(抽水蓄能电站|水电站|电站|水库|枢纽工程|导流洞工程|除险加固工程)"),
    re.compile(r"[\u4e00-\u9fffA-Za-z0-9（）()·\-]{1,20}[A-Z0-9]+标"),
]

PERSON_PATTERN = re.compile(r"[\u4e00-\u9fff]{1,3}某某|[\u4e00-\u9fff]{1,3}某")
ORG_FRAGMENT_PATTERNS = [
    re.compile(r"[^在，。；、\s（）()]{2,30}(?:有限责任公司|有限公司|集团有限公司|集团公司)"),
    re.compile(r"葛洲坝[\u4e00-\u9fffA-Za-z0-9（）()·\-]{0,20}"),
    re.compile(r"中铁[\u4e00-\u9fffA-Za-z0-9（）()·\-]{0,30}"),
    re.compile(r"中国水利水电[\u4e00-\u9fffA-Za-z0-9（）()·\-]{0,30}"),
    re.compile(r"水电[一二三四五六七八九十\d]+局"),
    re.compile(r"[第 一二三四五六七八九十\d]+工程处"),
    re.compile(r"[\u4e00-\u9fff]{2,10}分包队"),
    re.compile(r"施工局"),
    re.compile(r"工程局"),
    re.compile(r"项目经理部"),
    re.compile(r"项目部"),
    re.compile(r"项目公司"),
    re.compile(r"中国三峡集团"),
    re.compile(r"[\u4e00-\u9fff]{2,8}公司"),
]

COMMON_SURNAME_PAIR = re.compile(r"([张王李赵刘陈杨黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康])、([张王李赵刘陈杨黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康])")
NAME_WITH_DEMOGRAPHICS = re.compile(r"([张王李赵刘陈杨黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康][\u4e00-\u9fff]{1,2})(?=（[男女])")


def _letters() -> list[str]:
    return [chr(code) for code in range(ord("A"), ord("Z") + 1)]


@dataclass
class CaseAnonymizer:
    person_map: dict[str, str] = field(default_factory=dict)
    org_map: dict[str, str] = field(default_factory=dict)
    project_map: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=lambda: {"person": 0, "organization": 0, "project": 0})

    def anonymize_text(self, text: str) -> str:
        value = str(text or "")
        if not value:
            return value
        value = self._replace_role_names(value)
        value = PERSON_PATTERN.sub(lambda match: self._placeholder(self.person_map, match.group(0), "作业人员", "person"), value)
        value = COMMON_SURNAME_PAIR.sub(lambda match: self._placeholder(self.person_map, match.group(1), "作业人员", "person") + "、" + self._placeholder(self.person_map, match.group(2), "作业人员", "person"), value)
        value = NAME_WITH_DEMOGRAPHICS.sub(lambda match: self._placeholder(self.person_map, match.group(1), "作业人员", "person"), value)
        value = self._replace_known_persons(value)
        value = self._replace_orgs(value)
        value = self._replace_projects(value)
        return value

    def _replace_projects(self, text: str) -> str:
        for pattern in PROJECT_PATTERNS:
            text = pattern.sub(lambda match: self._project_placeholder(match.group(0), match), text)
        return text

    def _project_placeholder(self, original: str, match: re.Match[str]) -> str:
        if original not in self.project_map:
            suffix = match.group(1) if match.lastindex else "工程"
            self.project_map[original] = f"某{suffix}"
            self.counts["project"] += 1
        return self.project_map[original]

    def _replace_orgs(self, text: str) -> str:
        for pattern, role in ORG_PATTERNS:
            text = pattern.sub(
                lambda match, role=role: match.group("prefix")
                + self._placeholder(self.org_map, match.group("org"), role, "organization"),
                text,
            )
        for pattern in ORG_FRAGMENT_PATTERNS:
            text = pattern.sub(lambda match: self._placeholder(self.org_map, match.group(0), "施工单位", "organization"), text)
        return text

    def _replace_role_names(self, text: str) -> str:
        list_pattern = re.compile(r"(死者|伤者|遇难者|受伤人员|作业人员|施工人员)([\u4e00-\u9fff](?:、[\u4e00-\u9fff])+)")

        def list_repl(match: re.Match[str]) -> str:
            role = match.group(1)
            names = match.group(2).split("、")
            prefix = "死者" if role in {"死者", "遇难者"} else "伤者" if role in {"伤者", "受伤人员"} else "作业人员"
            return "、".join(self._placeholder(self.person_map, name, prefix, "person") for name in names)

        text = list_pattern.sub(list_repl, text)
        role_pattern = re.compile(
            r"(死者|伤者|遇难者|受伤人员|作业人员|施工人员|管理人员|现场管理人员|操作人员|操作员|驾驶员|指挥人员|带班人|班长|队长|工头)"
            r"([\u4e00-\u9fff]{1,3}某某|[\u4e00-\u9fff]{1,3}某|[\u4e00-\u9fff]{2,3})(?=[，,、。；;在因未不从将于和与])"
        )

        def repl(match: re.Match[str]) -> str:
            role = match.group(1)
            name = match.group(2)
            if role in {"死者", "遇难者"}:
                prefix = "死者"
            elif role in {"伤者", "受伤人员"}:
                prefix = "伤者"
            elif role in {"管理人员", "指挥人员"}:
                prefix = "管理人员"
            else:
                prefix = "作业人员"
            return self._placeholder(self.person_map, name, prefix, "person")

        return role_pattern.sub(repl, text)

    def _replace_known_persons(self, text: str) -> str:
        for original, placeholder in sorted(self.person_map.items(), key=lambda item: len(item[0]), reverse=True):
            text = text.replace(original, placeholder)
        return text

    def _placeholder(self, mapping: dict[str, str], original: str, prefix: str, counter_key: str) -> str:
        if original not in mapping:
            letters = _letters()
            index = len(mapping)
            suffix = letters[index] if index < len(letters) else str(index + 1)
            mapping[original] = f"{prefix}{suffix}"
            self.counts[counter_key] += 1
        return mapping[original]


def anonymize_value(value: Any, anonymizer: CaseAnonymizer) -> Any:
    if isinstance(value, str):
        return anonymizer.anonymize_text(value)
    if isinstance(value, list):
        return [anonymize_value(item, anonymizer) for item in value]
    if isinstance(value, dict):
        return anonymize_record(value, anonymizer)
    return value


def anonymize_record(record: dict[str, Any], anonymizer: CaseAnonymizer | None = None) -> dict[str, Any]:
    anonymizer = anonymizer or CaseAnonymizer()
    out: dict[str, Any] = {}
    for key, value in record.items():
        if key in SENSITIVE_FIELDS or key.endswith("_text") or key in {"evidence_texts", "aliases", "rationales"}:
            out[key] = anonymize_value(value, anonymizer)
        else:
            out[key] = value
    out["privacy_status"] = "anonymized"
    return out
