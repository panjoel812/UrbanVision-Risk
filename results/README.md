# Results / 结果

- `experiments/`: training logs, `best.pt`, `last.pt`, `results.csv`, and `training_summary.json` / 训练日志、权重、表格与训练摘要。
- `evaluations/`: held-out metrics and confusion-matrix plots / 留出集指标和混淆矩阵。
- `predictions/`: annotated JPG files and matching JSON / 带框 JPG 与匹配 JSON。
- `risks/`: explainable per-image maintenance priorities, deterministic ranking CSV, batch summary, and resolved configuration / 可解释单图维护优先级、确定性排序 CSV、批次摘要和实际配置。
- `reports/`: fully offline bilingual HTML dashboards and provenance manifests / 完全离线的双语 HTML 仪表板和来源清单。
- `inspections/`: immutable v1.1 single-image source, full/tiled inference metadata, annotation, prediction, risk, and provenance artifacts / 不可覆盖的 v1.1 单图原图、全图/分块推理元数据、标注、预测、风险和来源文件。

Every run name is unique. Existing results are never silently overwritten.

每个运行名称唯一；已有结果绝不被静默覆盖。
