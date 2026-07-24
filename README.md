# UrbanVision-Risk

**中文：** 面向城市基础设施智能巡检、可靠性分析与现场量测的端侧 AI 系统。v5.9 增加防篡改透明度账本：每次自动巡检完成后，系统会把本批次策划与快照、累计策划与快照、漂移审计及批次记录六类工件的真实文件字节绑定到一条规范化 SHA-256 哈希链。追加前后会验证完整历史；改写、缺失、编号错位、序列缺口或断链都会主动失败。v5.8 的确定性 RBF-MMD 漂移审计与小样本拒答全部保留。

**English:** An on-device system for reliable urban-infrastructure inspection and field metrology. Version 5.9 adds a tamper-evident transparency ledger. After every autopilot batch, the service binds the actual file bytes of six artifacts—batch curation and snapshot, cumulative curation and snapshot, drift audit, and batch record—into a canonical SHA-256 hash chain. The complete history is verified before and after append; mutation, loss, identity mismatch, sequence gaps, or broken links fail loudly. The v5.8 deterministic RBF-MMD shift audit and small-sample abstention remain active.

The resilient queue of up to 100 images still performs content deduplication, bounded retry, and per-item failure isolation before batch-scoped governance and cumulative refresh.

最多 100 张图片的弹性队列仍会在双范围治理前执行内容去重、有界重试和单项故障隔离。

Turning Autopilot off preserves the earlier `automatic_draft` workflow. When it is on, deterministic review decisions remain explicitly attributed to `machine_heuristic`; they are never represented as human approval. / 关闭自动驾驶会保留原有 `automatic_draft` 工作流；开启后，确定性复核决定仍明确归属于 `machine_heuristic`，绝不冒充人工批准。

Automatic results are reviewable evidence, not hidden ground truth. The synchronized loupe keeps the original-resolution mask visible while brush/eraser edits, undo, hotspot dispositions, and calibration remain available. Saving an operator correction creates an explicit `human_reviewed` version instead of silently rewriting the earlier `machine_reviewed_candidate`.

自动结果是可复核证据，不是隐藏的“真值”。同步放大窗会显示原分辨率掩膜，同时保留画笔/橡皮、撤销、热点处置和标定功能；保存人工修订时会明确创建 `human_reviewed` 版本，而不会静默改写之前的 `machine_reviewed_candidate`。

**v3.0 Calibrated Metrology / 标定量测：** printable field fiducials, semantic marker detection (`TL/TR/BR/BL`), homography rectification, graph-geodesic length, skeleton distance-transform width, immutable artifacts, privacy-minimized provenance, deterministic uncertainty analysis, and a first-hand field-validation protocol. / 可打印现场标记、语义标记检测、单应性矫正、图测地长度、骨架距离变换宽度、不可覆盖结果、最小化隐私来源记录、确定性不确定性分析和亲身现场验证方案。

**v2.0 Reliability Engineering / 可靠性工程：** 只有至少两个独立视图在类别和位置上达成共识的检测才能进入风险引擎；单视图高分、跨视图定位不稳定或类别冲突会触发人工复核。每次巡检额外保存 `reliability.json`，并通过 `/api/review-queue` 暴露完全本地的主动学习优先级。 / Only detections supported by at least two independent views can enter the risk engine. Single-view high scores, unstable localization, and class disagreement trigger review. Every inspection adds an immutable `reliability.json`, while `/api/review-queue` exposes a fully local active-learning priority queue.

## v5.9 Quick Start / v5.9 快速启动

```bash
uv sync --extra dev

# Verify the calibrated graph-metrology pipeline with a deterministic fixture
uv run python -m urbanvision_risk.metrology.demo --output-name metrology-demo-001

# Generate four printable field fiducials
uv run python -m urbanvision_risk.metrology.target --output-name aruco-field-kit-001

# Start the unified reliability + metrology workflow
uv run python -m urbanvision_risk.app.serve --run-name china-repair-mps-003
```

The first command creates auditable measurement artifacts under `results/metrology/metrology-demo-001`. The second creates four exact-size SVG fiducials and a field manifest. The third opens the complete workflow directly at `http://127.0.0.1:8000`. Keep **Autopilot** checked and choose one or more images. Each successful item receives an arbitration record. `urbanvision-autopilot-batch-v1.5.0` binds batch governance, cumulative governance, and `urbanvision-feedback-drift-audit-v1.0.0`; the resulting six artifacts then enter `urbanvision-transparency-entry-v1.0.0`.

第一条命令生成可审计量测样本；第二条生成四张精确尺寸现场标记；第三条在 `http://127.0.0.1:8000` 打开完整单页流程。保持 **自动驾驶开启**，一次选择一张或多张图片。每个成功项都生成仲裁记录；`urbanvision-autopilot-batch-v1.5.0` 绑定本批次治理、累计治理与 `urbanvision-feedback-drift-audit-v1.0.0`，随后六类工件进入 `urbanvision-transparency-entry-v1.0.0`。端口被占用时使用 `--port 8001`。

The v5.7 curator writes `urbanvision-feedback-curation-v2.3.0`, and snapshot preflight writes `urbanvision-feedback-snapshot-preflight-v1.2.0`. The page displays the exact current-batch scope and an automatically refreshed all-session local feedback registry scope. A 67/67 byte-integrity result can therefore be shown as technically verified while governance remains blocked, instead of being collapsed into the misleading phrase “upstream not ready.”

v5.7 策划器写入 `urbanvision-feedback-curation-v2.3.0`，快照预检写入 `urbanvision-feedback-snapshot-preflight-v1.2.0`。网页同时显示精确的本批次范围与自动刷新的跨会话累计范围。因此“67/67 数据对字节完整”可以诚实显示为技术完整性通过，同时明确标注治理审批未完成，不再被压缩成容易误解的“上游尚未就绪”。

The drift audit is monitoring evidence only. A low p-value says the bounded feature distributions differ; it does not prove concept drift, model-accuracy loss, label correctness, or road danger. `training_authorized` remains `false`.

漂移审计只属于监测证据。较低的 p 值只表示这些有界特征的分布存在差异，不能证明概念漂移、模型准确率下降、标签正确或道路危险；`training_authorized` 仍保持 `false`。

`GET /api/metrology/transparency-log` rehashes every ledger entry and every bound artifact on demand. This is local tamper evidence, not absolute immutability: an attacker controlling the entire disk could rewrite or truncate the whole chain. The project does not claim an external timestamp, transparency service, or notarization.

`GET /api/metrology/transparency-log` 会按需重新计算每条账本记录及全部绑定工件的摘要。这是本机防篡改证据，不是绝对不可变性：控制整块磁盘的攻击者仍可能重写或截断整条链；项目不声称外部时间戳、透明度服务或公证。

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
- `results/metrology/transparency-log/*.json`: local canonical hash-chain entries that bind and re-verify six governance artifacts per batch / 本机规范化哈希链记录，每个批次绑定并复核六类治理工件。
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
