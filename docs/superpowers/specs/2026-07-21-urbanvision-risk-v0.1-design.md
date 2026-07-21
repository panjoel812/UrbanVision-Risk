# UrbanVision-Risk v0.1 Design / 设计规格

**Status / 状态:** Approved in conversation / 已在对话中批准  
**Date / 日期:** 2026-07-21  
**Milestone / 里程碑:** Mission 001 — Local road-damage detection / 本地道路缺陷检测

## 1. Purpose / 项目目的

UrbanVision-Risk is a long-term, fully local AI project for urban infrastructure inspection and risk assessment. Version 0.1 establishes the first complete, measurable computer-vision pipeline on a 24 GB Apple Silicon MacBook Pro.

UrbanVision-Risk 是一个长期维护、完全本地运行的城市基础设施智能巡检与风险评估项目。v0.1 将在 24 GB Apple Silicon MacBook Pro 上建立第一条完整、可测量的计算机视觉流水线。

The v0.1 user provides road images. The system prepares labeled data, fine-tunes an object detector, evaluates it, and writes annotated predictions plus structured JSON. All runtime inference remains local after dependencies, source data, and pretrained weights have been downloaded.

v0.1 接收道路图片，完成标注数据准备、目标检测模型微调、模型评估，并输出带检测框的图片和结构化 JSON。依赖、原始数据和预训练权重完成一次性下载后，推理过程可以离线运行。

## 2. Goals and Non-Goals / 目标与非目标

### 2.1 Goals / 目标

- Use a project-scoped Python 3.11 runtime managed by `uv`; leave `/usr/bin/python3` unchanged.
- 使用 `uv` 管理项目专用 Python 3.11；不修改 `/usr/bin/python3`。
- Prepare and validate an RDD2022 country subset from its original Pascal VOC annotations.
- 从原始 Pascal VOC 标注准备并验证 RDD2022 的国家子集。
- Fine-tune a small YOLO object detector with Apple MPS acceleration.
- 使用 Apple MPS 加速微调小型 YOLO 目标检测模型。
- Produce reproducible splits, configurations, metrics, checkpoints, annotated images, and JSON predictions.
- 生成可复现的数据划分、配置、指标、检查点、标注图片和 JSON 预测。
- Teach every learner-facing operation in Chinese and English.
- 所有面向学习者的操作均提供中英双语说明。
- Remain free of paid APIs and cloud runtime dependencies.
- 不使用付费 API，也不依赖云端运行环境。

### 2.2 Non-Goals / 非目标

The following are explicitly outside v0.1:

以下内容明确不属于 v0.1：

- Web dashboard or mobile application / Web 仪表盘或移动应用
- Risk scoring engine / 风险评分引擎
- Local LLM report generation / 本地大语言模型报告生成
- Bridge, tunnel, or building inspection / 桥梁、隧道或建筑巡检
- GIS, historical comparison, or spatiotemporal prediction / GIS、历史变化或时空预测
- Large-scale multi-country training or publishable research claims / 大规模多国训练或可发表的科研结论
- Commercial or closed-source distribution / 商业或闭源分发

## 3. Learning Collaboration Model / 学习协作方式

Codex prepares project files, writes and tests code, diagnoses terminal output, and explains results. The learner runs the milestone commands, returns complete output, and observes generated artifacts.

Codex 负责搭建项目文件、编写和测试代码、诊断终端输出并解释结果；学习者负责运行里程碑命令、返回完整输出并观察生成物。

Every command handoff uses this format:

每条命令均按以下格式交付：

1. Goal / 目标
2. Why it is needed / 为什么需要
3. Exact command / 精确命令
4. Expected output / 预期输出
5. Explanation of the output / 输出含义
6. Common failures and recovery / 常见错误与恢复方法
7. Next checkpoint / 下一检查点

Source-code identifiers are English. The README, learning guide, milestone instructions, environment checks, and actionable error messages are bilingual.

源码中的标识符使用英文；README、学习指南、里程碑说明、环境检查和可操作错误信息使用中英双语。

## 4. System Architecture / 系统架构

