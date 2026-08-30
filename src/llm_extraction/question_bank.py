from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    question_id: str
    stage: str
    target_type: str
    relation_type: str | None
    text: str
    yes_label: str
    definition: str


DIRECT_CAUSE_QUESTIONS = [
    Question(
        question_id="D1_UNSAFE_ACTION",
        stage="direct_cause",
        target_type="UnsafeAction",
        relation_type="hasDirectCause",
        text="事故中是否存在人的不安全动作直接促成事故发生？",
        yes_label="人的不安全动作",
        definition="人的不安全动作指作业人员、管理人员或相关人员实施的违章操作、违章指挥、冒险作业、未使用防护用品、未按方案施工等具体行为。",
    ),
    Question(
        question_id="D2_UNSAFE_OBJECT_STATE",
        stage="direct_cause",
        target_type="UnsafeObjectState",
        relation_type="hasDirectCause",
        text="事故中是否存在物的不安全状态直接促成事故发生？",
        yes_label="物的不安全状态",
        definition="物的不安全状态指设备、设施、材料、工程结构、临时结构或施工环境处于危险状态，如支护不足、围堰渗漏、边坡失稳、防护缺失、设备故障等。",
    ),
]


CAPABILITY_QUESTIONS = [
    Question(
        question_id="C1_SAFETY_KNOWLEDGE",
        stage="capability_cause",
        target_type="SafetyCapabilityDefect",
        relation_type="hasCapabilityCause",
        text="该直接原因是否与人员安全知识不足有关？",
        yes_label="安全知识不足",
        definition="安全知识不足指人员不了解安全规程、专项方案、风险识别方法、设备使用要求或应急处置要求。",
    ),
    Question(
        question_id="C2_SAFETY_AWARENESS",
        stage="capability_cause",
        target_type="SafetyCapabilityDefect",
        relation_type="hasCapabilityCause",
        text="该直接原因是否与人员安全意识薄弱或风险感知不足有关？",
        yes_label="安全意识薄弱",
        definition="安全意识薄弱指人员轻视危险、未能识别明显风险、忽视警示、存在侥幸心理或冒险倾向。",
    ),
    Question(
        question_id="C3_SAFETY_HABIT",
        stage="capability_cause",
        target_type="SafetyCapabilityDefect",
        relation_type="hasCapabilityCause",
        text="该直接原因是否与不良安全习惯或习惯性违章有关？",
        yes_label="安全习惯不良",
        definition="安全习惯不良指长期形成的不按规程作业、不佩戴防护用品、图省事、凭经验替代制度等行为倾向。",
    ),
    Question(
        question_id="C4_PSYCHO_PHYSIO",
        stage="capability_cause",
        target_type="SafetyCapabilityDefect",
        relation_type="hasCapabilityCause",
        text="该直接原因是否与人员心理状态或生理状态不佳有关？",
        yes_label="心理或生理状态不佳",
        definition="心理或生理状态不佳包括疲劳、紧张、急躁、注意力不集中、身体不适、情绪异常等影响安全行为的状态。",
    ),
]


MANAGEMENT_QUESTIONS = [
    Question(
        question_id="M1_TRAINING",
        stage="management_cause",
        target_type="SafetyManagementDefect",
        relation_type="hasManagementCause",
        text="该事故原因是否与安全教育培训不足有关？",
        yes_label="安全培训不足",
        definition="安全培训不足包括未开展三级教育、专项安全技术交底不足、培训流于形式、作业人员不了解风险和控制措施。",
    ),
    Question(
        question_id="M2_PLAN",
        stage="management_cause",
        target_type="SafetyManagementDefect",
        relation_type="hasManagementCause",
        text="该事故原因是否与专项施工方案、技术措施或施工组织设计缺陷有关？",
        yes_label="专项方案或技术措施缺陷",
        definition="方案缺陷包括未编制专项方案、方案审查不足、措施不具体、未按地质水文条件调整方案或方案未落实。",
    ),
    Question(
        question_id="M3_SUPERVISION",
        stage="management_cause",
        target_type="SafetyManagementDefect",
        relation_type="hasManagementCause",
        text="该事故原因是否与现场监督检查不到位有关？",
        yes_label="监督检查不到位",
        definition="监督检查不到位包括旁站缺失、巡查不及时、违章未制止、重大危险源未监控、监理或管理人员履职不足。",
    ),
    Question(
        question_id="M4_HAZARD",
        stage="management_cause",
        target_type="SafetyManagementDefect",
        relation_type="hasManagementCause",
        text="该事故原因是否与隐患排查治理或风险管控不到位有关？",
        yes_label="隐患排查治理不到位",
        definition="隐患排查治理不到位包括未识别危险源、隐患整改不闭环、风险分级管控缺失、监测预警和应急准备不足。",
    ),
    Question(
        question_id="M5_RESPONSIBILITY",
        stage="management_cause",
        target_type="SafetyManagementDefect",
        relation_type="hasManagementCause",
        text="该事故原因是否与安全责任不落实或组织协调失效有关？",
        yes_label="安全责任落实不到位",
        definition="责任落实不到位包括职责不清、层层转包导致管理断裂、交叉作业协调不足、项目部和班组安全责任未落实。",
    ),
]


