# 基于事故致因24Model的水利工程施工事故本体构建方案

## 1. 构建思路

本文借鉴“Automated knowledge graph-based risk assessment for fall-from-height accidents in construction”一文的本体构建方法，即先选定事故致因理论模型，再将理论模型转化为实体类别、关系类型和属性字段，最后服务于大型语言模型（LLM）的自动化知识抽取与知识图谱构建。不同之处在于，原文以改造后的 AcciMap 作为高处坠落事故知识图谱的理论基础，而本文以事故致因“2-4”模型（24Model）第6版作为水利工程施工事故知识图谱的上层致因框架。

24Model 第6版将事故致因因素划分为组织因素和个体因素两大类。其中，组织因素包括安全文化和安全管理体系，个体因素包括人的安全能力和人和物的安全动作。基于该结构，水利工程施工事故本体应同时表达事故案例的基本事实、水利工程施工领域对象、事故致因链条、事故过程、事故后果与防控措施。

本体构建遵循以下逻辑：

```text
安全文化缺陷
  -> 安全管理体系缺陷
  -> 人的安全能力缺陷
  -> 人的不安全动作 / 物的不安全状态
  -> 事故过程
  -> 事故后果
```

在水利工程施工场景中，上述链条需要进一步连接施工活动、工程对象、设备设施和环境条件。例如，围堰施工中的高水位、导流方案缺陷、排水设施不足、现场巡查不到位和作业人员违规操作，均可嵌入24Model的致因层级中。

## 2. 实体类设计

表1给出了水利工程施工事故本体的核心实体类。实体类分为事故事实类、领域对象类、24Model致因类、事故演化类和防控措施类。

**表1 水利工程施工事故本体实体类**

| 序号 | 实体类 | 标签 | 所属层级 | 含义 | 示例 |
|---:|---|---|---|---|---|
| 1 | `AccidentCase` | 事故案例 | 事故事实 | 具体事故调查报告或事故记录 | 某水库除险加固工程坍塌事故 |
| 2 | `AccidentType` | 事故类型 | 事故事实 | 事故类别 | 坍塌、涌水、滑坡、起重伤害、机械伤害、高处坠落、触电、爆破事故 |
| 3 | `ConstructionActivity` | 施工活动 | 领域对象 | 事故发生时对应的施工工序或作业活动 | 围堰施工、基坑开挖、隧洞掘进、边坡支护、混凝土浇筑、吊装作业 |
| 4 | `EngineeringObject` | 工程对象 | 领域对象 | 事故涉及的水利工程结构、临时结构或作业部位 | 围堰、基坑、边坡、隧洞、闸室、大坝、脚手架、模板支撑体系 |
| 5 | `EnvironmentCondition` | 环境条件 | 领域对象 | 与事故相关的自然、水文、地质或施工环境因素 | 强降雨、高水位、复杂地质、软弱夹层、地下水丰富、夜间施工 |
| 6 | `EquipmentFacility` | 设备设施 | 领域对象 | 事故涉及的机械设备、防护设施、临时设施或监测设备 | 起重机械、挖掘机、排水设备、支护结构、防护栏杆、监测仪器 |
| 7 | `UnsafeAction` | 人的不安全动作 | 24Model-直接层 | 作业人员、管理人员或相关人员实施的不安全行为 | 违章指挥、冒险作业、未佩戴防护用品、擅自拆除支护 |
| 8 | `UnsafeObjectState` | 物的不安全状态 | 24Model-直接层 | 设备、设施、材料、结构或环境处于不安全状态 | 支护不足、围堰渗漏、边坡失稳、设备带病运行、防护缺失 |
| 9 | `SafetyCapabilityDefect` | 人的安全能力缺陷 | 24Model-个体因素 | 个体在安全知识、意识、习惯、心理或生理方面的缺陷 | 安全知识不足、风险意识薄弱、侥幸心理、疲劳作业、习惯性违章 |
| 10 | `SafetyManagementDefect` | 安全管理体系缺陷 | 24Model-组织因素 | 制度、责任、培训、监督、风险管控、隐患排查、应急管理等缺陷 | 安全培训不足、专项方案缺失、隐患排查不到位、监测预警缺失 |
| 11 | `SafetyCultureDefect` | 安全文化缺陷 | 24Model-组织因素 | 组织安全理念、价值观、态度和安全优先意识方面的深层缺陷 | 重进度轻安全、安全投入不足、安全责任意识淡薄 |
| 12 | `AccidentProcess` | 事故过程 | 事故演化 | 事故从风险因素触发到后果形成的事件链节点 | 围堰渗漏扩大、基坑涌水、边坡滑移、人员坠落 |
| 13 | `Consequence` | 事故后果 | 事故结果 | 事故造成的损失或影响 | 死亡、受伤、经济损失、工程损毁、工期延误 |
| 14 | `PreventiveMeasure` | 防控措施 | 风险治理 | 用于预防、控制或减轻事故风险的措施 | 加强监测预警、完善支护方案、开展安全培训、落实旁站监督 |

