# 3.3 Automated construction of HEC-KG via question-guided LLMs

Given the anonymized hydraulic engineering construction (HEC) accident reports and the ontology defined in Section 3.2, we construct the HEC accident knowledge graph (HEC-KG) through a three-stage pipeline. Let \(\mathcal{D}=\{x_i\}_{i=1}^{N}\) denote the accident-report corpus, where \(x_i\) is the narrative text of case \(i\), and let \(\mathcal{O}=(\mathcal{T},\mathcal{R},\mathcal{C})\) denote the HEC accident ontology. Here, \(\mathcal{T}\) is the set of entity types, \(\mathcal{R}\) is the set of admissible relation types, and \(\mathcal{C}\) contains domain and type constraints derived from the sixth version of 24Model. The objective is to transform each report into an evidence-grounded case graph \(G_i=(V_i,E_i)\) and subsequently integrate all case graphs into a canonical graph

\[
G^{*}=\operatorname{Fuse}\left(\bigcup_{i=1}^{N}G_i\right).
\tag{1}
\]

The pipeline separates entity discovery from causal-relation adjudication. This design prevents an LLM from generating an unconstrained graph in a single response and makes every accepted causal relation traceable to a predefined 24Model question, a model-returned evidence phrase, a voting record, and an ontology-validation result. Table 3 summarizes the three stages. The complete prompts and question bank used in the implementation are reported in Appendix B in their original Chinese form because the source accident reports are written in Chinese.

**Table 3. Three-stage construction pipeline for HEC-KG.**

| Stage | Main operation | Input | Output | Reliability mechanism |
| --- | --- | --- | --- | --- |
| I | Evidence-grounded entity identification | An anonymized accident report and the ontology entity types | Candidate HEC domain, accident, causal, process, consequence, and control entities | Evidence requirement, structured JSON output, deterministic cleaning, and one gleaning round |
| II | Question-guided causal-relation reasoning | Candidate entities, accident text, and accepted upstream factors | Accepted 24Model factors and typed causal relations | Closed question bank, conditional questioning, Yes/No adjudication, three repeated votes, and minimum vote margin |
| III | Ontology verification, cross-case fusion, and graph instantiation | Case-level entities, relations, evidence, and vote traces | Canonical entities, canonical triples, conflict records, and the final HEC-KG | Schema validation, bounded repair, same-type alignment, string and embedding similarity, NIL detection, and provenance-preserving merge |

## 3.3.1 Stage I: Evidence-grounded identification of HEC accident entities

The first stage identifies entities that describe the accident context, 24Model causal factors, accident evolution, consequences, and preventive measures. Before the LLM is called, each report is deterministically divided at sentence-level delimiters, including line breaks, Chinese full stops, and semicolons. A span longer than \(L_{\max}=360\) Chinese characters is further divided into fixed-length segments:

\[
\mathcal{S}_i=\operatorname{Segment}(x_i;L_{\max})
=\{(s_{ij},t_{ij})\}_{j=1}^{M_i},
\qquad |t_{ij}|\leq L_{\max},
\tag{2}
\]

where \(s_{ij}\) is a stable span identifier and \(t_{ij}\) is its text. These spans are retained as case-level evidence anchors. In addition, every entity returned by the LLM is required to contain a concise `evidence_text` copied from the report and may provide a `source_span_id` for provenance tracking.

Entity discovery is restricted to the entity types in \(\mathcal{T}\). These include the HEC context types `AccidentType`, `ConstructionActivity`, `EngineeringObject`, `EnvironmentCondition`, and `EquipmentFacility`; the 24Model causal types `UnsafeAction`, `UnsafeObjectState`, `SafetyCapabilityDefect`, `SafetyManagementDefect`, and `SafetyCultureDefect`; and the outcome and control types `AccidentProcess`, `Consequence`, and `PreventiveMeasure`. The initial candidate set is obtained using a GraphRAG-style structured extraction prompt [1]:

\[
\widehat{V}^{(0)}_i=operatorname{Clean}\left[
\operatorname{LLM}\left(P_{\mathrm{ent}}(x_i,\mathcal{T})\right)
\right].
\tag{3}
\]

The prompt requests five fields for each candidate: entity name, entity type, entity description, evidence text, and source span identifier. The deterministic cleaning operation removes records with an empty name, type, or evidence field. This discovery step is recall-oriented and therefore does not yet decide whether a candidate participates in a 24Model causal relation.

