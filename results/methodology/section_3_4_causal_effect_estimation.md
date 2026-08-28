# 3.4 Causal-effect estimation

HEC-KG represents accident cases as evidence-grounded entities and relations, whereas statistical causal inference requires a case-level table with explicit treatments, outcomes, and adjustment variables. We therefore introduce a causal-analysis layer that projects the fused graph into an observational matrix and uses the causal ordering of 24Model to constrain effect identification. The analysis follows the model-identify-estimate-refute workflow implemented in DoWhy [3]. Its estimand is the effect of a selected accident factor on the probability of a severe consequence among the recorded accident cases. It does not estimate the probability that an accident occurs because the corpus contains accident reports rather than accident-free construction observations.

## 3.4.1 Causal variable matrix

Let \(G^{*}=(V^{*},E^{*})\) denote the canonical HEC-KG obtained after knowledge fusion, and let \(\mathcal{D}=\{d_i\}_{i=1}^{N}\) be the anonymized accident-case collection. Each canonical entity \(v\in V^{*}\) is linked to one or more cases through its `source_cases` property, case-specific relations, or a path propagated from an `AccidentCase` node. We project these case memberships onto a binary matrix

\[
\mathbf{X}=[x_{ik}]\in\{0,1\}^{N\times K},
\qquad
x_{ik}=\mathbb{I}\!\left(v_k\text{ is supported in case }d_i\right),
\tag{14}
\]

where \(K\) is the number of canonical features retained from the ontology types `SafetyCultureDefect`, `SafetyManagementDefect`, `SafetyCapabilityDefect`, `UnsafeAction`, `UnsafeObjectState`, `AccidentType`, `ConstructionActivity`, and `EnvironmentCondition`. A feature is marked as present only when its case provenance is retained by the fused entity or by a graph relation associated with that case. This projection preserves the link from a matrix cell to the canonical entity and, through the graph, to its source evidence.

Each entity-level feature receives a deterministic column identifier constructed from its ontology type and normalized canonical name. The implementation uses a type-specific prefix and the first ten characters of an MD5 digest of the type-name pair. The digest is used only to produce stable, machine-readable column names. The corresponding entity type, canonical name, entity identifier, and causal role are stored in `causal_variable_map.json`. Consequently, the statistical output can be traced back to a human-readable KG concept without relying on the encoded column name.

The entity-level matrix is augmented with a binary indicator and a count variable for each ontology layer. For layer \(\ell\), let \(\mathcal{K}_{\ell}\) be the set of feature columns assigned to that layer. We define

\[
L_{i\ell}=\mathbb{I}\!\left(\sum_{k\in\mathcal{K}_{\ell}}x_{ik}>0\right),
\qquad
C_{i\ell}=\sum_{k\in\mathcal{K}_{\ell}}x_{ik}.
\tag{15}
\]

\(L_{i\ell}\) indicates whether at least one factor from layer \(\ell\) occurs in case \(i\), whereas \(C_{i\ell}\) records the number of distinct factors from that layer. Layer indicators provide higher-support treatment candidates and summarize the overall presence of a 24Model factor family. Entity-level variables retain the resolution needed to estimate the effects of specific factors such as inadequate safety training or failure to use fall protection. Layer-level and entity-level treatments are analysed separately. A layer aggregate derived from the treatment's own factor family is not included as an adjustment variable.

The binary outcome \(Y_i\) denotes whether case \(i\) contains a severe consequence. It is initialized by deterministic matching over the consequence, economic-loss, and report-text fields using a fixed lexicon for fatalities, failed rescue, serious injury, major-accident classifications, and explicitly reported direct economic loss. The label is then updated from accepted `hasConsequence` relations in HEC-KG:

\[
Y_i=\mathbb{I}\!\left[
\operatorname{text}(d_i)\cap\mathcal{K}_{\mathrm{sev}}\neq\varnothing
\ \lor\ 
\exists e\in E^{*}_{i}:\operatorname{type}(e)=\texttt{hasConsequence}
\land\operatorname{sev}(e)=1
\right].
\tag{16}
\]

