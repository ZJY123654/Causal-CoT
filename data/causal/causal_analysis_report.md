# DoWhy causal analysis report

This report is generated from the fused 24Model knowledge graph. Estimates are exploratory and depend on the encoded accident-case matrix.

- Cases: 456
- Outcome: `severe_consequence`
- Severe cases: 423
- Minimum treatment support: 20
- Selected treatments: 20

| Treatment | Label | Support | Treated severe rate | Control severe rate | Unadjusted RD | Adjusted estimate | 95% CI | Common causes | Needs review | Skip reason |
|---|---|---:|---:|---:|---:|---:|---|---:|---|---|
| 存在安全管理体系缺陷 | SafetyManagementDefect | 449 | 0.9265 | 1.0000 | -0.0735 |  |  | 6 | True | low_control_support:7<min_support:20 |
| 存在物的不安全状态 | UnsafeObjectState | 440 | 0.9273 | 0.9375 | -0.0102 |  |  | 12 | True | low_control_support:16<min_support:20 |
| 存在人的不安全动作 | UnsafeAction | 409 | 0.9389 | 0.8298 | 0.1091 | 0.1060 | [-0.0279, 0.2580] | 12 | False |  |
| 隐患排查治理 | SafetyManagementDefect | 304 | 0.9375 | 0.9079 | 0.0296 | 0.0336 | [-0.0213, 0.0839] | 6 | False |  |
| 监督检查 | SafetyManagementDefect | 156 | 0.9423 | 0.9200 | 0.0223 | 0.0292 | [-0.0181, 0.0765] | 6 | False |  |
| 隐患整改不闭环 | SafetyManagementDefect | 102 | 0.9216 | 0.9294 | -0.0078 | 0.0012 | [-0.0652, 0.0594] | 6 | False |  |
| 安全责任未落实 | SafetyManagementDefect | 101 | 0.9109 | 0.9324 | -0.0215 | -0.0148 | [-0.0784, 0.0445] | 6 | False |  |
| 安全培训不足 | SafetyManagementDefect | 60 | 0.9833 | 0.9192 | 0.0641 | 0.0625 | [0.0140, 0.1095] | 6 | False |  |
| 安全知识教育不足 | SafetyManagementDefect | 53 | 0.9811 | 0.9206 | 0.0605 | 0.0602 | [0.0080, 0.1024] | 6 | False |  |
| 作业人员不了解风险和控制措施 | SafetyManagementDefect | 53 | 0.9811 | 0.9206 | 0.0605 | 0.0527 | [0.0075, 0.0948] | 6 | False |  |
| 未按地质水文条件调整方案 | SafetyManagementDefect | 48 | 0.9375 | 0.9265 | 0.0110 | 0.0183 | [-0.0587, 0.0923] | 6 | False |  |
| 未识别危险源 | SafetyManagementDefect | 43 | 0.9535 | 0.9249 | 0.0285 | 0.0209 | [-0.0532, 0.0806] | 6 | False |  |
| 职责不清 | SafetyManagementDefect | 40 | 0.9250 | 0.9279 | -0.0029 | 0.0020 | [-0.0892, 0.0808] | 6 | False |  |
| 交叉作业协调不足 | SafetyManagementDefect | 38 | 0.9211 | 0.9282 | -0.0072 | -0.0209 | [-0.1154, 0.0612] | 6 | False |  |
| 专项安全技术交底不足 | SafetyManagementDefect | 37 | 0.9459 | 0.9260 | 0.0199 | 0.0187 | [-0.0777, 0.0883] | 6 | False |  |
| 职工安全知识教育不足 | SafetyManagementDefect | 23 | 0.9565 | 0.9261 | 0.0304 | 0.0676 | [-0.0323, 0.1680] | 6 | False |  |
| 安全监督检查不力 | SafetyManagementDefect | 21 | 1.0000 | 0.9241 | 0.0759 |  |  | 6 | True | separation_or_empty_cell:[21, 0, 402, 33] |
| 未系安全带 | UnsafeAction | 21 | 0.9048 | 0.9287 | -0.0240 | -0.0204 | [-0.1674, 0.0935] | 12 | False |  |
| 方案未落实 | SafetyManagementDefect | 20 | 0.8500 | 0.9312 | -0.0812 | -0.0866 | [-0.2551, 0.0606] | 6 | False |  |
| 专项施工方案 | SafetyManagementDefect | 20 | 1.0000 | 0.9243 | 0.0757 |  |  | 6 | True | separation_or_empty_cell:[20, 0, 403, 33] |