An additional gleaning call is used to recover entities missed by the initial pass. Given the current candidate set, the model is asked to return only omitted entities. For \(g=1,\ldots,G\),

\[
\widehat{V}^{(g)}_i=widehat{V}^{(g-1)}_i\cup
\operatorname{Clean}\left[
\operatorname{LLM}\left(P_{\mathrm{glean}}
(x_i,\widehat{V}^{(g-1)}_i,\mathcal{T})\right)
\right],
\tag{4}
\]

where duplicate candidates are removed using the pair `(entity_name, entity_type)`. We set \(G=1\) to bound the number of calls while retaining an explicit second opportunity to discover omitted entities. The resulting set \(\widehat{V}_i=\widehat{V}^{(G)}_i\) is passed to the relation-reasoning stage.

## 3.3.2 Stage II: Question-guided inference of causal relations between HEC accident entities

Free-form relation generation can blur the boundaries between direct causes, individual safety capability, safety management, and safety culture. We therefore formulate relation inference as a sequence of binary adjudication tasks. The question bank contains 16 questions derived from the ontology and is partitioned into direct-cause questions \(\mathcal{Q}_{D}\), safety-capability questions \(\mathcal{Q}_{C}\), safety-management questions \(\mathcal{Q}_{M}\), safety-culture questions \(\mathcal{Q}_{S}\), and accident-process and control questions \(\mathcal{Q}_{P}\):

\[
\mathcal{Q}=\mathcal{Q}_{D}\cup\mathcal{Q}_{C}\cup
\mathcal{Q}_{M}\cup\mathcal{Q}_{S}\cup\mathcal{Q}_{P},
\qquad |\mathcal{Q}|=2+4+5+3+2=16.
\tag{5}
\]

Each question is represented as

\[
q=(id_q,\,stage_q,\,\tau_q,\,\rho_q,\,text_q,\,def_q),
\tag{6}
\]

where \(\tau_q\in\mathcal{T}\) is the target entity type and \(\rho_q\in\mathcal{R}\) is the relation type to be instantiated when the judgment is accepted. The LLM is not allowed to invent a predicate. Instead, it determines whether the report supports the factor and the ontology fixes the corresponding relation. Each response must follow a JSON schema containing `answer`, `label`, `entity_type`, `relation_type`, `evidence_text`, `rationale`, and `confidence`. Evidence-insufficient cases are explicitly assigned `no`.

The questions are posed conditionally in the causal order prescribed by 24Model. First, two direct-cause questions independently test whether an unsafe action or unsafe object state directly contributed to the accident. For each accepted direct cause, four safety-capability questions and five safety-management questions are then evaluated using the accepted factor and its evidence as context. Safety-culture questions are activated only when at least one safety-management defect has been accepted. Their context contains the accepted management defects and supporting evidence, which prevents the cultural layer from being inferred independently of an organizational-management mechanism. Finally, the accident-process and preventive-measure questions are asked once for each report to capture accident evolution and available risk controls.

This conditional cascade instantiates the six relation patterns used by the experimental orchestrator:

\[
\begin{aligned}
&\texttt{AccidentCase}\xrightarrow{\texttt{hasDirectCause}}
\{\texttt{UnsafeAction},\texttt{UnsafeObjectState}\},\\
&\texttt{UnsafeAction}\xrightarrow{\texttt{hasCapabilityCause}}
\texttt{SafetyCapabilityDefect},\\
&\{\texttt{UnsafeAction},\texttt{UnsafeObjectState}\}
\xrightarrow{\texttt{hasManagementCause}}
\texttt{SafetyManagementDefect},\\
&\texttt{SafetyManagementDefect}\xrightarrow{\texttt{hasCultureCause}}
\texttt{SafetyCultureDefect},\\
&\{\texttt{UnsafeAction},\texttt{UnsafeObjectState}\}
\xrightarrow{\texttt{leadTo}}
\texttt{AccidentProcess},\\
&\{\texttt{UnsafeAction},\texttt{UnsafeObjectState}\}
\xrightarrow{\texttt{controlledBy}}
\texttt{PreventiveMeasure}.
\end{aligned}
\tag{7}
\]

The first-stage discovery output may also contain contextual and consequence entities. In the reported implementation, however, causal relation instantiation is limited to the six patterns in Eq. (7); the ontology-bound question identifier determines the predicate and the accepted upstream factor determines the source node.

