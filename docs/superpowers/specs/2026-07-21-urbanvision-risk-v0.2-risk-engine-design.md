# UrbanVision-Risk v0.2 Risk Engine Design / 风险引擎设计

**Date / 日期:** 2026-07-21  
**Status / 状态:** Conversational design approved; written review requested / 对话设计已批准，等待书面复核  
**Depends on / 依赖:** UrbanVision-Risk v0.1 prediction JSON schema

## 1. Objective / 目标

Version 0.2 converts the structured road-damage detections produced by v0.1 into an explainable maintenance-priority score. It scores each image from 0 to 100, assigns a bilingual priority level, explains every class contribution, and ranks a complete prediction batch.

v0.2 把 v0.1 生成的结构化道路缺陷检测结果转换成可解释的维护优先级分数。系统为每张图片计算 0–100 分，给出中英双语优先级、逐类别贡献解释，并对整批预测结果排序。

The score is an educational and research prototype for prioritizing human review. It is not a certified engineering safety assessment and must never be presented as proof that a road is safe or unsafe.

该分数是用于安排人工复检顺序的学习与研究原型，不是经过认证的工程安全鉴定，也不得被表述为道路安全或不安全的证明。

## 2. Decisions Already Approved / 已批准决策

- Purpose: explainable maintenance-priority prototype / 用途：可解释的维护优先级原型。
- Scope: per-image scoring plus batch ranking and summary / 范围：单图评分，加整批排序与汇总。
- Method: transparent rule model with configuration stored in YAML / 方法：参数保存在 YAML 中的透明规则模型。
- Confidence: evidence quality only; it does not change physical-priority score / 置信度：只表示证据质量，不改变物理缺陷优先级分数。
- Runtime: fully local, deterministic, and independent of YOLO inference / 运行：完全本地、确定性执行，并与 YOLO 推理解耦。
- Safety: existing prediction artifacts and risk results are immutable and never silently overwritten / 安全：已有预测和风险结果不可变，绝不静默覆盖。

## 3. Non-Goals / 非目标

v0.2 does not add:

- real-world crack length, depth, width, or pothole volume;
- camera calibration or conversion from pixels to physical units;
- traffic volume, road class, GPS, time series, route aggregation, or weather;
- Web UI, GIS, local LLM reporting, or model retraining;
- automatic traffic control, road closure, or certified maintenance decisions;
- an empirical claim that the default weights are calibrated to an engineering standard.

v0.2 不增加：

- 真实裂缝长度、深度、宽度或坑洞体积；
- 相机标定或像素到物理单位的换算；
- 交通量、道路等级、GPS、时间序列、路线聚合或天气数据；
- Web UI、GIS、本地 LLM 报告或模型重训；
- 自动交通管制、道路封闭或认证养护决策；
- 默认权重已经按工程规范完成校准的经验性结论。

## 4. Architecture and Responsibilities / 架构与职责

```text
v0.1 prediction JSON
        ↓
batch discovery and complete input validation
整批发现与完整输入验证
        ↓
geometry: clipped rectangles and per-class union area
几何层：边界裁剪与逐类别联合面积
        ↓
transparent per-class scoring
透明逐类别评分
        ↓
per-image bilingual risk records
单图双语风险记录
        ↓
deterministic batch ranking and summary
确定性批量排序与汇总
```

The risk engine never imports or calls Ultralytics. It consumes existing JSON, so configuration changes can be rescored without training or inference.

风险引擎不导入也不调用 Ultralytics，只消费已有 JSON，因此修改配置后无需重新训练或推理即可重新评分。

### 4.1 Proposed modules / 计划模块

| File / 文件 | Responsibility / 职责 |
|---|---|
| `configs/risk-v0.2.yaml` | Auditable defaults, formula version, thresholds, recommendations / 可审计默认值、公式版本、阈值和建议 |
| `src/urbanvision_risk/risk/config.py` | Load and validate risk configuration / 加载并验证风险配置 |
| `src/urbanvision_risk/risk/geometry.py` | Validate, clip, and calculate rectangle union area / 验证、裁剪并计算矩形联合面积 |
| `src/urbanvision_risk/risk/score.py` | Score one prediction payload without filesystem access / 对单个预测载荷评分，不访问文件系统 |
| `src/urbanvision_risk/risk/assess.py` | Batch discovery, validation, ranking, durable output, and CLI / 批量发现、验证、排序、持久输出和命令行 |
| `src/urbanvision_risk/paths.py` | Add the `results/risks` project path / 增加 `results/risks` 路径 |

Each module has one responsibility. Geometry does not assign engineering meaning; scoring does not read files; batch orchestration does not implement the formula.

