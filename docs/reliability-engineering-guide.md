# UrbanVision-Risk v2.0 Reliability Engineering / 可靠性工程

## Why this version exists / 为什么要做这一版

**English:** A single detector pass cannot distinguish a stable observation from an accidental high-confidence prediction. v2.0 treats inference as evidence collection: the same image is observed under controlled resolution and symmetry transformations, then detections must agree before they can affect maintenance priority.

**中文：** 单次检测无法区分稳定证据和偶然高置信度预测。v2.0 把推理重新定义为“证据收集”：同一图片在受控分辨率与对称变换下被多次观察，检测结果必须形成共识后才可影响维护优先级。

## Three independent views / 三个独立视图

| View / 视图 | Purpose / 目的 |
|---|---|
| `native-640` | Preserve the production detector's normal receptive field / 保留常规检测感受野 |
| `native-1280` | Recover thin or small defects weakened by resampling / 恢复重采样中被削弱的细小缺陷 |
| `hflip-1280` | Test invariance to horizontal symmetry / 检查水平对称不变性 |

All three passes use the same checkpoint. The lower candidate floor is not a decision threshold: it only retains proposals for disagreement analysis. A detection still needs one observation above the configured decision confidence and support from at least two views.

三次推理使用同一检查点。较低候选门槛不是最终判定门槛，只用于保留提案并分析分歧；检测簇仍需要至少一个观察达到正式置信度门槛，并得到至少两个视图支持。

## Association and fusion / 关联与融合

Candidates are first deduplicated inside each view using class-aware non-maximum suppression. Across views, two boxes may join one cluster only when their class is identical, the view has not already contributed to that cluster, and IoU is at least `0.45`.

每个视图先使用分类感知非极大值抑制去重。跨视图聚类时，只有类别相同、该视图尚未加入此簇且 IoU 至少为 `0.45` 的检测框才可关联。

For observations with confidence `cᵢ` and box coordinate `bᵢ`, the fused coordinate is:

```text
b_fused = Σ(cᵢ × bᵢ) / Σcᵢ
```

The final confidence is the arithmetic mean across supporting views. This is deliberately more conservative than selecting the maximum confidence.

最终置信度使用支持视图的算术平均值，刻意不采用最乐观的最大置信度。

## Reliability metrics / 可靠性指标

```text
support_ratio = supporting_views / total_views
localization_agreement = mean IoU(observed_box, fused_box)
stability = sqrt(support_ratio × localization_agreement)
uncertainty = 1 - (0.65 × stability + 0.35 × mean_confidence)
```

An accepted cluster is still routed to human review when localization stability is below `0.60`. A high-confidence cluster supported by only one view is marked `disputed_single_view` and does not enter risk scoring.

即使检测簇被接受，定位稳定性低于 `0.60` 时仍会进入人工复核。只有一个视图支持的高置信度簇标记为 `disputed_single_view`，不会进入风险评分。

## Active-learning queue / 主动学习队列

For accepted clusters with mean uncertainty `Ū` and disputed-cluster ratio `D`, the ranking score is:

```text
active_learning_priority = 100 × (0.70 × Ū + 0.30 × D)
```

The queue is generated from immutable local inspection artifacts, sorted deterministically, and never contains absolute filesystem paths. Inspect it while the app is running:

```bash
curl "http://127.0.0.1:8000/api/review-queue?limit=20"
```

This creates a real human-in-the-loop loop: review the highest-value failures, label them, add them to a versioned dataset, retrain, and compare the new held-out metrics and reliability distribution.

这形成真正的人机闭环：人工检查最高价值失败样本，完成标注并加入版本化数据集，再训练后比较新的留出集指标和可靠性分布。

## Audit artifacts / 审计文件

Every inspection writes `reliability.json` alongside `prediction.json` and `risk.json`. It records all view IDs, every consensus cluster, support, confidence dispersion, localization agreement, stability, uncertainty, disposition, and active-learning priority. Its SHA-256 digest is stored in `inspection-manifest.json`.

每次巡检都会在 `prediction.json` 与 `risk.json` 旁保存 `reliability.json`，记录全部视图、共识簇、支持度、置信度离散、定位一致性、稳定性、不确定性、处理结论和主动学习优先级；其 SHA-256 写入 `inspection-manifest.json`。

## Honest limitations / 诚实边界

- Transform consensus measures repeatability, not correctness. Consistently wrong predictions can still agree.
- The current RDD2022 taxonomy does not contain every structural pavement-failure mode.
- Bounding-box coverage is not a physical crack-width, depth, or structural-capacity measurement.
- The maintenance score is not a certified engineering safety assessment.

- 变换共识衡量可重复性，而不是绝对正确性；稳定的错误仍可能形成共识。
- 当前 RDD2022 类别体系不包含所有路面结构性失效模式。
- 检测框覆盖率不等于裂缝宽度、深度或结构承载能力。
- 维护优先级不能替代认证工程安全鉴定。

## Technical references / 技术参考

- [RDD2022 official challenge repository](https://github.com/sekilab/RoadDamageDetector)
- [Multiple Instance Active Learning for Object Detection](https://arxiv.org/abs/2104.02324)
- [Learning an Uncertainty-Aware Object Detector for Autonomous Driving](https://arxiv.org/abs/1910.11375)