Every question is evaluated three times. This adapts self-consistency reasoning [2] to structured causal adjudication: the repeated outputs are aggregated over the final Yes/No decision rather than over a hidden chain of thought. Let \(a_{iq}^{(t)}\in\{\mathrm{yes},\mathrm{no}\}\) denote vote \(t\) for question \(q\) in case \(i\), with \(T=3\). The vote counts and margin are

\[
n_{\mathrm{yes}}=\sum_{t=1}^{T}\mathbb{I}
\left(a_{iq}^{(t)}=\mathrm{yes}\right),
\qquad
n_{\mathrm{no}}=T-n_{\mathrm{yes}},
\qquad
m=|n_{\mathrm{yes}}-n_{\mathrm{no}}|.
\tag{8}
\]

The decision is accepted only when Yes is the majority and the margin satisfies \(m\geq m_{\min}\), where \(m_{\min}=1\):

\[
A_{iq}=\mathbb{I}\left[n_{\mathrm{yes}}>n_{\mathrm{no}}
\ \land\ m\geq m_{\min}\right].
\tag{9}
\]

Among the responses that agree with the majority, the response with the highest reported confidence supplies the representative label, evidence, and concise rationale. All individual votes are retained, including rejected decisions. Consequently, each instantiated causal relation can be traced to a question identifier, the supporting text, the vote counts, and the model confidence.

## 3.3.3 Stage III: Ontology verification, knowledge fusion, and HEC-KG instantiation

The third stage converts accepted judgments into a schema-consistent and cross-case canonical graph. Before graph insertion, the ontology validator checks every accepted entity judgment for a valid entity type, a non-empty label, and non-empty evidence. It also verifies that the subject and object types of each relation conform to the admissible domain and range of the ontology relation. Safety-culture judgments receive an additional evidence gate because ordinary training, supervision, planning, or hazard-control deficiencies do not by themselves establish an organizational culture defect. A culture judgment is valid only when its label, evidence, or rationale contains an explicit organizational value or persistent-execution marker, such as schedule being prioritized over safety, insufficient safety investment, long-term non-compliance, or weak organizational accountability. When the evidence contains only management-level markers and no culture marker, the judgment is rejected at the cultural layer.

An invalid judgment is passed to a bounded repair prompt together with the validator error. The LLM must either correct the type or relation using evidence already present in the report, or change the answer to `no` when sufficient evidence is unavailable. With a maximum of \(R=1\) repair round, the verification process is

\[
d^{(r+1)}_{iq}=\operatorname{LLM}
\left(P_{\mathrm{repair}}(x_i,d^{(r)}_{iq},
\operatorname{Err}_{\mathcal{O}}(d^{(r)}_{iq}))\right),
\qquad r<R.
\tag{10}
\]

Unresolved records are retained with `needs_review=true` for audit but are not treated as validated graph knowledge. Valid decisions are instantiated as nodes and directed edges in the case graph. Node properties include the entity type, name, evidence, rationale, vote summary, confidence, validation status, source case, and source span when available. Edge properties include the question identifier, relation type, evidence, Yes/No vote counts, and validation status. Culture-factor labels are additionally mapped to the controlled vocabulary `重进度轻安全` (schedule/production prioritized over safety), `安全投入不足` (insufficient safety investment), and `安全责任意识淡薄` (weak safety accountability) when the extracted wording contains the corresponding lexical cues.

Case-level graphs still contain repeated or variant mentions across accident reports. We therefore apply offline entity alignment before constructing the final HEC-KG. Entity names are normalized by removing redundant whitespace, harmonizing punctuation, applying type-specific aliases, and deleting weak suffixes when their removal preserves a meaningful concept. Candidate retrieval is restricted to entities with the same ontology type, preventing semantically related concepts from different 24Model layers from being merged. For a mention \(v\) and a candidate canonical entity \(c\), string similarity \(s_{\mathrm{str}}(v,c)\) is computed using exact match, containment, and sequence similarity. Candidates with \(s_{\mathrm{str}}\geq0.72\) are retained, with at most ten candidates per mention.

The retained candidates are reranked with embeddings generated by `text-embedding-3-large`. The final alignment score combines string and vector similarity:

\[
s(v,c)=\lambda s_{\mathrm{str}}(v,c)
+(1-\lambda)s_{\mathrm{vec}}(v,c),
\qquad \lambda=0.4,
\tag{11}
\]