```text
uv-managed Python 3.11 / uv 管理的 Python 3.11
                    |
                    v
Environment and MPS check / 环境与 MPS 检查
                    |
                    v
Official RDD2022 subset / 官方 RDD2022 子集
                    |
                    v
Pascal VOC -> YOLO conversion / Pascal VOC 转 YOLO
                    |
                    v
Dataset validation and manifest / 数据验证与清单
                    |
                    v
YOLO26n smoke and baseline training / 冒烟与基线训练
                    |
             +------+------+
             |             |
             v             v
Evaluation metrics    Annotated prediction
评估指标               标注预测图
             |             |
             +------+------+
                    v
Structured JSON for later risk engine
供未来风险引擎使用的结构化 JSON
```

Each module has one responsibility and communicates through documented files or typed Python interfaces. Data preparation does not train models; training does not download data; prediction does not calculate future risk scores.

每个模块只承担一种职责，并通过有文档说明的文件或带类型的 Python 接口通信。数据准备不训练模型，训练不下载数据，预测不计算未来的风险分数。

## 5. Repository Layout / 仓库结构

```text
UrbanVision-Risk/
├── .gitignore
├── .python-version
├── LICENSE
├── README.md
├── pyproject.toml
├── uv.lock
├── configs/
│   ├── dataset-rdd2022-china-motorbike.yaml
│   ├── train-smoke.yaml
│   └── train-baseline.yaml
├── data/
│   └── README.md
├── docs/
│   ├── learning-guide.md
│   └── superpowers/
│       ├── plans/
│       └── specs/
├── models/
│   └── README.md
├── results/
│   └── README.md
├── src/urbanvision_risk/
│   ├── __init__.py
│   ├── errors.py
│   ├── environment.py
│   ├── paths.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── download.py
│   │   ├── prepare.py
│   │   ├── split.py
│   │   ├── validate.py
│   │   └── voc.py
│   └── detection/
│       ├── __init__.py
│       ├── evaluate.py
│       ├── predict.py
│       └── train.py
└── tests/
    ├── fixtures/
    │   ├── sample.jpg
    │   └── sample.xml
    ├── test_dataset_split.py
    ├── test_dataset_validation.py
    ├── test_environment.py
    ├── test_training_config.py
    └── test_voc_conversion.py
```

Generated data, downloaded archives, model weights, and experiment outputs are ignored by Git. Small README files explain how those local directories are populated.

生成的数据、下载压缩包、模型权重和实验输出不提交 Git。对应目录保留小型 README，说明内容如何生成。

## 6. Python Environment and Dependencies / Python 环境与依赖

The project requires Python `>=3.11,<3.12`. `uv python install 3.11` supplies the project runtime and `.python-version` selects it. The macOS-managed `/usr/bin/python3` remains untouched.

项目要求 Python `>=3.11,<3.12`。`uv python install 3.11` 提供项目运行时，`.python-version` 负责选择该版本；macOS 管理的 `/usr/bin/python3` 保持不变。

Direct runtime dependencies are Ultralytics, PyTorch, OpenCV, Pillow, PyYAML, and NumPy. Pytest and Ruff belong to the `[project.optional-dependencies].dev` extra, which is installed with `uv sync --extra dev`. Exact resolved package versions are recorded in the committed `uv.lock`; reproducible setup uses `uv sync --frozen --extra dev` after the lock exists.

直接运行依赖包括 Ultralytics、PyTorch、OpenCV、Pillow、PyYAML 和 NumPy；pytest 和 Ruff 位于 `[project.optional-dependencies].dev` extra 中，并通过 `uv sync --extra dev` 安装。解析后的精确版本写入并提交 `uv.lock`；锁文件存在后使用 `uv sync --frozen --extra dev` 复现环境。

The environment check verifies:

环境检查验证：

- Python is in the supported 3.11 range / Python 位于支持的 3.11 范围
- PyTorch imports successfully / PyTorch 可成功导入
- `torch.backends.mps.is_built()` is true / PyTorch 已构建 MPS 支持
- `torch.backends.mps.is_available()` is true / 当前机器可使用 MPS
- A small tensor operation completes on `mps` and synchronizes / 小型张量操作可在 MPS 上完成并同步
- Required project paths resolve inside the repository / 所需路径均解析到项目仓库内部

There is no silent CPU fallback. A learner may explicitly select CPU for diagnostics, but the normal training profiles require MPS.

