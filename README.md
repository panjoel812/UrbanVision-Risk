# UrbanVision-Risk

**中文：** 面向城市基础设施智能巡检、可靠性分析与现场量测的端侧 AI 系统。v5.6 增加自修复数据就绪层：视觉簇至少覆盖三个正比例切分时，确定性分配器自动为 train、val、test 各保留一个完整视觉簇；审计结果直接给出还缺多少独立原图、视觉簇和人工批准。官方 RDD2022 只作为 CC BY-SA 4.0 检测基准引用，不会被冒充为本地像素掩膜真值。v5.5 的 YOLO × 分割同源仲裁、拒答机制和 SHA-256 证据绑定全部保留，最多 100 张图片的内容去重与自愈队列继续生效。

**English:** An on-device system for reliable urban-infrastructure inspection and field metrology. Version 5.6 adds self-remediating data readiness: when visual groups can cover all three positive-ratio splits, the deterministic allocator reserves a whole group for train, validation, and test, then reports exact source, scene-group, and approval deficits. Official RDD2022 is referenced only as a CC BY-SA 4.0 detector benchmark, never disguised as local pixel-mask ground truth. The v5.5 YOLO × segmentation source arbitration, selective abstention, and SHA-256 evidence binding remain active. The resilient queue of up to 100 images still deduplicates by content before batch-scoped governance.

Turning Autopilot off preserves the earlier `automatic_draft` workflow. When it is on, deterministic review decisions remain explicitly attributed to `machine_heuristic`; they are never represented as human approval. / 关闭自动驾驶会保留原有 `automatic_draft` 工作流；开启后，确定性复核决定仍明确归属于 `machine_heuristic`，绝不冒充人工批准。

Automatic results are reviewable evidence, not hidden ground truth. The synchronized loupe keeps the original-resolution mask visible while brush/eraser edits, undo, hotspot dispositions, and calibration remain available. Saving an operator correction creates an explicit `human_reviewed` version instead of silently rewriting the earlier `machine_reviewed_candidate`.

自动结果是可复核证据，不是隐藏的“真值”。同步放大窗会显示原分辨率掩膜，同时保留画笔/橡皮、撤销、热点处置和标定功能；保存人工修订时会明确创建 `human_reviewed` 版本，而不会静默改写之前的 `machine_reviewed_candidate`。

**v3.0 Calibrated Metrology / 标定量测：** printable field fiducials, semantic marker detection (`TL/TR/BR/BL`), homography rectification, graph-geodesic length, skeleton distance-transform width, immutable artifacts, privacy-minimized provenance, deterministic uncertainty analysis, and a first-hand field-validation protocol. / 可打印现场标记、语义标记检测、单应性矫正、图测地长度、骨架距离变换宽度、不可覆盖结果、最小化隐私来源记录、确定性不确定性分析和亲身现场验证方案。

**v2.0 Reliability Engineering / 可靠性工程：** 只有至少两个独立视图在类别和位置上达成共识的检测才能进入风险引擎；单视图高分、跨视图定位不稳定或类别冲突会触发人工复核。每次巡检额外保存 `reliability.json`，并通过 `/api/review-queue` 暴露完全本地的主动学习优先级。 / Only detections supported by at least two independent views can enter the risk engine. Single-view high scores, unstable localization, and class disagreement trigger review. Every inspection adds an immutable `reliability.json`, while `/api/review-queue` exposes a fully local active-learning priority queue.

## v5.6 Quick Start / v5.6 快速启动

```bash
uv sync --extra dev

# Verify the calibrated graph-metrology pipeline with a deterministic fixture
uv run python -m urbanvision_risk.metrology.demo --output-name metrology-demo-001

# Generate four printable field fiducials
uv run python -m urbanvision_risk.metrology.target --output-name aruco-field-kit-001

# Start the unified reliability + metrology workflow
uv run python -m urbanvision_risk.app.serve --run-name china-repair-mps-003
```

The first command creates auditable measurement artifacts under `results/metrology/metrology-demo-001`. The second creates four exact-size SVG fiducials and a field manifest. The third opens the complete workflow directly at `http://127.0.0.1:8000`. Keep **Autopilot** checked and choose one or more images. After parallel detector and segmentation execution, the page automatically shows cross-channel support, suspected semantic miss, detector-only evidence, spatial disagreement, or inconclusive evidence. Each successful item receives an arbitration record, and `urbanvision-autopilot-batch-v1.2.0` binds those records before governance.