where \(s_{\mathrm{vec}}\) is cosine similarity and the vector contribution therefore receives a weight of 0.6. Let \(c^{*}=\arg\max_c s(v,c)\). The alignment rule is

\[
\operatorname{Align}(v)=
\begin{cases}
c^{*}, & s(v,c^{*})\geq0.80,\\
\operatorname{NIL}(v), & s(v,c^{*})<0.68\text{ or no candidate exists},\\
\operatorname{NIL}_{\mathrm{review}}(v), & 0.68\leq s(v,c^{*})<0.80.
\end{cases}
\tag{12}
\]

A NIL decision creates a new canonical entity. Low-margin NIL decisions are additionally marked for review. When mentions are aligned, the canonical entity preserves all aliases, source entity identifiers, source cases, evidence texts, source spans, rationales, vote summaries, and confidence values. This design retains the evidence contributed by each report rather than replacing the aligned mentions with a single unsupported label.

After entity alignment, every triple endpoint is rewritten using the canonical-entity mapping. Triples with the same canonical source, relation type, and canonical target are merged:

\[
e^{*}_{abc}=\operatorname{Merge}
\{e\mid src(e)=a,\ rel(e)=b,\ tgt(e)=c\}.
\tag{13}
\]

The merged relation records its frequency (`weight`), number of distinct source cases, number of distinct evidence phrases, mean confidence, aggregated Yes-vote ratio, source question identifiers, and validation status. Same-name entities assigned to different ontology types are not merged and are written to the conflict file. The resulting canonical entities and triples form \(G^{*}\), which is exported to Neo4j while preserving sufficient provenance to trace a graph assertion back to its accident report, evidence, question, and voting history.

# Appendix B. Full prompts, question bank, and reproducibility settings

The prompts below are reproduced from the experimental implementation. Placeholders enclosed in braces are replaced at runtime. Chinese was retained because the accident reports and ontology labels used by the extraction model were Chinese. Table B1 distinguishes prompts invoked by the reported pipeline from an auxiliary template present in the source code but not called by the experimental orchestrator.

## B.1 Prompt inventory

**Table B1. Prompt templates and execution status.**

| Prompt | Runtime function | Execution status | Purpose |
| --- | --- | --- | --- |
| Entity discovery | `graph_entity_prompt` | Invoked once per case | Identify ontology-typed candidate entities with evidence |
| Gleaning | `gleaning_prompt` | Invoked once per case by default | Recover entities omitted by the initial discovery call |
| Yes/No adjudication | `yes_no_question_prompt` | Invoked for each activated question and repeated three times | Decide whether a 24Model factor-relation statement is supported |
| Validation repair | `validation_repair_prompt` | Conditionally invoked, at most once per invalid decision | Correct schema/evidence errors or downgrade unsupported decisions |
| Pairwise relation review | `relation_question_prompt` | Defined in the source code but not invoked by the reported extraction orchestrator | Reserved auxiliary template; not part of the reported experiment |

## B.2 Entity-discovery prompt

**Table B2. Complete entity-discovery prompt.**

<table>
<tr><th>Field</th><th>Exact prompt content</th></tr>
<tr><td>Runtime placeholders</td><td><code>{ontology_types}</code>, <code>{HYDRAULIC_FEW_SHOTS}</code>, and <code>{case_text}</code></td></tr>
<tr><td>Complete prompt</td><td><pre>
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
{
  "entities": [
    {
      "entity_name": "",
      "entity_type": "",
      "entity_description": "",
      "evidence_text": "",
      "source_span_id": "",
      "relationship_hints": ["可能相关的实体或关系"]
    }
  ]
}

领域 few-shot：
{HYDRAULIC_FEW_SHOTS}

真实事故文本：
{case_text}
</pre></td></tr>
</table>

## B.3 Gleaning prompt

**Table B3. Complete gleaning prompt.**

<table>
<tr><th>Field</th><th>Exact prompt content</th></tr>
<tr><td>Runtime placeholders</td><td><code>{known_entities_json}</code>, <code>{ontology_types}</code>, and <code>{case_text}</code></td></tr>
<tr><td>Complete prompt</td><td><pre>
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
{"entities": []}

事故文本：
{case_text}
</pre></td></tr>
</table>

## B.4 Question-guided Yes/No adjudication prompt

**Table B4. Complete question-adjudication prompt.**