程序不静默回退到 CPU。学习者可以明确选择 CPU 进行诊断，但正常训练配置要求使用 MPS。

## 7. Dataset / 数据集

### 7.1 Source and Classes / 来源与类别

RDD2022 contains 47,420 road images from six countries and more than 55,000 annotated damage instances. Its annotated training data uses JPG images and Pascal VOC XML annotations. The four retained classes and immutable YOLO indices are:

RDD2022 包含来自六个国家的 47,420 张道路图片和超过 55,000 个缺陷实例。带标注的训练数据由 JPG 图片与 Pascal VOC XML 构成。保留的四个类别及固定 YOLO 索引如下：

| YOLO index | RDD code | English | 中文 |
|---:|---|---|---|
| 0 | D00 | Longitudinal crack | 纵向裂缝 |
| 1 | D10 | Transverse crack | 横向裂缝 |
| 2 | D20 | Alligator crack | 网状裂缝 |
| 3 | D40 | Pothole | 坑洞 |

The first learning baseline uses the approximately 183.1 MB `RDD2022_China_MotorBike` country archive from the project maintainers. The complete multi-country dataset is deferred until this pipeline passes all acceptance checks.

第一个学习基线使用项目维护者提供、约 183.1 MB 的 `RDD2022_China_MotorBike` 国家压缩包。完整多国数据集在本流水线通过所有验收项后再引入。

### 7.2 Local Data Layout / 本地数据布局

```text
data/
├── downloads/
│   └── RDD2022_China_MotorBike.zip
├── raw/
│   └── rdd2022/china-motorbike/
└── processed/
    └── rdd2022-china-motorbike/
        ├── images/{train,val,test}/
        ├── labels/{train,val,test}/
        └── manifest.json
```

The downloader streams the official archive to a temporary `.part` file, records its SHA-256 digest, and renames it only after a successful download. It never treats an incomplete file as a valid archive.

下载器把官方压缩包流式写入临时 `.part` 文件，记录 SHA-256 摘要，并仅在下载成功后重命名；不把未完成文件当作有效压缩包。

Before extraction, every ZIP member path is resolved and checked to remain under the intended raw-data directory. Absolute paths and `..` traversal entries are rejected, preventing an archive from writing outside the project data area.

解压前，程序解析每个 ZIP 成员路径，并验证其始终位于目标原始数据目录内。绝对路径和包含 `..` 的路径穿越条目会被拒绝，防止压缩包向项目数据区之外写入文件。

Raw extracted files are immutable inputs. The converter copies source images into the small processed v0.1 subset with `shutil.copy2` and writes new YOLO label files. It never edits or deletes raw files.

解压后的原始文件是不可变输入。转换器使用 `shutil.copy2` 把图片复制到规模较小的 v0.1 处理目录，并写入新的 YOLO 标签；不编辑或删除原始文件。

### 7.3 Deterministic Split / 确定性划分

Only annotated source images participate in local training and evaluation. Image identifiers are sorted, shuffled by `random.Random(42)`, and split by count into 80% training, 10% validation, and 10% local test data. The original unannotated challenge test images remain separate and are used only for qualitative prediction.

只有带标注的原始图片用于本地训练和评估。图片标识符先排序，再由 `random.Random(42)` 打乱，并按数量分成 80% 训练、10% 验证和 10% 本地测试。原始无标注竞赛测试图片单独保存，仅用于定性预测。

This simple image-level split is appropriate for the learning baseline but may overestimate generalization when nearby video frames are similar. Future research experiments must use grouping or country-held-out evaluation before making publication claims.

这种图片级随机划分适合学习基线，但相邻视频帧相似时可能高估泛化能力。未来科研实验在形成可发表结论前，必须采用分组或国家留出评估。

### 7.4 VOC-to-YOLO Conversion / VOC 转 YOLO

For an image of width `W` and height `H`, a Pascal VOC box `(xmin, ymin, xmax, ymax)` becomes:

对宽度为 `W`、高度为 `H` 的图片，Pascal VOC 边界框 `(xmin, ymin, xmax, ymax)` 转换为：

```text
x_center = ((xmin + xmax) / 2) / W
y_center = ((ymin + ymax) / 2) / H
box_width = (xmax - xmin) / W
box_height = (ymax - ymin) / H
```

