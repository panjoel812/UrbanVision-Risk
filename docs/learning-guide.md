# UrbanVision-Risk v0.1 Learning Guide / 学习指南

This guide connects each concept to code you can run locally. Each lesson has one command; run it from the repository root and return the output before moving on.

本指南把每个概念对应到可在本机运行的代码。每课包含一条命令；从仓库根目录运行，并在继续前返回输出。

## Lesson 01 — Python, uv, and Isolation / Python、uv 与隔离环境

**中文：** macOS 的 `/usr/bin/python3` 属于系统。`uv` 另外安装 Python 3.11，并在 `.venv` 中保存本项目依赖。隔离环境防止一个项目升级包时破坏另一个项目。

**English:** `/usr/bin/python3` belongs to macOS. uv installs a separate Python 3.11 and stores this project's dependencies in `.venv`, preventing package changes from breaking unrelated projects.

File / 文件: `.python-version`, `pyproject.toml`, `uv.lock`

Command / 命令: `uv run python --version`

Expected / 预期: `Python 3.11.x`; the exact patch and packages are locked by uv.

**复习问题 / Review question:** Why do we keep the system Python unchanged? / 为什么不修改系统 Python？

## Lesson 02 — Images, Labels, and Object Detection / 图片、标签与目标检测

**中文：** 图片是模型输入；标签说明缺陷类别和位置。目标检测同时回答“是什么”和“在哪里”，而普通分类只回答“是什么”。

**English:** Images are model inputs; labels describe defect class and location. Object detection answers both “what” and “where,” while classification answers only “what.”

File / 文件: `src/urbanvision_risk/data/voc.py`

Command / 命令: `uv run pytest tests/test_voc_conversion.py -v`

Expected / 预期: valid labels convert and invalid boxes are rejected.

**复习问题 / Review question:** What extra information does a bounding box provide? / 边界框比分类标签多提供什么信息？

## Lesson 03 — Pascal VOC and YOLO Labels / Pascal VOC 与 YOLO 标注

**中文：** RDD2022 使用 XML 中的像素坐标。YOLO 使用 `class x_center y_center width height`，并把坐标归一化到 0–1。归一化让不同分辨率图片使用同一种表示。

**English:** RDD2022 stores pixel coordinates in XML. YOLO uses `class x_center y_center width height`, normalized to 0–1 so different image resolutions share one representation.

File / 文件: `src/urbanvision_risk/data/voc.py`

Command / 命令: `uv run python -m urbanvision_risk.data.validate`

Expected / 预期: split counts, class counts, and a final bilingual PASS.

**复习问题 / Review question:** Why are YOLO coordinates divided by image width or height? / YOLO 坐标为什么除以图片宽或高？

## Lesson 04 — Train, Validation, and Test / 训练、验证与测试集

**中文：** 训练集用于更新模型参数；验证集用于训练过程中比较表现；测试集只在训练完成后估计泛化能力。v0.1 固定 seed 42 和 80/10/10 划分，保证重复实验使用相同图片。

**English:** Training data updates model parameters, validation data tracks training decisions, and held-out test data estimates generalization after training. Seed 42 and an 80/10/10 split keep membership reproducible.

File / 文件: `src/urbanvision_risk/data/split.py`

Command / 命令: `uv run pytest tests/test_dataset_split.py -v`

Expected / 预期: deterministic and disjoint split tests PASS.

**复习问题 / Review question:** Why should test images not train the model? / 为什么测试图片不能参与训练？

## Lesson 05 — Epoch, Batch, and Loss / Epoch、Batch 与损失

**中文：** 一个 epoch 表示完整学习一遍训练数据；batch 表示一次送入模型的图片数量；loss 衡量当前预测与标签的差距。冒烟测试只跑 1 epoch 验证链路，基线跑 30 epochs 学习缺陷模式。

**English:** An epoch is one complete pass through the training data, batch is the number of images processed together, and loss measures prediction error. Smoke uses one epoch for plumbing; baseline uses 30 epochs to learn patterns.

File / 文件: `configs/train-smoke.yaml`, `configs/train-baseline.yaml`

Command / 命令: `uv run python -m urbanvision_risk.detection.train --profile smoke --run-name smoke-test-001`