## 3. 属性设计

属性用于补充事故案例、实体和关系的上下文信息。基础属性主要挂接到 `AccidentCase`，领域属性挂接到相应实体类，证据属性用于支持 LLM 抽取结果的可追溯性。

**表2 水利工程施工事故本体属性**

| 属性名 | 适用实体 | 数据类型 | 含义 | 示例 |
|---|---|---|---|---|
| `case_id` | `AccidentCase` | String | 事故案例编号 | HCA-2026-001 |
| `report_title` | `AccidentCase` | String | 事故报告名称 | 某水利枢纽工程围堰坍塌事故调查报告 |
| `accident_date` | `AccidentCase` | Date | 事故发生日期 | 2024-06-18 |
| `location` | `AccidentCase` | String | 事故发生地点 | 湖北省某市某水库工程 |
| `project_type` | `AccidentCase` | String | 工程类型 | 水库工程、堤防工程、引调水工程、水电站工程 |
| `construction_stage` | `AccidentCase` / `ConstructionActivity` | String | 施工阶段 | 主体施工、导流施工、基础处理、除险加固 |
| `severity_level` | `AccidentCase` | String | 事故等级 | 一般事故、较大事故、重大事故、特别重大事故 |
| `death_toll` | `Consequence` | Integer | 死亡人数 | 3 |
| `injury_count` | `Consequence` | Integer | 受伤人数 | 5 |
| `economic_loss` | `Consequence` | Float | 直接经济损失 | 6500000 |
| `evidence_text` | 全部实体/关系 | String | 支持抽取结果的原文证据 | “现场未按专项方案设置排水设施” |
| `source_report` | 全部实体/关系 | String | 来源报告 | 某事故调查报告PDF |
| `confidence` | 全部实体/关系 | Float | LLM抽取置信度或人工确认置信度 | 0.86 |
| `normalized_name` | 风险因素类实体 | String | 聚类融合后的标准名称 | 安全培训不足 |
| `model_layer` | 24Model致因实体 | String | 所属24Model层级 | 安全管理体系、人的安全能力 |

## 4. 关系类型设计

关系类型用于表达事故事实、领域对象关联和24Model致因链条。借鉴原论文中 Cause、Trigger、Lead_to 等关系思想，本文根据24Model重构为“事实关系、直接致因关系、深层致因关系、演化关系和治理关系”五类。

**表3 水利工程施工事故本体关系类型**

