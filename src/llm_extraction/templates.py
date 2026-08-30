from __future__ import annotations

from src.llm_extraction.question_bank import Question


HYDRAULIC_FEW_SHOTS = """
示例1：
文本：作业人员在高处作业时未系安全带，临边未设置防护栏杆，坠落后死亡。
问题：事故中是否存在人的不安全动作直接促成事故发生？
输出：{"answer":"yes","label":"未系安全带","evidence_text":"作业人员在高处作业时未系安全带","rationale":"原文明确描述人员未使用安全带，该行为直接导致坠落风险。","confidence":0.93}

示例2：
文本：基坑开挖过程中未按方案设置支护，连续降雨后边坡失稳坍塌。
问题：事故中是否存在物的不安全状态直接促成事故发生？
输出：{"answer":"yes","label":"边坡支护不足","evidence_text":"未按方案设置支护，连续降雨后边坡失稳坍塌","rationale":"支护不足和边坡失稳是事故发生前的危险状态。","confidence":0.91}

示例3：
文本：项目部未进行专项安全技术交底，现场管理人员未及时发现围堰渗漏扩大。
问题：该事故原因是否与安全教育培训不足有关？
输出：{"answer":"yes","label":"专项安全技术交底不足","evidence_text":"项目部未进行专项安全技术交底","rationale":"原文直接指出专项交底缺失，属于安全培训和交底不足。","confidence":0.88}

反例4：
文本：现场安全员未及时发现临边防护缺失。
问题：文本是否明确表明组织存在重进度、重成本、重生产而轻安全的价值取向，并且该取向能够解释已确认的管理缺陷？
输出：{"answer":"no","label":"","evidence_text":"","rationale":"原文只说明现场监督问题，没有明确出现抢进度、重生产轻安全、成本压缩或类似组织价值取向证据。","confidence":0.82}
""".strip()


def graph_entity_prompt(case_text: str, ontology_types: str) -> str:
    return f"""
你是水利工程施工事故知识图谱构建专家。请采用 GraphRAG 式领域实体发现方法，从文本中识别构建24Model知识图谱所需实体。

实体类型只能来自：
{ontology_types}

抽取要求：
1. 只抽取文本中明确出现或由文本直接支持的实体。
2. 每个实体必须给出 evidence_text，证据必须是原文短句。
3. entity_description 要说明该实体在事故中的作用。
4. 不要输出无证据实体，不要把同一实体重复输出。
5. 输出严格JSON。

输出格式：
{{
  "entities": [
    {{
      "entity_name": "",
      "entity_type": "",
      "entity_description": "",
      "evidence_text": "",
      "source_span_id": "",
      "relationship_hints": ["可能相关的实体或关系"]
    }}
  ]
}}

领域 few-shot：
{HYDRAULIC_FEW_SHOTS}

真实事故文本：
{case_text}
""".strip()


def gleaning_prompt(case_text: str, known_entities_json: str, ontology_types: str) -> str:
    return f"""
你正在进行 GraphRAG 式 gleaning 补漏。请检查事故文本中是否还有被遗漏的24Model知识图谱实体。

已识别实体：
{known_entities_json}

允许实体类型：
{ontology_types}

规则：
1. 只补充遗漏实体，不重复已有实体。
2. 每个实体必须给出原文 evidence_text。
3. 如果没有遗漏，返回空数组。
4. 输出严格JSON。

输出格式：
{{"entities": []}}

事故文本：
{case_text}
""".strip()


def yes_no_question_prompt(case_text: str, question: Question, context: str = "") -> str:
    culture_rules = ""
    if question.target_type == "SafetyCultureDefect":
        culture_rules = """
安全文化层额外硬约束：
1. SafetyCultureDefect 是深层组织文化原因，不是普通管理缺陷的同义改写。
2. 只有当原文明确出现组织价值取向或长期执行取向证据时才回答 yes，例如：抢工程进度、重生产轻安全、对安全重视不够、安全投入不足、置若罔闻、长期不落实整改、制度流于形式。
3. 如果 evidence_text 只能证明“培训不足、监督不力、方案缺陷、隐患排查不到位”，但不能证明深层组织文化取向，必须回答 no。
4. yes 的 label 应优先使用标准文化因素名称：重进度轻安全、安全投入不足、安全责任意识淡薄、安全文化执行力不足。
""".strip()
    return f"""
你是熟悉事故致因24Model第6版的水利工程施工事故调查专家。请逐步回答一个判定问题，但不要输出隐藏推理链，只输出可审查的简短依据。

24Model判定对象：
- 目标类型：{question.target_type}
- 关系类型：{question.relation_type or "无"}
- 判定定义：{question.definition}

问题：
{question.text}

上下文对象：
{context or "无。请直接基于事故文本判断。"}

回答规则：
1. 只能回答 "yes" 或 "no"；如果证据不足，回答 "no"。
2. 若回答 yes，label 必须是文本支持的具体实体名称或标准化风险因素名称。
3. evidence_text 必须逐字来自事故文本，尽量短。
4. rationale 只写1-2句可审查理由，不要写冗长思维链。
5. confidence 取0到1。
6. 输出严格JSON，不要输出Markdown。

{culture_rules}

输出格式：
{{
  "question_id": "{question.question_id}",
  "answer": "yes/no",
  "label": "",
  "entity_type": "{question.target_type}",
  "relation_type": "{question.relation_type or ""}",
  "evidence_text": "",
  "rationale": "",
  "confidence": 0.0
}}

few-shot：
{HYDRAULIC_FEW_SHOTS}

事故文本：
{case_text}
""".strip()


def relation_question_prompt(case_text: str, subject: dict, predicate: str, object_: dict) -> str:
    return f"""
你是水利工程施工事故知识图谱关系审查专家。请判断候选三元组是否被原文明确支持。

候选三元组：
subject = {subject.get("name") or subject.get("entity_name")} ({subject.get("label") or subject.get("entity_type")})
predicate = {predicate}
object = {object_.get("name") or object_.get("entity_name")} ({object_.get("label") or object_.get("entity_type")})

回答规则：
1. 只能回答 yes 或 no；证据不足回答 no。
2. yes 必须提供原文 evidence_text。
3. relationship_description 说明二者为何相关。
4. relationship_strength 为1-10整数，表示关系强度。
5. 输出严格JSON。

输出格式：
{{
  "answer": "yes/no",
  "predicate": "{predicate}",
  "evidence_text": "",
  "relationship_description": "",
  "relationship_strength": 0,
  "confidence": 0.0
}}

事故文本：
{case_text}
""".strip()


def validation_repair_prompt(case_text: str, invalid_item_json: str, reason: str) -> str:
    return f"""
你是24Model知识图谱质检专家。以下抽取结果未通过验证，请只根据原文修正。

失败原因：
{reason}

待修正结果：
{invalid_item_json}

修正规则：
1. 若原文没有证据，answer 改为 no，needs_review=true。
2. 若类型或关系方向错误，请改为本体允许的类型/关系。
3. evidence_text 必须来自原文。
4. 输出严格JSON。

事故文本：
{case_text}
""".strip()