Expected / 预期: one epoch completes and both `best.pt` and `last.pt` are saved.

**复习问题 / Review question:** Why is high accuracy not required from the smoke run? / 为什么冒烟测试不要求高准确率？

## Lesson 06 — Precision, Recall, F1, and mAP / Precision、Recall、F1 与 mAP

**中文：** Precision 关注模型报出的缺陷有多少正确；Recall 关注真实缺陷有多少被找到；F1 平衡两者；mAP 同时考虑类别、置信度排序和框的位置质量。`mAP50-95` 比 `mAP50` 更严格。

**English:** Precision asks how many reported defects are correct, recall asks how many real defects are found, F1 balances both, and mAP evaluates ranked confidence and box localization. `mAP50-95` is stricter than `mAP50`.

File / 文件: `src/urbanvision_risk/detection/evaluate.py`

Command / 命令: `uv run python -m urbanvision_risk.detection.evaluate --run-name china-baseline-001`

Expected / 预期: real overall and per-class metrics in `evaluation.json`.

**复习问题 / Review question:** Can a model have high precision but low recall? / 模型能否 Precision 高但 Recall 低？

## Lesson 07 — Apple MPS and the Mac GPU / Apple MPS 与 Mac GPU

**中文：** MPS 是 PyTorch 通过 Apple Metal 使用 GPU 的后端。环境体检不仅检查布尔标志，还实际在 `mps` 上执行张量运算。项目不静默切换 CPU，因为这会让训练时间产生巨大变化。

**English:** MPS is PyTorch's Apple Metal GPU backend. The checker performs a real tensor operation, not only flag checks. Silent CPU fallback is disabled because it would radically change training time.

File / 文件: `src/urbanvision_risk/environment.py`

Command / 命令: `uv run python -m urbanvision_risk.environment`

Expected / 预期: Python, root, PyTorch, and MPS all report PASS.

**复习问题 / Review question:** Why does the checker run a real tensor operation? / 为什么体检要执行真实张量运算？

## Lesson 08 — Reading the First Experiment / 阅读第一次实验结果

**中文：** `best.pt` 是验证表现最好的权重，`last.pt` 是最后一轮权重。`training_summary.json` 保存代码提交、数据摘要、参数和版本；`evaluation.json` 保存留出测试指标；预测 JSON 保存每个框的类别、置信度和像素坐标。

**English:** `best.pt` is the best validation checkpoint and `last.pt` is the final epoch. `training_summary.json` records code, data digest, parameters, and versions; `evaluation.json` stores held-out metrics; prediction JSON stores each class, confidence, and pixel box.

File / 文件: `results/README.md`

Command / 命令: `uv run python -m urbanvision_risk.detection.predict --run-name china-baseline-001 --source data/processed/rdd2022-china-motorbike/images/test`

Expected / 预期: an annotated JPG and matching JSON, including an honest empty list when nothing exceeds the threshold.

**复习问题 / Review question:** Why must an empty detection result remain valid? / 为什么空检测结果也必须是合法结果？

## Lesson 09 — Explainable Maintenance Priority / 可解释维护优先级

**中文：** v0.2 不重新运行模型，而是读取预测 JSON。它分别计算每类缺陷的数量因子和检测框并集覆盖因子，再按固定权重生成 0–100 的维护复核优先级。置信度只描述证据质量，不进入风险公式。

**English:** v0.2 does not rerun the model; it reads prediction JSON. It combines each class's capped count factor and exact box-union coverage factor into a 0–100 maintenance-review priority. Confidence reports evidence quality and does not enter the risk formula.

File / 文件: `src/urbanvision_risk/risk/score.py`, `configs/risk-v0.2.yaml`

Command / 命令: `uv run python -m urbanvision_risk.risk.assess --run-name china-baseline-001 --prediction-name prediction-001 --output-name risk-001`

Expected / 预期: 198 per-image risk JSON files, a deterministic ranking CSV, a batch summary, and the resolved configuration; no YOLO inference log.

**复习问题 / Review question:** Why must confidence remain separate from risk_score? / 为什么置信度必须与 risk_score 分开？
