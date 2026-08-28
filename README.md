# 水利工程施工事故知识图谱项目

本项目将水利水电工程施工事故案例汇编清洗为 JSONL，并基于事故致因 24Model 第6版提供 LLM 自动抽取、知识图谱构建、Neo4j CSV 导出和 Neo4j 直接写入能力。

## 1. 安装

```powershell
cd "D:\论文\投稿EAAI\R1\Data and code"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. 配置

复制 `.env.example` 为 `.env`，填入自己的 API key：

```powershell
Copy-Item .env.example .env
```

默认模型配置：

- `OPENAI_BASE_URL=https://yunwu.ai/v1`
- `OPENAI_MODEL=gpt-4o`
- `OPENAI_EMBEDDING_MODEL=text-embedding-3-large`

默认 Neo4j 配置：

```python
graph = Graph("bolt://localhost:7687", auth=("neo4j", "zjy20020111"))
```

也可以通过 `.env` 覆盖：

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=zjy20020111
```

## 3. 数据清洗

```powershell
python -m src.data_cleaning.build_dataset
```

输出：

```text
data/processed/cleaned_cases.jsonl
```

每行是一个事故案例，包含 `case_id`、`source_file`、`title`、`accident_type`、`date`、`location`、`direct_cause_text`、`process_text`、`cause_text`、`consequence_text`、`measures_text`、`raw_text` 等字段。

## 4. 不可逆脱敏

投稿公开数据建议先运行不可逆脱敏，真实人名、公司名、项目部名、施工局名等会被替换为稳定占位词，例如 `作业人员A`、`施工单位A`、`项目部A`；工程地点保留泛化表达。

```powershell
python -m src.privacy.anonymize_cases
```

输出：

```text
data/processed/anonymized_cases.jsonl
data/privacy/anonymization_report.json
```

## 5. 24Model问题引导式 LLM 抽取

当前抽取流程已经从普通 JSON 抽取升级为“问题引导 + 自一致投票 + 循环验证”的阶段式流程：

```text
Stage 0  证据片段切分
Stage 1  GraphRAG式候选实体发现
Stage 1b gleaning补漏
Stage 2  直接原因 Yes/No 判定
Stage 3  安全能力、管理体系、安全文化原因追溯
Stage 4  事故演化与防控措施判定
Stage 5  多轮投票聚合
Stage 6  本体约束验证
```

每个关键判断都会输出：

```text
answer, label, entity_type, relation_type, evidence_text, rationale,
confidence, vote_summary, validation_status, needs_review
```

配置好 `.env` 后运行抽取：

```powershell
python -m src.llm_extraction.extract --input data/processed/anonymized_cases.jsonl
```

抽取支持断点续跑：每完成一个案例就会追加写入 `data/kg/extraction_results.jsonl`，并更新 `data/kg/extraction_progress.json`。如果命令中断，重新运行同一命令会自动跳过已完成案例。每条结果都会记录 `timing.elapsed_seconds`，进度文件会记录总耗时、平均耗时和预计剩余时间。

查看当前进度：

```powershell
python -m src.llm_extraction.progress --input data/processed/anonymized_cases.jsonl
```

如果需要从头重跑抽取，使用：

```powershell
python -m src.llm_extraction.extract --input data/processed/anonymized_cases.jsonl --restart
```

输出：

```text
data/kg/extraction_results.jsonl
data/kg/extraction_progress.json
```

投票和验证参数在 `configs/settings.yaml` 中配置：

```yaml
llm:
  vote_count: 3
  gleaning_rounds: 1
  validation_rounds: 1
  min_vote_margin: 1