<table>
<tr><th>Field</th><th>Exact prompt content</th></tr>
<tr><td>Runtime placeholders</td><td><code>{question.target_type}</code>, <code>{question.relation_type}</code>, <code>{question.definition}</code>, <code>{question.text}</code>, <code>{context}</code>, <code>{culture_rules}</code>, <code>{question.question_id}</code>, <code>{HYDRAULIC_FEW_SHOTS}</code>, and <code>{case_text}</code></td></tr>
<tr><td>Complete prompt</td><td><pre>
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
{
  "question_id": "{question.question_id}",
  "answer": "yes/no",
  "label": "",
  "entity_type": "{question.target_type}",
  "relation_type": "{question.relation_type or ""}",
  "evidence_text": "",
  "rationale": "",
  "confidence": 0.0
}

few-shot：
{HYDRAULIC_FEW_SHOTS}

事故文本：
{case_text}
</pre></td></tr>
</table>

For the three safety-culture questions, `{culture_rules}` is replaced by the following additional block.

**Table B5. Additional hard constraints inserted into safety-culture prompts.**

<table>
<tr><th>Field</th><th>Exact prompt content</th></tr>
<tr><td>Culture constraint block</td><td><pre>
安全文化层额外硬约束：
1. SafetyCultureDefect 是深层组织文化原因，不是普通管理缺陷的同义改写。
2. 只有当原文明确出现组织价值取向或长期执行取向证据时才回答 yes，例如：抢工程进度、重生产轻安全、对安全重视不够、安全投入不足、置若罔闻、长期不落实整改、制度流于形式。
3. 如果 evidence_text 只能证明“培训不足、监督不力、方案缺陷、隐患排查不到位”，但不能证明深层组织文化取向，必须回答 no。
4. yes 的 label 应优先使用标准文化因素名称：重进度轻安全、安全投入不足、安全责任意识淡薄、安全文化执行力不足。
</pre></td></tr>
</table>

## B.5 Validation-repair prompt

**Table B6. Complete validation-repair prompt.**

<table>
<tr><th>Field</th><th>Exact prompt content</th></tr>
<tr><td>Runtime placeholders</td><td><code>{reason}</code>, <code>{invalid_item_json}</code>, and <code>{case_text}</code></td></tr>
<tr><td>Complete prompt</td><td><pre>
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
</pre></td></tr>
</table>

## B.6 Few-shot examples embedded in the prompts

**Table B7. Complete few-shot examples used for entity discovery and Yes/No adjudication.**

| Example | Accident text and question | Expected JSON output |
| --- | --- | --- |
| Positive unsafe-action example | Text: `作业人员在高处作业时未系安全带，临边未设置防护栏杆，坠落后死亡。`<br>Question: `事故中是否存在人的不安全动作直接促成事故发生？` | `{"answer":"yes","label":"未系安全带","evidence_text":"作业人员在高处作业时未系安全带","rationale":"原文明确描述人员未使用安全带，该行为直接导致坠落风险。","confidence":0.93}` |
| Positive unsafe-state example | Text: `基坑开挖过程中未按方案设置支护，连续降雨后边坡失稳坍塌。`<br>Question: `事故中是否存在物的不安全状态直接促成事故发生？` | `{"answer":"yes","label":"边坡支护不足","evidence_text":"未按方案设置支护，连续降雨后边坡失稳坍塌","rationale":"支护不足和边坡失稳是事故发生前的危险状态。","confidence":0.91}` |
| Positive management-defect example | Text: `项目部未进行专项安全技术交底，现场管理人员未及时发现围堰渗漏扩大。`<br>Question: `该事故原因是否与安全教育培训不足有关？` | `{"answer":"yes","label":"专项安全技术交底不足","evidence_text":"项目部未进行专项安全技术交底","rationale":"原文直接指出专项交底缺失，属于安全培训和交底不足。","confidence":0.88}` |
| Negative safety-culture example | Text: `现场安全员未及时发现临边防护缺失。`<br>Question: `文本是否明确表明组织存在重进度、重成本、重生产而轻安全的价值取向，并且该取向能够解释已确认的管理缺陷？` | `{"answer":"no","label":"","evidence_text":"","rationale":"原文只说明现场监督问题，没有明确出现抢进度、重生产轻安全、成本压缩或类似组织价值取向证据。","confidence":0.82}` |

## B.7 Complete 24Model question bank

**Table B8. Complete question bank used by the adjudication stage.**