| 序号 | 关系名 | 起点实体 | 终点实体 | 关系含义 | 示例 |
|---:|---|---|---|---|---|
| 1 | `hasAccidentType` | `AccidentCase` | `AccidentType` | 事故案例属于某类事故 | 某事故 -> 坍塌事故 |
| 2 | `occursInActivity` | `AccidentCase` | `ConstructionActivity` | 事故发生于某施工活动 | 某事故 -> 基坑开挖 |
| 3 | `involvesObject` | `AccidentCase` | `EngineeringObject` | 事故涉及某工程对象 | 某事故 -> 围堰 |
| 4 | `involvesEquipment` | `AccidentCase` | `EquipmentFacility` | 事故涉及某设备或设施 | 某事故 -> 排水设备 |
| 5 | `hasEnvironmentCondition` | `AccidentCase` | `EnvironmentCondition` | 事故发生时存在某环境条件 | 某事故 -> 强降雨 |
| 6 | `hasDirectCause` | `AccidentCase` | `UnsafeAction` / `UnsafeObjectState` | 事故具有直接原因 | 某事故 -> 未按方案支护 |
| 7 | `hasCapabilityCause` | `UnsafeAction` | `SafetyCapabilityDefect` | 人的不安全动作源于安全能力缺陷 | 冒险作业 -> 风险意识薄弱 |
| 8 | `hasManagementCause` | `UnsafeAction` / `UnsafeObjectState` / `SafetyCapabilityDefect` | `SafetyManagementDefect` | 直接原因或能力缺陷源于管理体系缺陷 | 支护不足 -> 专项方案审查不到位 |
| 9 | `hasCultureCause` | `SafetyManagementDefect` | `SafetyCultureDefect` | 管理体系缺陷源于安全文化缺陷 | 安全投入不足 -> 重进度轻安全 |
| 10 | `leadTo` | `AccidentProcess` / `UnsafeObjectState` / `UnsafeAction` | `AccidentProcess` / `Consequence` | 某因素或过程导致后续状态或后果 | 基坑涌水 -> 边坡失稳 |
| 11 | `controlledBy` | `UnsafeAction` / `UnsafeObjectState` / `SafetyCapabilityDefect` / `SafetyManagementDefect` | `PreventiveMeasure` | 风险因素可由某措施控制 | 支护不足 -> 完善支护方案 |
| 12 | `hasConsequence` | `AccidentCase` | `Consequence` | 事故造成某后果 | 某事故 -> 3人死亡 |

## 5. 本体约束规则

为保证LLM自动抽取结果稳定、可解释和可入库，本体应设置以下约束。

**表4 本体约束规则**

| 编号 | 约束类型 | 规则内容 |
|---:|---|---|
| R1 | 层级约束 | `SafetyCultureDefect`、`SafetyManagementDefect`、`SafetyCapabilityDefect`、`UnsafeAction`、`UnsafeObjectState` 必须映射到24Model层级。 |
| R2 | 直接原因约束 | `hasDirectCause` 的终点只能是 `UnsafeAction` 或 `UnsafeObjectState`。 |
| R3 | 管理原因约束 | `hasManagementCause` 的终点只能是 `SafetyManagementDefect`。 |
| R4 | 文化原因约束 | `hasCultureCause` 的起点应为 `SafetyManagementDefect`，终点应为 `SafetyCultureDefect`。 |
| R5 | 事故事实约束 | 每个 `AccidentCase` 至少应包含事故类型、发生地点、施工活动和事故后果之一。 |
| R6 | 证据约束 | 每个LLM抽取实体和关系均应保留 `evidence_text`，用于人工复核。 |
| R7 | 标准化约束 | 同义或近义风险因素应合并为统一的 `normalized_name`。 |
| R8 | 不确定性约束 | 无法从原文直接支持的实体或关系不得入库，或标记为 `needs_review=true`。 |
| R9 | 因果方向约束 | 致因关系应从深层原因指向浅层原因或事故结果；若使用追溯查询，可在图数据库中反向遍历。 |
| R10 | 领域边界约束 | 水利施工特有对象和活动应优先归入 `ConstructionActivity`、`EngineeringObject`、`EnvironmentCondition` 或 `EquipmentFacility`，不得误归为24Model致因类。 |

## 6. LLM自动抽取流程

借鉴原论文的分步抽取策略，不建议让LLM一次性输出完整知识图谱。本文将抽取任务拆分为基础信息抽取、领域实体抽取、24Model致因实体抽取、关系判断和实体融合五个阶段。

### 6.1 阶段一：基础信息抽取

目标是从事故报告中抽取事故案例的基本事实。

**输出JSON模板**

```json
{
  "case_id": "",
  "report_title": "",
  "accident_date": "",
  "location": "",
  "project_type": "",
  "construction_stage": "",
  "accident_type": "",
  "consequence": {
    "death_toll": null,
    "injury_count": null,
    "economic_loss": null,
    "description": ""
  },
  "evidence_text": ""
}
```

**提示词模板**