```

## 6. 构建基础图谱记录

如果已经存在 `data/kg/extraction_results.jsonl`，图谱构建会优先使用 LLM 阶段式抽取结果，并保留投票和验证属性；否则会回退到清洗字段生成基础图谱：

```powershell
python -m src.kg_building.build_graph
```

输出：

```text
data/kg/entities.jsonl
data/kg/triples.jsonl
```

## 7. 导出 Neo4j CSV

推荐先运行知识融合，将 LLM 抽取中的同义实体、重复三元组统一为 canonical graph：

```powershell
python -m src.kg_fusion.run_fusion
```

融合层参考 graph-rag-agent 的实体处理思路，并按 24Model 做了约束化改造：

- 字符串召回：规范化名称、别名词典、包含关系、编辑距离。
- 向量重排：默认使用 `text-embedding-3-large`，综合分数为 `0.4 * string_score + 0.6 * vector_score`。
- NIL 检测：低于阈值时创建新的 canonical entity，不强行合并。
- 同类型合并：只允许同一 `label/entity_type` 内自动融合，避免跨 24Model 层级误合并。
- 关系融合：重写三元组端点，合并重复关系并计算 `weight`、`case_count`、`evidence_count`、`avg_confidence`、`vote_yes_ratio`。

输出：

```text
data/fusion/canonical_entities.jsonl
data/fusion/canonical_triples.jsonl
data/fusion/entity_alignment_map.jsonl
data/fusion/conflicts.jsonl
data/fusion/fusion_report.json
```

如需不调用 embedding API 进行快速检查：

```powershell
python -m src.kg_fusion.run_fusion --dry-run
```

导出 Neo4j CSV。若 `data/fusion/canonical_entities.jsonl` 和 `data/fusion/canonical_triples.jsonl` 已存在，默认优先导出融合后的 canonical graph：

```powershell
python -m src.kg_building.export_neo4j
```

仍可导出未融合的基础图谱：

```powershell
python -m src.kg_building.export_neo4j --raw
```

输出：

```text
data/neo4j/neo4j_nodes.csv
data/neo4j/neo4j_relationships.csv
```

## 8. 写入 Neo4j

先确认本地 Neo4j 已启动：

```powershell
python -m src.kg_building.check_neo4j
```

写入：

```powershell
python -m src.kg_building.write_neo4j
```

若融合结果已存在，默认写入融合后的 canonical graph：

```powershell
python -m src.kg_building.write_neo4j
```

如需写入未融合图谱，使用：

```powershell
python -m src.kg_building.write_neo4j --raw
```

如需清空后重写：

```powershell
python -m src.kg_building.write_neo4j --clear
```

## 9. 推荐运行顺序

完整实验可直接运行：

```powershell
python -m src.run_full_experiment
```

查看完整实验阶段进度：

```powershell
Get-Content data/experiment_progress.json
```

查看 LLM 抽取案例级进度：

```powershell
python -m src.llm_extraction.progress --input data/processed/anonymized_cases.jsonl
```

也可以按阶段手动运行：

```powershell
python -m src.data_cleaning.build_dataset
python -m src.privacy.anonymize_cases
python -m src.llm_extraction.extract --input data/processed/anonymized_cases.jsonl
python -m src.kg_building.build_graph
python -m src.kg_fusion.run_fusion
python -m src.causal_analysis.build_causal_dataset
python -m src.causal_analysis.run_batch_dowhy
python -m src.kg_building.export_neo4j
python -m src.kg_building.check_neo4j
python -m src.kg_building.write_neo4j
```

## 10. DoWhy因果推断分析

知识融合之后，可以将 canonical graph 转换为案例级因果变量矩阵，并基于 24Model 理论图运行 DoWhy 的建模、识别、估计和反驳检验：

```powershell
python -m src.causal_analysis.build_causal_dataset
python -m src.causal_analysis.run_dowhy --treatment 安全培训不足
python -m src.causal_analysis.run_batch_dowhy
```

默认 outcome 为 `severe_consequence`，表示事故是否出现死亡、重伤或显著损失。输出包括：

```text
data/causal/case_causal_matrix.csv
data/causal/causal_variable_map.json
data/causal/24model_causal_graph.dot
data/causal/dowhy_effect_results.jsonl
data/causal/dowhy_refutation_results.jsonl
data/causal/causal_analysis_report.md
```

批量分析默认选择高频 `SafetyManagementDefect`、`UnsafeAction`、`UnsafeObjectState` 作为 treatment。低样本或无变异变量会标记 `needs_review=true`，不会强行解释为可靠因果效应。

## 11. 说明

- `.docx` 文件使用 `python-docx` 读取。
- 旧版 `.doc` 文件通过 Windows Word COM 读取，需要本机安装 Microsoft Word。
- 关系和实体类别遵循 `ontology/24model_hydraulic_ontology_schema.json`。
- API key 不写入源码，请使用 `.env` 或环境变量配置。