每个模块只承担一种职责：几何层不赋予工程含义，评分层不读取文件，批处理层不实现评分公式。

## 5. Command-Line Interface / 命令行接口

```bash
uv run python -m urbanvision_risk.risk.assess \
  --run-name china-baseline-001 \
  --prediction-name prediction-001 \
  --output-name risk-001
```

Optional arguments:

- `--config PATH`: use another risk configuration; defaults to `configs/risk-v0.2.yaml`.
- `--debug`: re-raise project errors with a traceback.

可选参数：

- `--config PATH`：使用另一份风险配置；默认是 `configs/risk-v0.2.yaml`。
- `--debug`：重新抛出项目错误并显示调用栈。

Run names use the existing safe-name validator. The command resolves input from `results/predictions/<run-name>/<prediction-name>` and writes below `results/risks`.

运行名沿用已有安全名称验证器。命令从 `results/predictions/<run-name>/<prediction-name>` 解析输入，并写入 `results/risks`。

## 6. Input Contract / 输入契约

The batch input is every `*.json` file immediately inside one v0.1 prediction directory, sorted by filename. Annotated JPG files are ignored. Subdirectories are not traversed.

批量输入是一个 v0.1 预测目录直属的全部 `*.json` 文件，并按文件名排序。带框 JPG 被忽略，也不递归读取子目录。

Every JSON must contain:

- `source_image`: non-empty string;
- `model_checkpoint`: non-empty string;
- `confidence_threshold`: finite number from 0 to 1;
- `image_dimensions.width` and `.height`: positive integers;
- `detections`: list;
- `counts`: exact integer totals for D00, D10, D20, and D40.

Every detection must contain:

- `class_id`: integer 0–3;
- `code`: matching D00, D10, D20, or D40;
- `name_en` and `name_zh`: the canonical v0.1 names;
- `confidence`: finite number from 0 to 1;
- `bbox_xyxy`: four finite numbers with `xmax > xmin` and `ymax > ymin`.

The `counts` object must exactly match detections grouped by code. Unknown class codes or contradictory fields fail validation rather than being guessed. Optional v0.1 bilingual empty-result messages are allowed.

`counts` 必须与按类别汇总的检测列表完全一致。未知类别代码或互相矛盾的字段直接验证失败，不进行猜测性修复；v0.1 的可选中英文空结果说明字段可以保留。

### 6.1 Coordinate tolerance / 坐标容差

The default coordinate tolerance is 1 pixel. A coordinate no more than 1 pixel beyond an image boundary is clamped for area calculation and recorded in `audit_flags`. A box entirely outside the image, or any coordinate more than 1 pixel outside the valid range, is rejected.

默认坐标容差是 1 像素。坐标越界不超过 1 像素时，在面积计算中裁剪到图片边界，并记录到 `audit_flags`；边界框完全位于图片外，或任一坐标越界超过 1 像素时拒绝输入。

## 7. Geometry / 几何计算

For each class, the engine computes the exact union area of its clipped axis-aligned rectangles. It uses an x-axis sweep across unique rectangle boundaries and merges y-intervals within every x strip. Overlap therefore contributes area once, while the original detection count remains visible and auditable.

系统对每个类别的裁剪后轴对齐矩形计算精确联合面积：沿唯一 x 边界扫描，并在每个 x 区间内合并 y 区间。因此重叠区域只计算一次，同时保留原始检测数量以供审计。

```text
coverage_ratio = class_union_area / (image_width × image_height)
```

Coverage is a two-dimensional image proxy, not a physical road-area measurement.

覆盖率只是二维图片代理量，不是真实道路面积。

## 8. Scoring Formula / 评分公式

### 8.1 Default parameters / 默认参数

```yaml
formula_version: "risk-v0.2.0"
count_cap: 5
reference_coverage: 0.05
count_mix: 0.35
coverage_mix: 0.65
class_max_points:
  D00: 15
  D10: 20
  D20: 25
  D40: 40
risk_thresholds:
  moderate: 20
  high: 40
  critical: 70
evidence_thresholds:
  moderate: 0.50
  high: 0.75
coordinate_tolerance_pixels: 1
```

Constraints:

- all maximum points are positive and total exactly 100;
- `count_cap` is a positive integer;
- `reference_coverage` is in `(0, 1]`;
- `count_mix` and `coverage_mix` are non-negative and total exactly 1;
- risk and evidence thresholds are strictly increasing and within their valid ranges;
- coordinate tolerance is finite and non-negative.

约束：类别最大分值都为正且总和正好为 100；数量上限为正整数；参考覆盖率位于 `(0, 1]`；数量与覆盖率混合权重非负且总和正好为 1；风险和证据阈值严格递增且位于合法范围；坐标容差有限且非负。