| ID | Activated stage | Target type | Relation type | Exact question | Operational definition |
| --- | --- | --- | --- | --- | --- |
| D1_UNSAFE_ACTION | Direct cause | UnsafeAction | hasDirectCause | 事故中是否存在人的不安全动作直接促成事故发生？ | 人的不安全动作指作业人员、管理人员或相关人员实施的违章操作、违章指挥、冒险作业、未使用防护用品、未按方案施工等具体行为。 |
| D2_UNSAFE_OBJECT_STATE | Direct cause | UnsafeObjectState | hasDirectCause | 事故中是否存在物的不安全状态直接促成事故发生？ | 物的不安全状态指设备、设施、材料、工程结构、临时结构或施工环境处于危险状态，如支护不足、围堰渗漏、边坡失稳、防护缺失、设备故障等。 |
| C1_SAFETY_KNOWLEDGE | Capability cause | SafetyCapabilityDefect | hasCapabilityCause | 该直接原因是否与人员安全知识不足有关？ | 安全知识不足指人员不了解安全规程、专项方案、风险识别方法、设备使用要求或应急处置要求。 |
| C2_SAFETY_AWARENESS | Capability cause | SafetyCapabilityDefect | hasCapabilityCause | 该直接原因是否与人员安全意识薄弱或风险感知不足有关？ | 安全意识薄弱指人员轻视危险、未能识别明显风险、忽视警示、存在侥幸心理或冒险倾向。 |
| C3_SAFETY_HABIT | Capability cause | SafetyCapabilityDefect | hasCapabilityCause | 该直接原因是否与不良安全习惯或习惯性违章有关？ | 安全习惯不良指长期形成的不按规程作业、不佩戴防护用品、图省事、凭经验替代制度等行为倾向。 |
| C4_PSYCHO_PHYSIO | Capability cause | SafetyCapabilityDefect | hasCapabilityCause | 该直接原因是否与人员心理状态或生理状态不佳有关？ | 心理或生理状态不佳包括疲劳、紧张、急躁、注意力不集中、身体不适、情绪异常等影响安全行为的状态。 |
| M1_TRAINING | Management cause | SafetyManagementDefect | hasManagementCause | 该事故原因是否与安全教育培训不足有关？ | 安全培训不足包括未开展三级教育、专项安全技术交底不足、培训流于形式、作业人员不了解风险和控制措施。 |
| M2_PLAN | Management cause | SafetyManagementDefect | hasManagementCause | 该事故原因是否与专项施工方案、技术措施或施工组织设计缺陷有关？ | 方案缺陷包括未编制专项方案、方案审查不足、措施不具体、未按地质水文条件调整方案或方案未落实。 |
| M3_SUPERVISION | Management cause | SafetyManagementDefect | hasManagementCause | 该事故原因是否与现场监督检查不到位有关？ | 监督检查不到位包括旁站缺失、巡查不及时、违章未制止、重大危险源未监控、监理或管理人员履职不足。 |
| M4_HAZARD | Management cause | SafetyManagementDefect | hasManagementCause | 该事故原因是否与隐患排查治理或风险管控不到位有关？ | 隐患排查治理不到位包括未识别危险源、隐患整改不闭环、风险分级管控缺失、监测预警和应急准备不足。 |
| M5_RESPONSIBILITY | Management cause | SafetyManagementDefect | hasManagementCause | 该事故原因是否与安全责任不落实或组织协调失效有关？ | 责任落实不到位包括职责不清、层层转包导致管理断裂、交叉作业协调不足、项目部和班组安全责任未落实。 |
| S1_SAFETY_PRIORITY | Culture cause | SafetyCultureDefect | hasCultureCause | 文本是否明确表明组织存在重进度、重成本、重生产而轻安全的价值取向，并且该取向能够解释已确认的管理缺陷？ | 重进度轻安全是安全文化缺陷，必须有明确组织层证据，如抢工期、抢工程进度、重生产轻安全、忽视安全整改、为进度或成本牺牲安全。不能仅因存在培训不足、监督不力或隐患排查不到位就推断为该文化缺陷。 |
| S2_SAFETY_INVESTMENT | Culture cause | SafetyCultureDefect | hasCultureCause | 文本是否明确表明组织在安全防护、监测、培训、设备维护或应急资源上的投入不足，并且该投入不足能够解释已确认的管理缺陷？ | 安全投入不足是安全文化缺陷，必须有明确组织层证据，如安全设施、防护、监测、培训、设备维护、应急资源投入不足或安全保障长期缺位。不能把单一管理失误或技术措施缺陷自动归为安全投入不足。 |
| S3_ACCOUNTABILITY_CULTURE | Culture cause | SafetyCultureDefect | hasCultureCause | 文本是否明确表明组织或项目管理层存在安全责任意识淡薄、安全制度执行力不足或对整改要求置若罔闻，并且该文化取向能够解释已确认的管理缺陷？ | 安全责任意识淡薄是安全文化缺陷，必须有明确组织层证据，如对安全重视不够、置若罔闻、长期不落实整改、制度执行流于形式、管理层主动履责意识不足。不能仅因事故发生或存在一般管理缺陷就推断。 |
| P1_ACCIDENT_PROCESS | Accident process | AccidentProcess | leadTo | 文本中是否存在清晰的事故演化过程节点，可以表达为 A 导致 B？ | 事故过程节点指从危险状态、触发事件到伤害后果之间的事件链，如渗漏扩大、涌水、失稳、坠落、撞击、伤亡。 |
| R1_CONTROL_MEASURE | Control measure | PreventiveMeasure | controlledBy | 文本中是否给出可控制或预防该风险因素的防控措施？ | 防控措施指可预防、控制或减轻风险的技术、管理、培训、监测、应急或制度措施。 |