Every output line is `class_index x_center y_center box_width box_height`. Coordinates must be finite and within `[0,1]`; width and height must be greater than zero. Unknown classes, malformed XML, missing images, and invalid boxes fail preparation with an actionable error instead of being silently skipped.

每行输出为 `class_index x_center y_center box_width box_height`。坐标必须为有限数且位于 `[0,1]`，宽和高必须大于零。未知类别、损坏 XML、图片缺失或非法边界框都会以可操作错误终止准备流程，不会被静默忽略。

### 7.5 Manifest / 数据清单

`manifest.json` records source URL, local archive SHA-256, preparation timestamp, split seed and ratios, file counts, object counts per class, invalid-record count, and the SHA-256 digest of the manifest inputs. Training summaries reference this manifest digest.

`manifest.json` 记录来源 URL、本地压缩包 SHA-256、准备时间、划分种子与比例、文件数量、各类别实例数量、非法记录数量以及清单输入摘要。训练摘要引用该清单摘要。

## 8. Model and Training / 模型与训练

### 8.1 Model / 模型

The baseline fine-tunes the current small Ultralytics object-detection checkpoint `yolo26n.pt`. It uses transfer learning rather than training a detector from random initialization.

基线微调当前的小型 Ultralytics 目标检测检查点 `yolo26n.pt`，采用迁移学习而不是从随机初始化开始训练。

### 8.2 Smoke Profile / 冒烟配置

The `smoke` profile validates the end-to-end training path:

`smoke` 配置验证端到端训练链路：

```yaml
model: yolo26n.pt
epochs: 1
imgsz: 640
batch: 4
device: mps
workers: 2
seed: 42
deterministic: true
cache: false
fraction: 0.1
```

Accuracy is not a smoke-test acceptance criterion. The run must read the prepared dataset, complete one epoch, validate, and save checkpoints and metrics.

准确率不是冒烟测试验收项。该运行必须读取准备后的数据，完成一个 epoch 和验证，并保存检查点及指标。

### 8.3 Baseline Profile / 基线配置

The `baseline` profile trains on the complete prepared China MotorBike training split:

`baseline` 配置使用完整的 China MotorBike 处理后训练集：

```yaml
model: yolo26n.pt
epochs: 30
imgsz: 640
batch: 8
device: mps
workers: 2
seed: 42
deterministic: true
cache: false
fraction: 1.0
```

The learner may later change batch size only in a new named experiment. The accepted baseline configuration remains unchanged for reproducibility.

学习者之后只能在新命名实验中修改 batch size；已验收的基线配置保持不变，以保证可复现性。

### 8.4 Experiment Safety and Outputs / 实验安全与输出

Every run requires a unique run name. If its output directory already exists, training stops instead of overwriting it. Expected directories are:

每次运行必须使用唯一名称。输出目录已经存在时，训练停止而不是覆盖。预期目录如下：

```text
results/experiments/
├── smoke-test-001/
│   ├── weights/{best.pt,last.pt}
│   └── results.csv
└── china-baseline-001/
    ├── weights/{best.pt,last.pt}
    ├── results.csv
    ├── confusion_matrix.png
    └── training_summary.json
```

`training_summary.json` contains the run name, start/end timestamps, Git commit, dataset manifest digest, model name, effective training parameters, selected device, library versions, and evaluation metrics.

`training_summary.json` 包含运行名称、起止时间、Git 提交、数据清单摘要、模型名称、实际训练参数、所选设备、库版本和评估指标。

## 9. Evaluation and Prediction / 评估与预测

Evaluation uses the local held-out test split and reports overall and per-class precision, recall, F1, mAP@50, and mAP@50-95, plus a confusion matrix. v0.1 records honest measurements and defines no artificial minimum accuracy threshold.

评估使用本地留出测试集，报告整体及各类别的 Precision、Recall、F1、mAP@50、mAP@50-95 和混淆矩阵。v0.1 如实记录测量结果，不设人为最低准确率门槛。

Prediction accepts one image or one directory and writes an annotated image plus JSON. Each detection contains:

预测接受单张图片或一个目录，输出带框图片与 JSON。每个检测项包含：