### 8.2 Per-class contribution / 逐类别贡献

For class `c`:

```text
count_factor(c) = min(count(c) / count_cap, 1)

coverage_factor(c) =
    min(sqrt(coverage_ratio(c) / reference_coverage), 1)

class_score(c) =
    class_max_points(c)
    × [count_mix × count_factor(c)
       + coverage_mix × coverage_factor(c)]
```

An absent class contributes zero. The square root allows small visible defects to contribute while limiting domination by one large rectangle.

不存在的类别贡献为零。平方根让小型可见缺陷仍产生贡献，同时限制单个大框完全支配结果。

### 8.3 Image score and levels / 图片分数与等级

```text
risk_score = round(min(100, sum(class_score)), 1)
```

| Range / 区间 | Level / 等级 | Maintenance recommendation / 维护建议 |
|---|---|---|
| `0 <= score < 20` | `low` / 低 | Routine review; no urgent priority detected / 常规复核；未检测到紧急优先项 |
| `20 <= score < 40` | `moderate` / 中 | Schedule a manual review / 安排人工复检 |
| `40 <= score < 70` | `high` / 高 | Prioritize manual inspection / 优先人工检查 |
| `70 <= score <= 100` | `critical` / 严重 | Urgent manual inspection; a human decides any control action / 紧急人工检查；任何管制措施由人工决定 |

A zero score means no maintenance-priority item was detected at the prediction threshold. It never means that the road is proven safe.

零分表示在预测阈值下未检测到维护优先项，绝不表示道路已被证明安全。

## 9. Evidence Quality / 证据质量

Prediction confidence is reported separately and never appears in the risk-score formula.

预测置信度单独报告，永不进入风险评分公式。

For non-empty detections:

```text
mean_confidence = arithmetic mean of detection confidence
minimum_confidence = minimum detection confidence
```

Default evidence labels:

- `low`: `mean_confidence < 0.50`;
- `moderate`: `0.50 <= mean_confidence < 0.75`;
- `high`: `mean_confidence >= 0.75`.

An empty detection list uses `not_applicable` with null mean and minimum confidence. `low` evidence adds a bilingual `low_confidence_evidence` review flag but does not lower or raise the risk score.

空检测列表的证据等级是 `not_applicable`，平均和最低置信度为 null。低证据质量增加中英双语 `low_confidence_evidence` 人工复核标志，但不提高或降低风险分数。

## 10. Durable Outputs / 持久输出

```text
results/risks/
└── <run-name>/
    └── <prediction-name>/
        └── <output-name>/
            ├── per-image/
            │   └── <source-stem>-risk.json
            ├── risk-summary.json
            ├── ranking.csv
            └── risk-config-resolved.yaml
```

The output directory is created only after every input file and the configuration pass validation. An existing output directory raises the existing non-overwrite error `E204`.

只有全部输入文件和配置通过验证后才创建输出目录。已有输出目录触发现有的禁止覆盖错误 `E204`。

### 10.1 Per-image risk JSON / 单图风险 JSON

Each record contains:

- source prediction path and SHA-256;
- source image and model checkpoint copied from prediction metadata;
- formula version and resolved-config SHA-256;
- risk score, level, and bilingual recommendation;
- class-by-class count, union coverage ratio, factors, maximum points, and contribution;
- mean confidence, minimum confidence, evidence quality, and audit flags;
- a bilingual limitation stating that human engineering review is required.

### 10.2 Ranking CSV / 排名 CSV

Rows sort by descending risk score, then ascending source filename. Columns include rank, source filename, score, level, evidence quality, confidence statistics, four class counts, four coverage ratios, and four class contributions.

数据行先按风险分数降序，再按源文件名升序。列包含排名、源文件名、分数、等级、证据质量、置信度统计、四类数量、四类覆盖率和四类贡献分。

### 10.3 Batch summary / 批量摘要

`risk-summary.json` contains:

- UTC creation time;
- source directory, file count, ordered aggregate input digest, and config digest;
- formula version;
- score minimum, mean, median, and maximum;
- counts by risk level and evidence quality;
- total detections by class;
- the ten highest-priority images, or every image when the batch has fewer than ten.

`risk-config-resolved.yaml` is the exact validated configuration used for the run.

## 11. Error Handling / 错误处理

All learner-facing failures use `ProjectError` and bilingual recovery instructions.