```text
你是一名水利工程施工安全事故分析专家。请从以下事故调查报告文本中抽取事故基础信息。
只抽取原文中明确出现或可以直接确定的信息，不要推测。
请按照给定JSON格式输出，并为每个重要字段保留原文证据。

事故报告文本：
{accident_report_text}

输出字段：
case_id, report_title, accident_date, location, project_type, construction_stage,
accident_type, consequence, evidence_text。
```

### 6.2 阶段二：水利施工领域实体抽取

目标是抽取施工活动、工程对象、环境条件和设备设施。

**输出JSON模板**

```json
{
  "construction_activities": [
    {"name": "", "evidence_text": ""}
  ],
  "engineering_objects": [
    {"name": "", "evidence_text": ""}
  ],
  "environment_conditions": [
    {"name": "", "evidence_text": ""}
  ],
  "equipment_facilities": [
    {"name": "", "evidence_text": ""}
  ]
}
```

**提示词模板**

```text
请从事故报告中抽取水利工程施工领域实体，并分为四类：
1. ConstructionActivity：施工活动或作业工序；
2. EngineeringObject：工程对象、结构物、临时结构或作业部位；
3. EnvironmentCondition：自然、水文、地质、气象或现场环境条件；
4. EquipmentFacility：机械设备、防护设施、临时设施、监测设备。

注意：
- 不要把管理缺陷、人的行为或事故后果归入本步骤。
- 每个实体必须提供原文证据。
- 输出JSON。

事故报告文本：
{accident_report_text}
```

### 6.3 阶段三：24Model致因实体抽取

目标是按照24Model第6版抽取事故致因实体。

**输出JSON模板**

```json
{
  "unsafe_actions": [
    {"name": "", "actor": "", "evidence_text": ""}
  ],
  "unsafe_object_states": [
    {"name": "", "object": "", "evidence_text": ""}
  ],
  "safety_capability_defects": [
    {"name": "", "subtype": "", "evidence_text": ""}
  ],
  "safety_management_defects": [
    {"name": "", "subtype": "", "evidence_text": ""}
  ],
  "safety_culture_defects": [
    {"name": "", "subtype": "", "evidence_text": ""}
  ]
}
```

**24Model分类说明**

| 类别 | 子类建议 | 判别标准 |
|---|---|---|
| `UnsafeAction` | 违章操作、违章指挥、冒险作业、防护用品使用不当、未按方案施工 | 原文描述了人的具体动作或行为 |
| `UnsafeObjectState` | 结构失稳、设备故障、防护缺失、材料缺陷、环境危险状态 | 原文描述了物、设备、结构或环境处于危险状态 |
| `SafetyCapabilityDefect` | 安全知识不足、安全意识薄弱、安全习惯不良、安全心理异常、生理状态不佳 | 原文描述了个体能力、认知、心理、生理或习惯问题 |
| `SafetyManagementDefect` | 制度缺陷、责任不落实、培训不足、监督检查不到位、隐患排查不到位、应急管理不足 | 原文描述了组织管理体系运行缺陷 |
| `SafetyCultureDefect` | 重生产轻安全、安全价值观偏差、安全投入不足、安全责任意识淡薄 | 原文反映组织深层安全理念或价值取向问题 |

**提示词模板**

```text
你是一名熟悉事故致因24Model第6版的安全科学研究者。
请依据24Model从事故报告中抽取致因实体，并严格分为以下五类：
1. UnsafeAction：人的不安全动作；
2. UnsafeObjectState：物的不安全状态；
3. SafetyCapabilityDefect：人的安全能力缺陷；
4. SafetyManagementDefect：安全管理体系缺陷；
5. SafetyCultureDefect：安全文化缺陷。

分类要求：
- 具体人的行为归入 UnsafeAction。
- 设备、结构、设施、环境的危险状态归入 UnsafeObjectState。
- 知识、意识、习惯、心理、生理问题归入 SafetyCapabilityDefect。
- 制度、培训、监督、隐患排查、责任落实、应急管理问题归入 SafetyManagementDefect。
- 安全理念、价值观、安全优先意识、安全投入倾向等深层组织问题归入 SafetyCultureDefect。
- 每个实体必须给出原文证据，不得凭常识补充。

事故报告文本：
{accident_report_text}

请输出JSON。
```

