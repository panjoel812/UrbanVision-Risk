# UrbanVision-Risk

**中文：** 面向城市基础设施智能巡检与风险评估的端侧 AI 项目。v0.1 在 Apple Silicon Mac 上完成 RDD2022 道路缺陷数据准备、YOLO26n 微调、真实评估和图片预测。

**English:** An on-device AI project for urban-infrastructure inspection and risk assessment. Version 0.1 prepares RDD2022 road-damage data, fine-tunes YOLO26n, evaluates real held-out metrics, and predicts locally on Apple Silicon.

## v0.1 Scope / v0.1 范围

- Four classes / 四类缺陷: D00 longitudinal crack / 纵向裂缝, D10 transverse crack / 横向裂缝, D20 alligator crack / 网状裂缝, D40 pothole / 坑洞.
- Fully local after one-time dependency, data, and model downloads / 完成一次性依赖、数据和模型下载后可完全本地运行。
- No paid API or cloud runtime / 不使用付费 API 或云端运行环境。
- No Web UI, risk engine, LLM, GIS, or multi-country research claim in v0.1 / v0.1 不包含 Web、风险引擎、LLM、GIS 或多国科研结论。

## Safety / 安全说明

The project uses uv-managed Python 3.11 and never replaces macOS `/usr/bin/python3`. Raw data is immutable. Commands never permanently delete data or silently overwrite experiments.

项目使用 uv 管理的 Python 3.11，不替换 macOS `/usr/bin/python3`。原始数据不可变，命令不永久删除数据，也不静默覆盖实验。

## Learner Workflow / 学习者流程

Run one command at a time. Return the complete terminal output for explanation before continuing.

一次只运行一条命令。继续之前，把完整终端输出发回以便解释。

```bash
uv python install 3.11
uv sync --extra dev
uv run python -m urbanvision_risk.environment
uv run pytest
uv run python -m urbanvision_risk.data.download
uv run python -m urbanvision_risk.data.prepare
uv run python -m urbanvision_risk.data.validate
uv run python -m urbanvision_risk.detection.train --profile smoke --run-name smoke-test-001
uv run python -m urbanvision_risk.detection.train --profile baseline --run-name china-baseline-001
uv run python -m urbanvision_risk.detection.evaluate --run-name china-baseline-001
uv run python -m urbanvision_risk.detection.predict --run-name china-baseline-001 --source data/processed/rdd2022-china-motorbike/images/test
```

## Generated Artifacts / 生成物

- `data/processed/rdd2022-china-motorbike/manifest.json`: data lineage and counts / 数据来源与统计。
- `results/experiments/<run>/weights/best.pt`: best checkpoint / 最佳模型。
- `results/evaluations/<run>/evaluation.json`: held-out metrics / 留出集指标。
- `results/predictions/<run>/<output>/`: annotated JPG and JSON / 带框图片与 JSON。

## Learning Guide / 学习指南

Read [`docs/learning-guide.md`](docs/learning-guide.md) for bilingual explanations of Python environments, labels, splits, training, metrics, MPS, and experiment interpretation.

阅读 [`docs/learning-guide.md`](docs/learning-guide.md)，了解 Python 环境、标签、数据划分、训练、指标、MPS 和实验解读。

## Data and Citation / 数据与引用

RDD2022 is downloaded from its maintainers and is not redistributed here: <https://github.com/sekilab/RoadDamageDetector>. Cite the dataset article: <https://arxiv.org/abs/2209.08538>.

RDD2022 从维护者来源下载，本仓库不重新分发。使用数据时请引用上述资料。

## License / 许可

Repository code is licensed under `AGPL-3.0-or-later`. Ultralytics licensing must be reviewed again before any closed-source commercial use.

仓库代码采用 `AGPL-3.0-or-later`。任何闭源商业使用前必须重新审查 Ultralytics 许可。
