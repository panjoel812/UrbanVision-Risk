# UrbanVision-Risk v0.2 Risk Engine / 风险引擎指南

## What it does / 它做什么

**English:** v0.2 reads the JSON files produced by v0.1 and ranks images for human maintenance review. It does not run YOLO again, use the network, or call a cloud API.

**中文：** v0.2 读取 v0.1 已生成的 JSON，把图片按人工维护复核优先级排序。它不会再次运行 YOLO，不访问网络，也不调用云 API。

## Run one batch / 运行一批数据

From the repository root / 从仓库根目录运行：

```bash
uv run python -m urbanvision_risk.risk.assess --run-name china-baseline-001 --prediction-name prediction-001 --output-name risk-001
```

The command first validates all 198 prediction JSON files. It creates output only after every input passes. Existing output is never overwritten.

命令会先验证全部 198 个预测 JSON。只有所有输入都通过后才创建输出；已有输出绝不覆盖。

## Formula / 公式

For each class D00, D10, D20, and D40 / 分别对 D00、D10、D20、D40 计算：

```text
count_factor = min(count / 5, 1)
coverage_factor = min(sqrt(coverage_ratio / 0.05), 1)
class_score = class_max_points × (0.35 × count_factor + 0.65 × coverage_factor)
risk_score = round(min(100, sum(class_score)), 1)
```

Class maximum points are D00=15, D10=20, D20=25, and D40=40. `coverage_ratio` uses the exact union of same-class boxes, so overlapping pixels are counted once.

类别最高分是 D00=15、D10=20、D20=25、D40=40。`coverage_ratio` 使用同类检测框的精确并集，所以重叠像素只计算一次。

Risk levels / 风险等级：low `[0,20)`、moderate `[20,40)`、high `[40,70)`、critical `[70,100]`。

## Default settings / 默认设置

| Setting / 设置 | Default / 默认值 | Meaning / 含义 |
|---|---:|---|
| Formula version / 公式版本 | `risk-v0.2.0` | Identifies this fixed scoring rule / 标识这套固定评分规则。 |
| `count_cap` / 数量上限 | `5` | Counts above five do not increase that class factor / 同类数量超过五个后不再提高该类别因子。 |
| `reference_coverage` / 参考覆盖率 | `0.05` | Coverage ratio that reaches the coverage-factor cap / 使覆盖因子达到上限的覆盖率。 |
| `count_mix / coverage_mix` / 数量与覆盖权重 | `0.35 / 0.65` | Mixes count and coverage factors in every class score / 在每个类别分数中混合数量与覆盖因子。 |
| Class maximum points / 类别最高分 | `D00=15, D10=20, D20=25, D40=40` / `D00=15、D10=20、D20=25、D40=40` | Per-class contribution caps / 各类别贡献上限。 |
| Risk thresholds / 风险阈值 | `20 / 40 / 70` | Moderate, high, and critical start points / 中等、高、严重等级的起始分数。 |
| Evidence thresholds / 证据阈值 | `0.50 / 0.75` | Moderate and high mean-confidence start points / 中等和高证据质量的平均置信度起点。 |
| `coordinate_tolerance_pixels` / 坐标容差像素 | `1` | A box may extend at most 1 pixel outside the image before validation rejects it / 检测框最多可超出图像边界 1 个像素，超过则验证失败。 |

## Confidence is separate / 置信度单独处理

Detection confidence describes evidence quality; confidence never changes risk_score. Every non-empty result reports the mean and minimum detection confidence. Evidence bands use the mean: low `[0,0.50)`, moderate `[0.50,0.75)`, and high `[0.75,1]`. Low mean confidence adds the `low_confidence_evidence` audit flag. No detections means evidence quality is `not_applicable`, with both confidence values set to `null`.

检测置信度描述证据质量；置信度绝不改变 risk_score。每个非空结果都会报告平均和最低检测置信度。证据质量按平均值划分：低 `[0,0.50)`、中等 `[0.50,0.75)`、高 `[0.75,1]`；低平均置信度会增加 `low_confidence_evidence` 审计标记。没有检测结果时证据质量为 `not_applicable`，两个置信度值均为 `null`。

This separation is important: a model can be confident about a small defect, or uncertain about a large one. Human review should see both facts.

这种分离很重要：模型可能对一个小缺陷很自信，也可能对一个大缺陷不确定。人工复核需要同时看到两种信息。

## Output files / 输出文件

`results/risks/china-baseline-001/prediction-001/risk-001/` contains / 包含：

- `per-image/*-risk.json`: score, class contributions, provenance hashes, evidence, flags, and bilingual recommendation / 分数、类别贡献、来源哈希、证据、审计标记和双语建议；
- `ranking.csv`: descending score order, mean/minimum confidence, and filename as deterministic tie-breaker / 按分数降序，包含平均/最低置信度，同分时按文件名稳定排序；
- `risk-summary.json`: batch digest, statistics, counts, and top ten / 批次摘要哈希、统计、计数和前十名；
- `risk-config-resolved.yaml`: the exact validated settings used / 本次实际使用且验证过的完整配置。

## Error recovery / 错误恢复

| Code | English | 中文 |
|---|---|---|
| E201 | Prediction directory or config is missing; check names and paths. | 预测目录或配置不存在；检查名称和路径。 |
| E204 | Output exists; keep it and choose a new output name. | 输出已存在；保留它并换一个输出名。 |
| E401 | Configuration violates a formula constraint. | 配置违反公式约束。 |
| E402 | JSON is malformed, incomplete, or the directory is empty. | JSON 损坏、不完整，或目录为空。 |
| E403 | Geometry, class metadata, or counts contradict each other. | 几何、类别信息或计数互相矛盾。 |
| E404 | A write failed. Inspect and fix disk space, the parent path, or permissions; preserve the partial directory if it was created, then retry with a new unused output name. | 写入失败。检查并修复磁盘空间、父级路径或权限；如果已创建不完整目录，请保留它供检查，然后使用新的未使用的输出名重试。 |

Never manually change v0.1 prediction JSON to make an error disappear. For E201–E403, follow the named input or configuration correction; E404 is a write-environment problem, so use its disk-space, parent-path, permission, and new-output-name recovery steps.

不要为了消除错误而手工修改 v0.1 预测 JSON。对 E201–E403，请修复错误中指出的输入或配置；E404 是写入环境问题，请按其磁盘空间、父级路径、权限和新输出名的恢复步骤处理。

## Safety boundary / 安全边界

This heuristic maintenance-priority score does not replace a certified engineering safety assessment. A score of zero means only that this model detected no current maintenance priority; it does not mean the road is safe. The prototype has no physical scale, GPS, traffic exposure, pavement history, or calibrated engineering severity labels. A human engineer decides inspection, closure, and repair actions.

此启发式维护优先级分数不能替代经过认证的工程安全鉴定。零分只表示本模型当前未检测到维护优先项，不代表道路安全。原型没有物理尺度、GPS、交通暴露、路面历史或经过标定的工程严重度标签。检查、封闭和维修措施必须由人类工程人员决定。