The resulting table contains case identifiers and provenance fields, the outcome, layer indicators, layer counts, and entity-level binary features. Accident type is retained as a descriptive matrix feature, but it is excluded from treatment-specific adjustment sets because an accident category may be determined by the direct accident mechanism and can therefore lie downstream of unsafe actions or unsafe object states.

## 3.4.2 Prior causal graph

Data-driven structure discovery is not used to determine causal direction. Instead, the sixth version of 24Model provides a prior directed acyclic graph \(G_{\mathrm{24}}=(V_{\mathrm{24}},E_{\mathrm{24}})\). Its core causal chain describes the propagation from organizational conditions to direct causes and severe consequences:

\[
\text{SCD}\rightarrow\text{SMD}\rightarrow\text{SCap}\rightarrow\text{UA}\rightarrow Y,
\qquad
\text{SMD}\rightarrow\text{UOS}\rightarrow Y,
\tag{17}
\]

where SCD, SMD, SCap, UA, and UOS denote safety-culture defects, safety-management defects, safety-capability defects, unsafe actions, and unsafe object states, respectively. Construction activity is allowed to affect both unsafe actions and unsafe object states, while environmental conditions may affect unsafe object states and the severity outcome. The complete set of eleven graph edges used by the implementation is listed in Table B11.

The prior graph serves two related purposes. First, it fixes the temporal and organizational order of the five 24Model factor layers. Second, it defines which measured variables are eligible as pre-treatment adjustment candidates for a selected treatment. Let \(o(\ell)\) denote the order of a causal layer, with \(o(\mathrm{SCD})=0\), \(o(\mathrm{SMD})=1\), \(o(\mathrm{SCap})=2\), and \(o(\mathrm{UA})=o(\mathrm{UOS})=3\). For treatment \(T\), the admissible candidate pool is

\[
\mathcal{P}_{T}=\left\{
Z_j:\ 
\ell(Z_j)\in\{\mathrm{Act},\mathrm{Env}\}
\ \lor\ 
o\!\left(\ell(Z_j)\right)<o\!\left(\ell(T)\right)
\right\},
\tag{18}
\]

subject to three exclusions: \(Z_j\neq T\), \(Z_j\) cannot belong to the treatment's own layer, and \(Z_j\) must not be a descendant of \(T\). Only variables with variation and adequate support in both exposed and unexposed cases are retained. The selected set \(\mathbf{Z}_T\) contains at most twelve variables, ordered by layer-level status and then by support. This rule prevents a treatment from being adjusted by its own aggregation variable or by a downstream mediator.

For each treatment, the implementation constructs a treatment-specific identification graph \(G_T\). It contains \(T\rightarrow Y\) and, for every \(Z_j\in\mathbf{Z}_T\), the edges \(Z_j\rightarrow T\) and \(Z_j\rightarrow Y\). The global 24Model graph therefore supplies the admissible causal order, while \(G_T\) makes the selected backdoor assumptions explicit for DoWhy. This separation is useful because the entity-level matrix may contain thousands of sparse factors, whereas each estimation problem requires a compact, treatment-specific adjustment set.

## 3.4.3 Causal identification, estimation, and reliability screening

The batch analysis considers safety-management defects, unsafe actions, and unsafe object states as treatment families because these factors are sufficiently close to operational intervention and accident severity to yield interpretable treatment definitions. Both layer-level indicators and entity-level factors are eligible. Candidates are ranked with layer indicators first and then by descending support. Under the experimental configuration, a treatment must occur in at least \(s_{\min}=20\) cases, at least 20 cases must remain in the comparison arm, and at most \(k_{\max}=20\) candidates are analysed.