## B.8 Auxiliary pairwise relation-review prompt not used in the reported experiment

**Table B9. Complete auxiliary pairwise relation-review prompt and its execution status.**

<table>
<tr><th>Field</th><th>Content</th></tr>
<tr><td>Execution status</td><td>This template is defined in <code>templates.py</code>, but <code>extract.py</code> does not invoke it. Relations in the reported experiment are assigned by the ontology-bound question bank described in Section 3.3.2.</td></tr>
<tr><td>Complete template</td><td><pre>
你是水利工程施工事故知识图谱关系审查专家。请判断候选三元组是否被原文明确支持。

候选三元组：
subject = {subject.name} ({subject.type})
predicate = {predicate}
object = {object.name} ({object.type})

回答规则：
1. 只能回答 yes 或 no；证据不足回答 no。
2. yes 必须提供原文 evidence_text。
3. relationship_description 说明二者为何相关。
4. relationship_strength 为1-10整数，表示关系强度。
5. 输出严格JSON。

输出格式：
{
  "answer": "yes/no",
  "predicate": "{predicate}",
  "evidence_text": "",
  "relationship_description": "",
  "relationship_strength": 0,
  "confidence": 0.0
}

事故文本：
{case_text}
</pre></td></tr>
</table>

## B.9 Implementation settings

**Table B10. Reproducibility settings used by the reported pipeline.**

| Component | Parameter | Value |
| --- | --- | --- |
| LLM extraction | Model | `gpt-4o` |
| LLM extraction | Temperature | 0 |
| LLM extraction | Structured output | JSON object |
| LLM extraction | Maximum API retries | 3 |
| Entity discovery | Maximum evidence-span length | 360 characters |
| Entity discovery | Gleaning rounds \(G\) | 1 |
| Relation adjudication | Repeated votes \(T\) | 3 |
| Relation adjudication | Minimum vote margin \(m_{\min}\) | 1 |
| Ontology verification | Maximum repair rounds \(R\) | 1 |
| Entity fusion | Embedding model | `text-embedding-3-large` |
| Entity fusion | Same-type-only alignment | True |
| Entity fusion | String recall threshold | 0.72 |
| Entity fusion | Maximum recalled candidates | 10 |
| Entity fusion | String similarity weight | 0.4 |
| Entity fusion | Vector similarity weight | 0.6 |
| Entity fusion | Automatic match threshold | 0.80 |
| Entity fusion | NIL threshold | 0.68 |

## Citation records corresponding to the numbered slots

[1] D. Edge, H. Trinh, N. Cheng, J. Bradley, A. Chao, A. Mody, S. Truitt, and J. Larson, “From Local to Global: A Graph RAG Approach to Query-Focused Summarization,” arXiv:2404.16130, 2024.

[2] X. Wang, J. Wei, D. Schuurmans, Q. Le, E. Chi, S. Narang, A. Chowdhery, and D. Zhou, “Self-Consistency Improves Chain of Thought Reasoning in Language Models,” International Conference on Learning Representations, 2023.