| Code / 错误码 | Meaning / 含义 | Recovery / 恢复方法 |
|---|---|---|
| `E201` | Prediction directory or config path is missing / 预测目录或配置路径不存在 | Check run, prediction, and config names / 检查运行、预测和配置名称 |
| `E204` | Risk output already exists / 风险输出已存在 | Keep it and choose a new output name / 保留结果并使用新输出名 |
| `E401` | Risk configuration is invalid / 风险配置非法 | Inspect the named field and restore valid constraints / 检查指定字段并恢复合法约束 |
| `E402` | Prediction JSON is malformed or incomplete / 预测 JSON 损坏或不完整 | Inspect or regenerate the named prediction JSON / 检查或重新生成指定预测 JSON |
| `E403` | Detection geometry or statistics are contradictory / 检测几何或统计互相矛盾 | Inspect bbox, dimensions, class identity, and counts / 检查边界框、尺寸、类别和计数 |

The command validates all inputs before creating outputs. If an operating-system write error occurs afterward, the incomplete directory is preserved for inspection and is never deleted automatically.

命令在创建输出前验证全部输入。若随后发生操作系统写入错误，不完整目录会保留以供检查，绝不自动删除。

## 12. Determinism and Provenance / 确定性与来源记录

- Files are discovered and processed in sorted relative-path order.
- JSON uses stable key ordering and UTF-8 with a trailing newline.
- CSV uses a fixed column order and UTF-8.
- Equal scores are ordered by source filename.
- Each source JSON has a SHA-256; the batch digest hashes ordered relative paths and file digests.
- The resolved configuration and its digest are stored with every run.
- Changing only confidence values may change evidence fields but cannot change risk score.

- 文件按相对路径排序后发现并处理；
- JSON 使用稳定键顺序、UTF-8 和末尾换行；
- CSV 使用固定列顺序和 UTF-8；
- 相同分数按源文件名排序；
- 每个源 JSON 保存 SHA-256，批次摘要对有序相对路径和文件摘要再次计算摘要；
- 每次运行保存解析后配置及其摘要；
- 只修改置信度可以改变证据字段，但不能改变风险分数。

## 13. Testing Strategy / 测试策略

### Unit tests / 单元测试

- rectangle-union area for disjoint, overlapping, nested, touching, and empty rectangles;
- coordinate tolerance, clipping audit flags, and invalid boxes;
- config constraints and level boundaries;
- monotonic count and coverage factors, score cap, and one-decimal rounding;
- confidence independence from risk score;
- empty detection behavior and safety wording;
- stable bilingual recommendations.

### Integration tests / 集成测试

- valid prediction directory produces per-image JSON, summary, resolved config, and CSV;
- malformed JSON, unknown class, mismatched count, and empty directory fail before output creation;
- existing output directory is preserved and rejected;
- ranking is deterministic and uses the fixed tie-break;
- rerunning the same inputs under a new output name produces identical scores and digests except creation time and output path.

### Learner acceptance / 学习者验收

Run the real command against `china-baseline-001/prediction-001`. The expected batch contains 198 per-image risk files plus the summary, ranking CSV, and resolved configuration. Interpret the highest-ranked examples manually and state clearly that the output is a prioritization prototype.

对 `china-baseline-001/prediction-001` 运行真实命令。预期生成 198 份单图风险文件，以及摘要、排名 CSV 和解析后配置。人工解释排名最高的样本，并明确输出只是优先级原型。

## 14. Acceptance Criteria / 验收标准

v0.2 is accepted when:

1. all v0.1 tests still pass;
2. every new unit and integration test passes without network access;
3. scores remain in 0–100 and are reproducible from stored inputs and config;
4. confidence-only changes do not change a risk score;
5. existing predictions and risk outputs are not modified or overwritten;
6. the 198-image real batch completes locally and writes the complete artifact set;
7. documentation explains formula, limitations, errors, and the learner command in Chinese and English;
8. no output claims certified safety, automatic closure, or engineering-standard calibration.

v0.2 只有在以下条件全部满足时才验收：v0.1 测试无回归；新测试离线通过；分数位于 0–100 且可复现；只改变置信度不改变风险分数；已有产物不被修改或覆盖；198 张真实批次在本地完成；中英双语文档完整；任何输出都不宣称认证安全、自动封路或已按工程规范校准。

## 15. Future Calibration / 后续校准

The YAML boundary is intentional. A future independent milestone may replace heuristic defaults with values calibrated from engineer-labeled severity, camera scale, road type, traffic exposure, or longitudinal observations. That future work must retain the current formula version and output provenance so old experiments remain reproducible.

YAML 配置边界是有意设计的。未来独立里程碑可以使用工程师严重度标签、相机尺度、道路类型、交通暴露或长期观测来校准默认值；未来工作必须保留当前公式版本和输出来源记录，让旧实验继续可复现。