```json
{
  "class_id": 3,
  "code": "D40",
  "name_en": "Pothole",
  "name_zh": "坑洞",
  "confidence": 0.87,
  "bbox_xyxy": [120.0, 80.0, 260.0, 210.0]
}
```

The top-level JSON also records source image, model checkpoint, inference parameters, image dimensions, detections, and counts by class. A valid no-detection result contains an empty list and an explicit bilingual explanation; the program never invents boxes.

顶层 JSON 还记录源图片、模型检查点、推理参数、图片尺寸、检测列表和分类计数。合法的无检测结果包含空列表及明确的中英双语说明；程序绝不伪造边界框。

## 10. Command Interfaces / 命令接口

The learner-facing sequence is:

面向学习者的命令顺序是：

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
uv run python -m urbanvision_risk.detection.predict --run-name china-baseline-001 --source PATH_TO_IMAGE
```

Each Python module uses `argparse`, typed functions, nonzero exit codes on failure, and repository-relative defaults resolved through `paths.py`. Commands do not depend on the caller's current directory after the project root has been identified.

每个 Python 模块使用 `argparse`、类型标注函数和非零失败退出码，并通过 `paths.py` 解析仓库相对默认路径。识别项目根目录后，命令不依赖调用者的当前目录。

## 11. Error Handling and Safety / 错误处理与安全

Stable learner-facing error codes are:

稳定的学习者错误编号如下：

| Code | Meaning / 含义 |
|---|---|
| E101 | Unsupported or incorrect Python environment / Python 环境不正确或不支持 |
| E102 | MPS unavailable or tensor check failed / MPS 不可用或张量检查失败 |
| E201 | Dataset/archive/path missing / 数据集、压缩包或路径缺失 |
| E202 | Malformed XML or missing image-label pair / XML 损坏或图像标注不匹配 |
| E203 | Invalid class or bounding box / 类别或边界框非法 |
| E204 | Existing output would be overwritten / 已有输出可能被覆盖 |
| E301 | Model checkpoint missing or unreadable / 模型检查点缺失或不可读 |
| E302 | Training or inference configuration invalid / 训练或推理配置非法 |

Errors print the code, Chinese and English explanation, relevant path or value, and a concrete recovery action. Expected failures do not dump a Python traceback by default; an explicit debug flag enables tracebacks for diagnosis.

错误输出包括编号、中英双语解释、相关路径或数值和具体恢复步骤。预期错误默认不显示 Python traceback；明确启用 debug 参数后才显示，供诊断使用。

No project command permanently deletes files, modifies raw data, or silently overwrites experiments. When removal is truly necessary, instructions use macOS recoverable Trash via `/usr/bin/trash <absolute-path>`.

项目命令不永久删除文件、不修改原始数据，也不静默覆盖实验。确需移除内容时，说明仅使用 macOS 可恢复命令 `/usr/bin/trash <absolute-path>`。

## 12. Testing / 测试

Unit tests use small local fixtures and do not require RDD2022, model weights, or network access. They cover:

单元测试使用小型本地 fixture，不需要 RDD2022、模型权重或网络，覆盖：

- VOC parsing and class mapping / VOC 解析与类别映射
- Exact coordinate normalization and invalid-box rejection / 精确坐标归一化与非法框拒绝
- Deterministic, disjoint 80/10/10 splitting / 确定且互斥的 80/10/10 划分
- Missing/corrupt image and XML detection / 缺失或损坏图片及 XML 检测
- Class-count and manifest generation / 类别统计与清单生成
- Supported Python and MPS status reporting through injectable probes / 通过可注入探针测试 Python 与 MPS 状态报告
- Training-profile schema and unique-run protection / 训练配置结构与唯一运行名保护
- Prediction JSON schema, including empty detections / 预测 JSON 结构，包括空检测

`uv run pytest` must pass before any large download. The one-epoch smoke training is the integration test for PyTorch, Ultralytics, MPS, prepared data, validation, and checkpoint writing.

任何大型下载前，`uv run pytest` 必须通过。单 epoch 冒烟训练是 PyTorch、Ultralytics、MPS、处理后数据、验证与检查点写入的集成测试。

## 13. Documentation / 文档

`README.md` provides the short bilingual setup and milestone sequence. `docs/learning-guide.md` contains:

`README.md` 提供简短的双语安装与里程碑顺序；`docs/learning-guide.md` 包含：

1. Python, `uv`, and virtual environments / Python、`uv` 与虚拟环境
2. Images, labels, and object detection / 图片、标签与目标检测
3. Pascal VOC and YOLO formats / Pascal VOC 与 YOLO 格式
4. Train, validation, and test sets / 训练、验证与测试集
5. Epochs, batches, and losses / Epoch、Batch 与损失函数
6. Precision, recall, F1, and mAP / Precision、Recall、F1 与 mAP
7. Apple MPS and Mac GPU execution / Apple MPS 与 Mac GPU 执行
8. Reading the first experiment / 阅读第一次实验结果

Every lesson ties concepts to an actual project file, includes one learner-run command, and ends with a short review question.

每课把概念对应到实际项目文件，包含一条由学习者运行的命令，并以一个简短复习问题结束。

## 14. Licensing and Citations / 许可与引用

Ultralytics models are available under AGPL-3.0 and enterprise licensing. The free v0.1 repository code is licensed under `AGPL-3.0-or-later` and is intended for learning and research. Closed-source commercial distribution requires a separate license review.

Ultralytics 模型提供 AGPL-3.0 与企业许可。免费的 v0.1 仓库代码明确采用 `AGPL-3.0-or-later` 许可，用于学习与研究；闭源商业发布需要单独进行许可审查。

The repository documents and cites RDD2022 without redistributing the dataset itself. Users download it from the maintainers' source.

仓库记录并引用 RDD2022，但不重新分发数据集本身；用户从维护者来源下载。

Primary references / 主要资料：

- RDD2022 Figshare: <https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547>
- RoadDamageDetector maintainers: <https://github.com/sekilab/RoadDamageDetector>
- RDD2022 paper: <https://arxiv.org/abs/2209.08538>
- Ultralytics training with MPS: <https://docs.ultralytics.com/modes/train>
- PyTorch MPS backend: <https://docs.pytorch.org/docs/stable/notes/mps>

## 15. Acceptance Criteria / 验收标准

UrbanVision-Risk v0.1 is complete only when all conditions hold:

UrbanVision-Risk v0.1 仅在以下条件全部满足时完成：

1. The project uses an isolated Python 3.11 environment and leaves macOS system Python unchanged.  
   项目使用隔离的 Python 3.11 环境，且不修改 macOS 系统 Python。
2. The environment command completes and a real MPS tensor operation passes.  
   环境命令完成，且真实 MPS 张量操作通过。
3. All network-independent automated tests pass before dataset download.  
   数据下载前，所有不依赖网络的自动测试通过。
4. RDD2022 China MotorBike downloads from the maintainer source, extracts without archive errors, and records a local digest.  
   RDD2022 China MotorBike 从维护者来源下载，成功解压并记录本地摘要。
5. Dataset preparation reports zero fatal validation errors and writes a reproducible manifest.  
   数据准备报告零个致命验证错误，并写出可复现清单。
6. The one-epoch MPS smoke run completes and saves checkpoints and metrics.  
   单 epoch MPS 冒烟运行完成并保存检查点与指标。
7. The 30-epoch baseline saves `best.pt`, `last.pt`, metrics, a confusion matrix, and a training summary.  
   30 epoch 基线保存 `best.pt`、`last.pt`、指标、混淆矩阵和训练摘要。
8. Held-out evaluation reports real overall and per-class metrics without invented values.  
   留出评估报告真实的整体与分类指标，不编造数值。
9. Prediction writes at least one annotated test image and matching structured JSON; empty detections remain valid and explicit.  
   预测至少写出一张标注测试图片和匹配的结构化 JSON；空检测必须合法且明确。
10. README and the learning guide explain the completed workflow in Chinese and English.  
    README 与学习指南使用中英双语解释完整流程。

## 16. Deferred Evolution / 后续演进

After v0.1 passes, the next independent design cycles may cover multi-country domain generalization, a quantitative risk engine, a local web dashboard, and local-LLM report generation. None is included implicitly in this milestone.

v0.1 通过后，后续独立设计周期可以覆盖多国域泛化、量化风险引擎、本地 Web 仪表盘和本地 LLM 报告生成；本里程碑不隐含实现这些内容。