第一条命令生成可审计量测样本；第二条生成四张精确尺寸现场标记；第三条在 `http://127.0.0.1:8000` 打开完整单页流程。保持 **自动驾驶开启**，一次选择一张或多张图片。检测与分割并行结束后，页面自动显示双通道支持、疑似语义漏检、仅检测器证据、空间分歧或无充分证据；每个成功项都生成仲裁记录，`urbanvision-autopilot-batch-v1.2.0` 在治理前绑定这些证据。端口被占用时使用 `--port 8001`。

The v5.6 curator writes `urbanvision-feedback-curation-v2.2.0`. Three independent visual groups now produce non-empty train/validation/test splits instead of silently placing every candidate in train. Its structured remediation block distinguishes the cumulative local-registry deficit from the minimum size of a fresh batch-scoped run, and reports machine candidates awaiting independent approval. Snapshot preflight v1.1 carries the same upstream guidance.

v5.6 策划器写入 `urbanvision-feedback-curation-v2.2.0`。三个独立视觉簇现在会得到非空的训练、验证和测试切分，而不是把所有候选静默塞进训练集；结构化修复建议会区分“本机累计台账还差多少”和“全新批次至少要选多少”，并显示多少机器候选等待独立批准。快照预检 v1.1 会继承同一份上游建议。

The app and metrology pipeline are local-only. Press `Control+C` to stop a running server. Neither component calls a paid API or cloud runtime.

应用与量测管线都只在本机运行。回到终端按 `Control+C` 停止服务器；二者都不调用付费 API 或云端运行环境。

After inspection, select **Generate locally / 生成本地说明**. If Ollama with `qwen3:4b` is available on `127.0.0.1:11434`, the app uses it. Otherwise it immediately returns an audited bilingual template. The image, original filename, and local paths are never sent to the narrative generator.

巡检完成后点击 **生成本地说明**。如果 `127.0.0.1:11434` 上存在 Ollama 与 `qwen3:4b`，应用会使用本地模型；否则立即返回可审计双语模板。原图、原文件名和本机路径绝不进入说明生成器。

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
uv run python -m urbanvision_risk.detection.evaluate --run-name china-repair-mps-003
uv run python -m urbanvision_risk.detection.predict --run-name china-repair-mps-003 --source data/processed/rdd2022-china-motorbike-repair-v1.1/images/test

# v0.2: score an existing prediction batch; this does not rerun YOLO
uv run python -m urbanvision_risk.risk.assess --run-name china-baseline-001 --prediction-name prediction-001 --output-name risk-001

# v0.3: build an offline bilingual dashboard; this does not need a server
uv run python -m urbanvision_risk.reporting.build --run-name china-baseline-001 --prediction-name prediction-001 --risk-name risk-001 --output-name report-001

# v2.0: multi-view consensus, reliability evidence, active learning, and local narrative
uv run python -m urbanvision_risk.app.serve --run-name china-repair-mps-003