Before estimation, each treatment is screened for empirical overlap. The procedure rejects a candidate when the treatment or outcome is constant, either treatment arm has insufficient support, or any cell in the \(2\times2\) treatment-outcome table is empty. These checks prevent estimation under complete separation and make the comparison between exposed and unexposed cases explicit. Upstream and contextual adjustment variables are subjected to the same minimum-support requirement. If no usable common cause remains, the numerical estimation may still be recorded, but it is marked `needs_review=true` and does not pass the causal-quality gate.

For an accepted treatment \(T\), DoWhy instantiates

\[
\mathcal{M}_T=\operatorname{CausalModel}
\left(\mathbf{X},T,Y,G_T\right)
\tag{19}
\]

and applies the backdoor criterion [4]. Under consistency, positivity, and conditional exchangeability given \(\mathbf{Z}_T\), the average treatment effect is identified as

\[
\tau_T=\mathbb{E}[Y\mid do(T=1)]-
\mathbb{E}[Y\mid do(T=0)]
=
\mathbb{E}_{\mathbf{Z}_T}
\left[
\mathbb{E}(Y\mid T=1,\mathbf{Z}_T)-
\mathbb{E}(Y\mid T=0,\mathbf{Z}_T)
\right].
\tag{20}
\]

The identified estimand is evaluated with DoWhy's `backdoor.linear_regression` estimator. The corresponding linear probability model is

\[
Y_i=\beta_0+\beta_TT_i+
\boldsymbol{\beta}_{Z}^{\top}\mathbf{Z}_{Ti}+\varepsilon_i,
\qquad
\widehat{\tau}_T=\widehat{\beta}_T.
\tag{21}
\]

Because \(Y\) is binary, \(\widehat{\tau}_T\) is interpreted as an adjusted difference in the probability of a severe consequence, measured in percentage points [5]. The implementation also reports the unadjusted risk difference, treated and comparison group sizes, outcome counts, and group-specific severe-consequence rates. These quantities distinguish the model-adjusted estimate from the raw difference observed in the accident corpus.