### 6.4 阶段四：关系抽取

关系抽取不采用一次性生成全部三元组的方式，而采用“候选实体对 + 问题判断”的方式，以降低幻觉和错误连接。

**关系判断问题模板**

| 关系 | 判断问题 | 输出 |
|---|---|---|
| `hasDirectCause` | 实体A是否是事故案例B的直接原因？ | Yes/No + evidence |
| `hasCapabilityCause` | 安全能力缺陷A是否导致或解释了不安全动作B？ | Yes/No + evidence |
| `hasManagementCause` | 管理体系缺陷A是否导致或解释了实体B？ | Yes/No + evidence |
| `hasCultureCause` | 安全文化缺陷A是否导致或解释了管理体系缺陷B？ | Yes/No + evidence |
| `leadTo` | 实体A是否在事故演化过程中导致实体B？ | Yes/No + evidence |
| `controlledBy` | 防控措施A是否能够控制或预防风险因素B？ | Yes/No + evidence |

**输出JSON模板**

```json
{
  "triples": [
    {
      "subject": "",
      "subject_type": "",
      "predicate": "",
      "object": "",
      "object_type": "",
      "evidence_text": "",
      "confidence": null,
      "needs_review": false
    }
  ]
}
```

**提示词模板**

```text
你是一名水利工程施工事故知识图谱构建专家。
请判断候选实体对之间是否存在指定关系。
只能依据事故报告原文判断，不允许根据常识臆测。

事故报告文本：
{accident_report_text}

候选实体对：
主体：{subject}，类型：{subject_type}
客体：{object}，类型：{object_type}
候选关系：{predicate}

请回答：
1. 是否存在该关系：Yes 或 No；
2. 若存在，请给出原文证据；
3. 输出JSON。
```

### 6.5 阶段五：实体标准化与知识融合

事故报告中常出现同义或近义表达。为避免知识图谱节点冗余，需要进行实体标准化。

**表5 同义实体融合示例**

| 原始表达 | 标准化名称 | 实体类型 |
|---|---|---|
| 安全教育不到位、未开展安全培训、培训不足、三级教育流于形式 | 安全培训不足 | `SafetyManagementDefect` |
| 未按方案施工、违反专项施工方案、擅自改变施工工艺 | 未按专项方案施工 | `UnsafeAction` |
| 支护不到位、支护结构缺失、支撑体系不完善 | 支护措施不足 | `UnsafeObjectState` |
| 排水设施不足、未设置有效排水、抽排水能力不足 | 排水措施不足 | `UnsafeObjectState` |
| 重进度轻安全、抢工期忽视安全、安全优先意识不足 | 重进度轻安全 | `SafetyCultureDefect` |

推荐流程：

```text
原始实体
  -> 文本向量化
  -> 层级聚类或人工辅助聚类
  -> 标准名称命名
  -> 替换图谱中的原始节点
  -> 形成加权风险因素网络
```

## 7. 知识图谱三元组模式

本体最终服务于水利工程施工事故知识图谱。三元组可采用如下模式：

```text
<AccidentCase, hasAccidentType, AccidentType>
<AccidentCase, occursInActivity, ConstructionActivity>
<AccidentCase, involvesObject, EngineeringObject>
<AccidentCase, involvesEquipment, EquipmentFacility>
<AccidentCase, hasEnvironmentCondition, EnvironmentCondition>
<AccidentCase, hasDirectCause, UnsafeAction>
<AccidentCase, hasDirectCause, UnsafeObjectState>
<UnsafeAction, hasCapabilityCause, SafetyCapabilityDefect>
<UnsafeAction, hasManagementCause, SafetyManagementDefect>
<UnsafeObjectState, hasManagementCause, SafetyManagementDefect>
<SafetyCapabilityDefect, hasManagementCause, SafetyManagementDefect>
<SafetyManagementDefect, hasCultureCause, SafetyCultureDefect>
<UnsafeAction, leadTo, AccidentProcess>
<UnsafeObjectState, leadTo, AccidentProcess>
<AccidentProcess, leadTo, Consequence>
<RiskFactor, controlledBy, PreventiveMeasure>
```

示例：