# v3.0: calibrated crack topology and physical metrology
uv run python -m urbanvision_risk.metrology.demo --output-name metrology-demo-001
uv run python -m urbanvision_risk.metrology.target --output-name aruco-field-kit-001
```

## Generated Artifacts / 生成物

- `data/processed/rdd2022-china-motorbike/manifest.json`: data lineage and counts / 数据来源与统计。
- `data/processed/rdd2022-china-motorbike-repair-v1.1/manifest.json`: five-class v1.1 data lineage, including the auxiliary Repair observation / v1.1 五类数据来源，包含 Repair 辅助观察。
- `results/experiments/<run>/weights/best.pt`: best checkpoint / 最佳模型。
- `results/evaluations/<run>/evaluation.json`: held-out metrics / 留出集指标。
- `results/predictions/<run>/<output>/`: annotated JPG and JSON / 带框图片与 JSON。
- `results/risks/<run>/<prediction>/<output>/`: per-image risk JSON, deterministic ranking, summary, and resolved config / 单图风险 JSON、确定性排序、摘要和实际配置。
- `results/reports/<run>/<prediction>/<risk>/<output>/`: offline bilingual HTML dashboard and provenance manifest / 离线双语 HTML 仪表板和来源清单。
- `results/inspections/<run>/<inspection-id>/`: normalized source, annotation, prediction, risk record, provenance, and optional immutable `narrative.json` / 规范化原图、标注、预测、风险、来源记录和可选不可变 `narrative.json`。
- `results/metrology/<output>/measurement.json`: calibrated topology, physical geometry, uncertainty, provenance, and decision boundaries; sibling files contain source/rectified masks, skeletons, width heatmaps, and overlays / 标定拓扑、真实几何量、不确定性、来源和使用边界；同目录还包含原始/矫正掩膜、骨架、宽度热图和叠加图。
- `results/metrology/proposals/<proposal>/`: immutable `proposal-mask.png`, `review-hotspots.png`, and algorithm `evidence.json`; the source image itself is not retained / 不可覆盖的候选掩膜、复核热点与算法证据；不保存原图本身。
- `results/metrology/<output>/active-learning-feedback.zip`: deterministic machine- or human-authored ROI feedback with explicit review authority / 带明确审核身份的确定性机器或人工 ROI 反馈包。
- `results/metrology/curations/*.json` and `results/metrology/snapshots/*.json`: automatically generated leakage-safe plans and content-addressed Merkle preflight records; neither authorizes training / 自动生成的防泄漏策划与内容寻址 Merkle 预检记录；二者都不授权训练。
- `results/metrology/arbitrations/*.json`: immutable YOLO–segmentation source binding, spatial support, abstention state, and claim boundary / 不可覆盖的 YOLO—分割同源绑定、空间支持、拒答状态与使用边界。
- `results/metrology/autopilot-batches/*.json`: privacy-minimized batch ledger binding completed machine runs and arbitration evidence to one curation and snapshot / 隐私最小化批次台账，把成功机器运行及仲裁证据绑定到一次策划与快照。
- `results/metrology/<output>/plans/*.json`: immutable material quantity, cost assumptions, measurement digest, and decision boundary / 不可覆盖的材料数量、成本假设、量测摘要和使用边界。
- `results/metrology/comparisons/*.json` and `*-change-map.png`: normalized two-date changes, physical alignment quality, spatial classes, daily growth, user thresholds, and source-record digests / 统一单位的两期变化、物理对齐质量、空间分类、每日增长、用户阈值和源记录摘要。

## Learning Guide / 学习指南

Read [`docs/learning-guide.md`](docs/learning-guide.md) for bilingual explanations of Python environments, labels, splits, training, metrics, MPS, and experiment interpretation.

阅读 [`docs/learning-guide.md`](docs/learning-guide.md)，了解 Python 环境、标签、数据划分、训练、指标、MPS 和实验解读。

The v0.2 formula, output schema, recovery steps, and safety boundary are explained in [`docs/risk-engine-guide.md`](docs/risk-engine-guide.md).

v0.2 的公式、输出结构、恢复步骤和安全边界见 [`docs/risk-engine-guide.md`](docs/risk-engine-guide.md)。

The v0.3 offline dashboard workflow is explained in [`docs/local-report-guide.md`](docs/local-report-guide.md).

v0.3 离线仪表板流程见 [`docs/local-report-guide.md`](docs/local-report-guide.md)。

The v2.0 local app is explained in [`docs/local-app-guide.md`](docs/local-app-guide.md). Its algorithms and interview-ready engineering decisions are documented in [`docs/reliability-engineering-guide.md`](docs/reliability-engineering-guide.md) and [`docs/portfolio-guide.md`](docs/portfolio-guide.md). The optional Ollama/template layer remains documented in [`docs/local-ai-narrative-guide.md`](docs/local-ai-narrative-guide.md).

完整的 v2.0 本地应用见 [`docs/local-app-guide.md`](docs/local-app-guide.md)。算法、工程取舍与简历/面试表达见 [`docs/reliability-engineering-guide.md`](docs/reliability-engineering-guide.md) 和 [`docs/portfolio-guide.md`](docs/portfolio-guide.md)；本地 Ollama/模板层仍见 [`docs/local-ai-narrative-guide.md`](docs/local-ai-narrative-guide.md)。

The complete v3.0 algorithms, print workflow, automatic ArUco calibration, mask contract, commands, limitations, and first-hand validation protocol are in [`docs/metrology-field-guide.md`](docs/metrology-field-guide.md). Record each experiment with [`docs/field-experiment-template.md`](docs/field-experiment-template.md).

v3.0 的算法、打印流程、ArUco 自动标定、掩膜契约、命令、限制与亲身验证方案见 [`docs/metrology-field-guide.md`](docs/metrology-field-guide.md)；每次实验使用 [`docs/field-experiment-template.md`](docs/field-experiment-template.md) 记录。

## Data and Citation / 数据与引用

RDD2022 is downloaded from its maintainers and is not redistributed here: <https://github.com/sekilab/RoadDamageDetector>. Cite the dataset article: <https://arxiv.org/abs/2209.08538>.

RDD2022 从维护者来源下载，本仓库不重新分发。使用数据时请引用上述资料。

## License / 许可

Repository code is licensed under `AGPL-3.0-or-later`. Ultralytics licensing must be reviewed again before any closed-source commercial use.

仓库代码采用 `AGPL-3.0-or-later`。任何闭源商业使用前必须重新审查 Ultralytics 许可。
