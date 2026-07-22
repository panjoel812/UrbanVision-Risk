# UrbanVision-Risk

**中文：** 面向城市基础设施智能巡检与风险评估的端侧 AI 系统。v1.1 在完全本地闭环上增加高清重叠分块推理、历史修补区域观察类，以及“零检测必须人工复核”的安全保护，避免把模型漏检误写成低风险。

**English:** An on-device AI system for urban-infrastructure inspection and risk assessment. Version 1.1 adds overlapping high-resolution inference, an auxiliary observation for previously repaired areas, and a zero-detection human-review safeguard so model misses are never presented as low risk.

## v1.1 Quick Start / v1.1 快速启动

```bash
uv sync --extra dev
uv run python -m urbanvision_risk.app.serve --run-name china-repair-mps-003
```

Open `http://127.0.0.1:8000` and upload one JPEG, PNG, or WebP road image. Press `Control+C` in the terminal to stop. The app binds only to the local loopback interface and makes no cloud or paid-API call.

打开 `http://127.0.0.1:8000`，上传一张 JPEG、PNG 或 WebP 道路图片。回到终端按 `Control+C` 停止。应用只监听本机回环地址，不调用云服务或付费 API。

## v0.1 Scope / v0.1 范围

- Four classes / 四类缺陷: D00 longitudinal crack / 纵向裂缝, D10 transverse crack / 横向裂缝, D20 alligator crack / 网状裂缝, D40 pothole / 坑洞.
- Auxiliary observation / 辅助观察: Repair previously repaired area / 历史修补区域；它不参与缺陷风险计分。
- Fully local after one-time dependency, data, and model downloads / 完成一次性依赖、数据和模型下载后可完全本地运行。
- No paid API or cloud runtime / 不使用付费 API 或云端运行环境。
- No Web UI, risk engine, LLM, GIS, or multi-country research claim in v0.1 / v0.1 不包含 Web、风险引擎、LLM、GIS 或多国科研结论。

## Safety / 安全说明

The project uses uv-managed Python 3.11 and never replaces macOS `/usr/bin/python3`. Raw data is immutable. Commands never permanently delete data or silently overwrite experiments.

项目使用 uv 管理的 Python 3.11，不替换 macOS `/usr/bin/python3`。原始数据不可变，命令不永久删除数据，也不静默覆盖实验。

## Reproduction Workflow / 完整复现实验

The commands below reproduce the project from environment setup through the final app. Code, tests, and documentation are completed as one batch; these commands are retained for learning and independent reproduction.

以下命令用于从环境准备完整复现到最终应用。代码、测试和文档采用整批完成方式；保留这些命令是为了学习和独立复现实验。

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
uv run python -m urbanvision_risk.detection.train --profile repair --run-name china-repair-mps-003
uv run python -m urbanvision_risk.detection.evaluate --run-name china-baseline-001
uv run python -m urbanvision_risk.detection.predict --run-name china-repair-mps-003 --source data/processed/rdd2022-china-motorbike-repair-v1.1/images/test

# v0.2: score an existing prediction batch; this does not rerun YOLO
uv run python -m urbanvision_risk.risk.assess --run-name china-baseline-001 --prediction-name prediction-001 --output-name risk-001

# v0.3: build an offline bilingual dashboard; this does not need a server
uv run python -m urbanvision_risk.reporting.build --run-name china-baseline-001 --prediction-name prediction-001 --risk-name risk-001 --output-name report-001

# v1.1: full-image + overlapping tiled inference with a zero-detection safeguard
uv run python -m urbanvision_risk.app.serve --run-name china-repair-mps-003
```

## Generated Artifacts / 生成物

- `data/processed/rdd2022-china-motorbike/manifest.json`: data lineage and counts / 数据来源与统计。
- `data/processed/rdd2022-china-motorbike-repair-v1.1/manifest.json`: five-class v1.1 data lineage, including the auxiliary Repair observation / v1.1 五类数据来源，包含 Repair 辅助观察。
- `results/experiments/<run>/weights/best.pt`: best checkpoint / 最佳模型。
- `results/evaluations/<run>/evaluation.json`: held-out metrics / 留出集指标。
- `results/predictions/<run>/<output>/`: annotated JPG and JSON / 带框图片与 JSON。
- `results/risks/<run>/<prediction>/<output>/`: per-image risk JSON, deterministic ranking, summary, and resolved config / 单图风险 JSON、确定性排序、摘要和实际配置。
- `results/reports/<run>/<prediction>/<risk>/<output>/`: offline bilingual HTML dashboard and provenance manifest / 离线双语 HTML 仪表板和来源清单。
- `results/inspections/<run>/<inspection-id>/`: normalized source, annotated image, prediction, risk record, and provenance manifest / 规范化原图、标注图、预测、风险记录和来源清单。

## Learning Guide / 学习指南

Read [`docs/learning-guide.md`](docs/learning-guide.md) for bilingual explanations of Python environments, labels, splits, training, metrics, MPS, and experiment interpretation.

阅读 [`docs/learning-guide.md`](docs/learning-guide.md)，了解 Python 环境、标签、数据划分、训练、指标、MPS 和实验解读。

The v0.2 formula, output schema, recovery steps, and safety boundary are explained in [`docs/risk-engine-guide.md`](docs/risk-engine-guide.md).

v0.2 的公式、输出结构、恢复步骤和安全边界见 [`docs/risk-engine-guide.md`](docs/risk-engine-guide.md)。

The v0.3 offline dashboard workflow is explained in [`docs/local-report-guide.md`](docs/local-report-guide.md).

v0.3 离线仪表板流程见 [`docs/local-report-guide.md`](docs/local-report-guide.md)。

The completed v1.1 local upload app is explained in [`docs/local-app-guide.md`](docs/local-app-guide.md).

完整的 v1.1 本地上传应用见 [`docs/local-app-guide.md`](docs/local-app-guide.md)。

## Data and Citation / 数据与引用

RDD2022 is downloaded from its maintainers and is not redistributed here: <https://github.com/sekilab/RoadDamageDetector>. Cite the dataset article: <https://arxiv.org/abs/2209.08538>.

RDD2022 从维护者来源下载，本仓库不重新分发。使用数据时请引用上述资料。

## License / 许可

Repository code is licensed under `AGPL-3.0-or-later`. Ultralytics licensing must be reviewed again before any closed-source commercial use.

仓库代码采用 `AGPL-3.0-or-later`。任何闭源商业使用前必须重新审查 Ultralytics 许可。