```text
<某围堰坍塌事故, hasAccidentType, 坍塌事故>
<某围堰坍塌事故, occursInActivity, 围堰施工>
<某围堰坍塌事故, involvesObject, 围堰>
<某围堰坍塌事故, hasEnvironmentCondition, 高水位>
<某围堰坍塌事故, hasDirectCause, 围堰渗漏未及时处置>
<围堰渗漏未及时处置, hasCapabilityCause, 风险意识薄弱>
<围堰渗漏未及时处置, hasManagementCause, 巡查制度落实不到位>
<巡查制度落实不到位, hasCultureCause, 重进度轻安全>
<围堰渗漏扩大, leadTo, 围堰坍塌>
<围堰坍塌, leadTo, 人员伤亡>
<围堰渗漏风险, controlledBy, 加强围堰监测预警>
```

## 8. 验证与评价方案

本体构建完成后，应通过抽取准确性、本体覆盖性和图谱可用性三个方面进行评价。

**表6 验证与评价指标**

| 评价维度 | 指标 | 方法 |
|---|---|---|
| 实体抽取准确性 | Precision、Recall、F1 | 选取30-50篇水利工程施工事故报告，由专家标注标准答案，与LLM抽取结果比较 |
| 关系抽取准确性 | Precision | 对候选关系进行人工复核，统计正确关系占比 |
| 标注一致性 | Fleiss' Kappa | 多名专家独立标注同一批样本，计算一致性 |
| 本体覆盖性 | 类别覆盖率 | 检查是否覆盖主要事故类型、施工活动、工程对象和24Model致因层级 |
| 致因链完整性 | 链条完整率 | 检查是否能形成“安全文化-管理体系-安全能力-不安全动作/状态-事故后果”的链条 |
| 图谱可用性 | 查询任务完成率 | 测试高频原因查询、深层原因追溯、关键风险因素识别等任务 |
| 风险分析能力 | 中心性、出入度、边权 | 对融合后的风险因素网络进行拓扑分析 |

建议设置以下查询任务检验图谱实用性：

```text
1. 查询坍塌事故中出现频率最高的直接原因。
2. 查询涌水事故中最常见的管理体系缺陷。
3. 查询与“安全培训不足”相关的事故类型和施工活动。
4. 追溯某一事故从不安全状态到安全文化缺陷的完整链条。
5. 识别水利工程施工事故知识图谱中出度最高的风险因素。
```

## 9. 论文方法章节表述建议

可在论文中表述为：

> 本研究以事故致因“2-4”模型（24Model）第6版作为水利工程施工事故知识图谱的上层本体框架。该模型将事故致因因素划分为组织因素和个体因素两大类，其中组织因素包括安全文化和安全管理体系，个体因素包括人的安全能力和人和物的安全动作。为适配水利工程施工事故场景，本文在24Model基础上扩展施工活动、工程对象、设备设施、环境条件、事故过程、事故后果和防控措施等领域实体，构建面向LLM自动抽取的水利工程施工事故本体模型。该本体既保留24Model对事故深层致因链条的解释能力，又增强了其对水利工程施工专业语义的表达能力。

> 在知识抽取方面，本文借鉴自动化知识图谱构建研究中的分步提示策略，将抽取任务拆解为基础信息抽取、领域实体识别、24Model致因实体识别、关系判断和实体标准化五个阶段。通过实体类型约束、关系方向约束和原文证据约束，降低LLM在事故致因抽取中的幻觉风险，提高知识图谱构建结果的可解释性和可复核性。

## 10. 后续实现建议

初始阶段建议优先完成论文表格版本体和小样本验证。随后可按以下路线扩展：

```text
论文表格版本体
  -> JSON Schema抽取模板
  -> Neo4j节点/关系模式
  -> LLM批量抽取程序
  -> 实体聚类融合
  -> 加权风险因素网络
  -> 风险评估与可视化分析
```

如果进入Neo4j实现阶段，建议将 `AccidentCase`、`AccidentType`、`ConstructionActivity`、`EngineeringObject`、`UnsafeAction`、`UnsafeObjectState`、`SafetyCapabilityDefect`、`SafetyManagementDefect`、`SafetyCultureDefect` 设为核心节点标签，将本文表3中的关系类型设为图数据库关系。