CULTURE_QUESTIONS = [
    Question(
        question_id="S1_SAFETY_PRIORITY",
        stage="culture_cause",
        target_type="SafetyCultureDefect",
        relation_type="hasCultureCause",
        text="文本是否明确表明组织存在重进度、重成本、重生产而轻安全的价值取向，并且该取向能够解释已确认的管理缺陷？",
        yes_label="重进度轻安全",
        definition="重进度轻安全是安全文化缺陷，必须有明确组织层证据，如抢工期、抢工程进度、重生产轻安全、忽视安全整改、为进度或成本牺牲安全。不能仅因存在培训不足、监督不力或隐患排查不到位就推断为该文化缺陷。",
    ),
    Question(
        question_id="S2_SAFETY_INVESTMENT",
        stage="culture_cause",
        target_type="SafetyCultureDefect",
        relation_type="hasCultureCause",
        text="文本是否明确表明组织在安全防护、监测、培训、设备维护或应急资源上的投入不足，并且该投入不足能够解释已确认的管理缺陷？",
        yes_label="安全投入不足",
        definition="安全投入不足是安全文化缺陷，必须有明确组织层证据，如安全设施、防护、监测、培训、设备维护、应急资源投入不足或安全保障长期缺位。不能把单一管理失误或技术措施缺陷自动归为安全投入不足。",
    ),
    Question(
        question_id="S3_ACCOUNTABILITY_CULTURE",
        stage="culture_cause",
        target_type="SafetyCultureDefect",
        relation_type="hasCultureCause",
        text="文本是否明确表明组织或项目管理层存在安全责任意识淡薄、安全制度执行力不足或对整改要求置若罔闻，并且该文化取向能够解释已确认的管理缺陷？",
        yes_label="安全责任意识淡薄",
        definition="安全责任意识淡薄是安全文化缺陷，必须有明确组织层证据，如对安全重视不够、置若罔闻、长期不落实整改、制度执行流于形式、管理层主动履责意识不足。不能仅因事故发生或存在一般管理缺陷就推断。",
    ),
]


PROCESS_QUESTIONS = [
    Question(
        question_id="P1_ACCIDENT_PROCESS",
        stage="accident_process",
        target_type="AccidentProcess",
        relation_type="leadTo",
        text="文本中是否存在清晰的事故演化过程节点，可以表达为 A 导致 B？",
        yes_label="事故过程节点",
        definition="事故过程节点指从危险状态、触发事件到伤害后果之间的事件链，如渗漏扩大、涌水、失稳、坠落、撞击、伤亡。",
    ),
    Question(
        question_id="R1_CONTROL_MEASURE",
        stage="control_measure",
        target_type="PreventiveMeasure",
        relation_type="controlledBy",
        text="文本中是否给出可控制或预防该风险因素的防控措施？",
        yes_label="防控措施",
        definition="防控措施指可预防、控制或减轻风险的技术、管理、培训、监测、应急或制度措施。",
    ),
]


ALL_QUESTIONS = [
    *DIRECT_CAUSE_QUESTIONS,
    *CAPABILITY_QUESTIONS,
    *MANAGEMENT_QUESTIONS,
    *CULTURE_QUESTIONS,
    *PROCESS_QUESTIONS,
]


def questions_by_stage(stage: str) -> list[Question]:
    return [q for q in ALL_QUESTIONS if q.stage == stage]


def question_ids() -> list[str]:
    return [q.question_id for q in ALL_QUESTIONS]