Uncertainty is quantified by case-level nonparametric bootstrap. With \(B=500\) and random seed 2026, cases are sampled with replacement, Eq. (21) is refitted whenever the resample retains variation in \(T\) and \(Y\), and the resulting estimates \(\{\widehat{\tau}^{(b)}_T\}_{b=1}^{B'}\) are collected. The reported interval and standard error are

\[
\operatorname{CI}_{95\%}(\widehat{\tau}_T)=
\left[
Q_{0.025}\!\left(\widehat{\tau}^{(b)}_T\right),
Q_{0.975}\!\left(\widehat{\tau}^{(b)}_T\right)
\right],
\qquad
\widehat{\operatorname{se}}_{\mathrm{boot}}=
\operatorname{sd}\!\left(\widehat{\tau}^{(b)}_T\right).
\tag{22}
\]

A two-sided normal-approximation \(p\)-value is computed from the bootstrap standard error and retained as an uncertainty diagnostic rather than as the sole acceptance criterion.

Two refutation procedures are then applied to each estimated effect [3]. The random-common-cause refuter adds an independently generated covariate and checks whether the estimate changes materially. The placebo-treatment refuter permutes the treatment assignment while preserving its marginal frequency. The resulting placebo effect should approach zero when the original estimate depends on the observed treatment-case correspondence. Exceptions or failed refutation records are preserved and marked for review. The final output for treatment \(T\) contains the identified estimand, selected adjustment set, adjusted effect, unadjusted risk difference, bootstrap interval, refutation records, and a machine-readable review status. This design supports causal interpretation under the stated 24Model graph and observed-variable assumptions while retaining all intermediate information needed to audit an estimate back to its source cases and canonical KG entities.

# Appendix B (continued). Reproducibility details for causal-effect estimation

The following tables continue the Appendix B numbering used for the extraction prompts and implementation settings. They summarize the causal-analysis code in `src/causal_analysis/` and the active parameters in `configs/settings.yaml`.

## B.10 Causal-variable encoding

**Table B10. Variables generated by `build_causal_dataset.py`.**

| Variable family | Ontology type or field | Encoding | Role in the causal analysis |
| --- | --- | --- | --- |
| Organizational factor | `SafetyCultureDefect` | Entity-level binary variable, layer indicator, and layer count | Eligible upstream adjustment variable |
| Organizational factor | `SafetyManagementDefect` | Entity-level binary variable, layer indicator, and layer count | Treatment candidate and upstream adjustment variable when temporally prior to another treatment |
| Individual capability | `SafetyCapabilityDefect` | Entity-level binary variable, layer indicator, and layer count | Upstream adjustment variable for unsafe-action treatments |
| Direct cause | `UnsafeAction` | Entity-level binary variable, layer indicator, and layer count | Treatment candidate |
| Direct cause | `UnsafeObjectState` | Entity-level binary variable, layer indicator, and layer count | Treatment candidate |
| Engineering context | `ConstructionActivity` | Entity-level binary variable, layer indicator, and layer count | Treatment-specific adjustment candidate |
| Engineering context | `EnvironmentCondition` | Entity-level binary variable, layer indicator, and layer count | Treatment-specific adjustment candidate |
| Accident descriptor | `AccidentType` | Entity-level binary variable, layer indicator, and layer count | Retained in the matrix; excluded from adjustment-set selection |
| Outcome | `severe_consequence` | Binary variable derived from the fixed severity lexicon and `hasConsequence` evidence | Outcome \(Y\) |
| Provenance | `case_id`, `title`, `source_file` | String fields | Case identity and audit trail |

The entity-level column convention is `x_<type-prefix>_<digest10>`. The digest is the first ten characters of the deterministic MD5 value produced from the entity type and normalized canonical name. The complete reverse mapping is stored in `causal_variable_map.json`.

## B.11 Prior causal graph

**Table B11. Directed edges written by `causal_graph.py` to `24model_causal_graph.dot`.**

| Source | Target | Methodological interpretation |
| --- | --- | --- |
| `SafetyCultureDefect` | `SafetyManagementDefect` | Safety culture shapes the management system |
| `SafetyManagementDefect` | `SafetyCapabilityDefect` | Management conditions influence individual safety capability |
| `SafetyManagementDefect` | `UnsafeObjectState` | Management deficiencies permit unsafe physical states |
| `SafetyCapabilityDefect` | `UnsafeAction` | Capability deficiencies contribute to unsafe actions |
| `UnsafeAction` | `severe_consequence` | Unsafe actions are direct antecedents of accident severity |
| `UnsafeObjectState` | `severe_consequence` | Unsafe object states are direct antecedents of accident severity |
| `ConstructionActivity` | `UnsafeAction` | Construction activity conditions opportunities for unsafe actions |
| `ConstructionActivity` | `UnsafeObjectState` | Construction activity conditions unsafe physical states |
| `EnvironmentCondition` | `UnsafeObjectState` | Environmental conditions influence unsafe object states |
| `EnvironmentCondition` | `severe_consequence` | Environmental conditions may directly influence severity |
| `AccidentType` | `severe_consequence` | Retained in the global descriptive DAG; not selected as a treatment-specific common cause |

## B.12 Active estimation settings

**Table B12. Reproducibility settings used by the causal-analysis pipeline.**

| Component | Code/configuration value | Function |
| --- | --- | --- |
| Causal framework | `dowhy.CausalModel` | Model construction, identification, estimation, and refutation |
| Outcome | `severe_consequence` | Binary severity outcome among recorded accidents |
| Batch treatment labels | `SafetyManagementDefect`, `UnsafeAction`, `UnsafeObjectState` | Eligible treatment families |
| Minimum treated-arm support | `causal.min_treatment_support = 20` | Excludes sparse treatments |
| Minimum comparison-arm support | 20, inherited from the same setting | Excludes near-universal treatments |
| Batch limit | `causal.batch_top_k = 20` | Maximum number of ranked treatment candidates |
| Maximum adjustment variables | 12 | Bounds the treatment-specific regression dimension |
| Adjustment controls | `ConstructionActivity`, `EnvironmentCondition` | Contextual pre-treatment candidates |
| Estimator | `backdoor.linear_regression` | Linear probability estimate of the adjusted risk difference |
| Significance request | `test_significance=True` | Requests estimator-level significance output from DoWhy |
| Bootstrap replicates | 500 | Percentile interval and bootstrap standard error |
| Bootstrap seed | 2026 | Reproducible case resampling |
| Refuters | `random_common_cause`; `placebo_treatment_refuter` | Sensitivity and falsification diagnostics |

## B.13 Quality filters and review status

**Table B13. Automatic quality filters implemented in `run_dowhy.py`.**

| Filter | Program condition | Recorded status |
| --- | --- | --- |
| Missing treatment or outcome | Required column is absent | `needs_review=true`; estimation skipped |
| Low treated-arm support | \(\sum_iT_i<s_{\min}\) | `low_support` |
| Low comparison-arm support | \(N-\sum_iT_i<s_{\min}\) | `low_control_support` |
| No variation | \(T\) or \(Y\) contains only one value | `treatment_has_no_variation` or `outcome_has_no_variation` |
| Empty contingency cell | At least one \(T\times Y\) cell equals zero | `separation_or_empty_cell` |
| Insufficient arm overlap | Treated or comparison arm is smaller than \(s_{\min}\) | `insufficient_overlap` |
| No usable common cause | Estimation completes with \(|\mathbf{Z}_T|=0\) | `causal_quality_pass=false`; `needs_review=true` |
| Missing DoWhy dependency | Import of `dowhy` fails | `dowhy_not_installed`; estimation skipped |
| Refuter exception | A refutation call raises an exception | Refutation record marked `needs_review=true` |

## B.14 Output artefacts

**Table B14. Files produced by the causal-analysis stage.**

| Output file | Producer | Reproducibility content |
| --- | --- | --- |
| `data/causal/case_causal_matrix.csv` | `build_causal_dataset.py` | Case-level outcome, layer indicators, layer counts, and entity-level binary features |
| `data/causal/causal_variable_map.json` | `build_causal_dataset.py` | Column name, ontology type, canonical name, entity ID, causal role, and layer-variable flag |
| `data/causal/24model_causal_graph.dot` | `causal_graph.py` | Eleven directed prior edges |
| `data/causal/dowhy_effect_results.jsonl` | `run_dowhy.py` / `run_batch_dowhy.py` | Treatment support, group risks, adjustment set, estimand, adjusted estimate, bootstrap uncertainty, graph, and review status |
| `data/causal/dowhy_refutation_results.jsonl` | `run_dowhy.py` | One record for each treatment-refuter pair, including returned diagnostics or exceptions |
| `data/causal/causal_analysis_report.md` | `run_batch_dowhy.py` | Human-readable batch summary of accepted, skipped, and review-flagged analyses |

The corresponding command sequence is:

```powershell
python -m src.causal_analysis.build_causal_dataset
python -m src.causal_analysis.run_batch_dowhy
```

## B.15 Deterministic severity labeling

**Table B15. Fixed lexicon used by `is_severe_consequence`.**

| Code token | English interpretation | Fields searched |
| --- | --- | --- |
| `死亡` | Fatality | Consequence text, economic-loss text, full report text, and consequence-relation evidence |
| `抢救无效` | Death after unsuccessful rescue | Same as above |
| `重伤` | Serious injury | Same as above |
| `较大事故` | Larger accident classification | Same as above |
| `重大事故` | Major accident classification | Same as above |
| `特别重大事故` | Particularly major accident classification | Same as above |
| `直接经济损失` | Explicitly reported direct economic loss | Same as above |
