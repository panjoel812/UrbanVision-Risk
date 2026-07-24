# UrbanVision-Risk v2.0 Reliability-Aware Local App / 可靠性本地应用指南

## Finished product / 最终产品

**English:** v2.0 runs a three-view transform-consensus detector locally on Apple MPS. It associates boxes across 640, 1280, and horizontally mirrored views; fuses supported boxes; quantifies localization stability and uncertainty; and ranks inspections for active learning. Large images retain overlapping 1024-pixel spatial inference. The bilingual Ollama/template narrative remains optional.

**中文：** v2.0 在 Apple MPS 上运行三视图变换共识检测：关联 640、1280 和水平镜像视图中的检测框，融合得到共识框，量化定位稳定性与不确定性，并为主动学习排列巡检样本。大图继续使用 1024 像素重叠空间推理；双语 Ollama/模板说明仍为可选层。

It uses no AWS, Azure, Google Cloud, paid API, remote model, CDN, analytics, or telemetry. After dependencies and the model are present, the complete workflow can run without internet access.

它不使用 AWS、Azure、Google Cloud、付费 API、远程模型、CDN、分析或遥测。依赖和模型准备完成后，完整流程可以断网运行。

## Start everything with one command / 一条命令启动全部功能

From the preserved project worktree / 在保留的项目工作树中运行：

```bash
uv run python -m urbanvision_risk.app.serve --run-name china-repair-mps-003
```

Expected terminal message / 预期终端信息：

```text
[PASS] 本地应用已就绪 / Local app ready: http://127.0.0.1:8000
[INFO] 按 Control+C 停止 / Press Control+C to stop
```

Open `http://127.0.0.1:8000` in a browser. Keep the terminal window running while you use the app. Press `Control+C` in that terminal when finished.

在浏览器打开 `http://127.0.0.1:8000`。使用应用期间不要关闭终端；完成后在该终端按 `Control+C`。

## Unified inspection and metrology / 巡检与量测合一

Open `http://127.0.0.1:8000`. Detection, reliability evidence, editable mask review, calibration, metrology, material planning, and longitudinal change now live on one page. The old `/metrology` address returns the same page only for bookmark compatibility.

打开 `http://127.0.0.1:8000`。检测、可靠性证据、可编辑掩膜复核、标定、量测、材料计划和多期变化现在全部位于同一页面；旧 `/metrology` 地址只为兼容书签而返回相同页面。

The browser workflow includes:

- deterministic built-in calibrated demo / 确定性内置标定 Demo；
- original-resolution mask brush, eraser, undo, and clear / 原分辨率掩膜画笔、橡皮、撤销和清空；
- pixel-only, manual `TL → TR → BR → BL`, and automatic ArUco modes / 仅像素、手动四点和 ArUco 自动模式；
- physical width, height, unit, rectification resolution, corner sigma, Monte Carlo sample count, and boundary sensitivity controls / 真实宽高、单位、矫正分辨率、点位 sigma、Monte Carlo 样本数和边界敏感性设置；
- overlay, rectified overlay, width heatmap, skeleton, topology, physical geometry, interval evidence, and complete `measurement.json` / 叠加图、矫正图、宽度热图、骨架、拓扑、真实几何量、区间证据和完整 JSON；
- immutable local output under `results/metrology/<run-id>/` / 保存到不可覆盖的本地量测目录。

One upload automatically starts transform-consensus detection and the independent local crack proposal in parallel. The proposal is painted green and immediately produces a pixel-only geometry draft. The algorithm also repeats its decision at sensitivity −0.15 and +0.15; unstable pixels appear as a yellow review layer. Version 4.4 groups yellow pixels into connected components, ranks up to 24 targets by disagreement size and overlap with the nominal proposal, and provides previous/next inspection controls. Marking a target as inspected changes review progress, not the mask. Sensitivity changes rerun the proposal, ranked queue, and draft. Saving creates an immutable `human_reviewed` run containing the inspected IDs and both count-based and priority-weighted completion. Yellow means parameter disagreement, not a calibrated error probability. The browser never turns detector boxes into a mask.

上传一次会并行自动启动变换共识检测和独立的本地裂缝建议算法；绿色底稿画出后立即生成仅像素几何草稿。算法还会在当前灵敏度的 −0.15 与 +0.15 处重复计算，不稳定像素显示为黄色复核层。v4.4 把黄色像素拆成连通区域，按分歧规模和当前候选重叠影响排序，最多提供 24 项“上一个/下一个”检查目标。标记“已检查”只改变复核进度，不会改变掩膜。保存后，`human_reviewed` 记录包含已检查编号、数量完成率和优先影响覆盖率。黄色只代表参数分歧，不是校准后的错误概率；网页也不会把检测框直接转换成掩膜。

## What happens after upload / 上传后发生什么

```text
Road image / 道路图片
        ↓
Input validation / 输入验证
        ↓
YOLO + Apple MPS multi-view inference / 多视图本地推理
        ↓
Cross-view association + weighted box fusion / 跨视图关联与加权框融合
        ↓
Stability + uncertainty + active-learning priority / 稳定性、不确定性与主动学习优先级
        ↓
D00 · D10 · D20 · D40 scored damage / 计分缺陷
Repair auxiliary observation / 历史修补辅助观察
        ↓
Versioned risk engine / 版本化风险引擎
        ↓
Bilingual result + optional local narrative / 双语结果与可选本地说明
        ↓
Immutable local audit files / 不可变本地审计文件
```

The model is loaded once when the server starts. Each small image runs through native 640, native 1280, and horizontally mirrored 1280 views at a candidate confidence floor. Class-aware IoU association groups corresponding detections, confidence-weighted fusion estimates one box, and a conservative mean confidence replaces the most optimistic score. A cluster needs support from at least two views before it enters `risk-v0.2.0`. Images larger than 1280 pixels retain full-image plus overlapping 1024 × 1024 spatial inference.

服务启动时只加载一次模型。每张小图会以原图 640、原图 1280 和水平镜像 1280 三种视图运行；分类感知 IoU 关联聚合同一缺陷，置信度加权融合定位框，并以保守平均置信度替代最乐观的单次分数。一个检测簇至少得到两个视图支持后才能进入 `risk-v0.2.0`。任一边大于 1280 像素时，保留全图与 1024 × 1024 重叠空间推理。

## What the page shows / 页面显示内容

- annotated image and detected bounding boxes / 标注图和检测框；
- D00 longitudinal, D10 transverse, D20 alligator cracks, and D40 potholes / 四类道路缺陷；
- Repair previously repaired area as an unscored observation / Repair 历史修补区域作为不计分观察项；
- 0–100 maintenance-review priority and level / 0–100 维护复核优先级与等级；
- evidence quality, mean/minimum confidence, and audit flags / 证据质量、平均/最低置信度和审计标记；
- multi-view support, localization stability, uncertainty, and active-learning priority / 多视图支持、定位稳定性、不确定性与主动学习优先级；
- count, coverage, and score contribution for every class / 每类数量、覆盖率与分数贡献；
- bilingual recommendation and safety limitation / 双语建议与安全限制；
- optional Ollama/Qwen or audited-template narrative / 可选 Ollama/Qwen 或审计模板说明；
- immutable local inspection ID / 不可覆盖的本地巡检编号。

## Uncertain evidence is not low risk / 不确定证据不等于低风险

When none of the four scored damage classes is detected, or when mean detection confidence is low, the page withholds the score and displays **Human review required / 需要人工复核**. The numeric formula remains in `risk.json` as an audit value. This is intentional: a model can miss an obvious defect, and uncertain bounding boxes are not evidence of a safe road.

四类计分缺陷均未检测到，或平均检测置信度较低时，页面不会展示“低优先级”，而是显示 **需要人工复核**；公式数值只在 `risk.json` 中作为审计值保留。这是刻意的安全设计：模型可能漏掉肉眼明显的缺陷，不确定的检测框也不能证明道路安全。

## Five core artifacts plus one optional narrative / 五份核心文件和一份可选说明

Every successful upload creates a new directory:

每次成功上传都会创建新目录：

```text
results/inspections/china-repair-mps-003/<inspection-id>/
├── source.jpg
├── annotated.jpg
├── prediction.json
├── reliability.json
├── risk.json
├── inspection-manifest.json
└── narrative.json              # after Generate locally / 点击生成后出现
```

- `source.jpg`: normalized local copy / 规范化本地副本；
- `annotated.jpg`: model boxes and labels / 模型检测框与标签；
- `reliability.json`: view-level consensus clusters, uncertainty, stability, and active-learning evidence / 视图级共识簇、不确定性、稳定性与主动学习证据；
- `prediction.json`: dimensions, detections, confidence, and counts / 尺寸、检测、置信度与数量；
- `risk.json`: formula, priority, evidence, flags, recommendation, and limitation / 公式、优先级、证据、标记、建议与限制；
- `inspection-manifest.json`: timestamp, model/config identity, and SHA-256 digests / 时间、模型/配置身份和 SHA-256。
- `narrative.json`: immutable bilingual summary, observations, actions, generator mode, and source digests / 不可变双语摘要、观察、动作、生成模式和来源摘要。

Existing directories are never silently overwritten.

已有目录绝不被静默覆盖。

## Local privacy and input limits / 本地隐私与输入限制

- The server accepts only `127.0.0.1`, `localhost`, or `::1` / 服务只允许本机回环地址；
- JPEG, PNG, and WebP only / 只接受 JPEG、PNG 和 WebP；
- maximum compressed upload: 15 MiB / 最大上传大小 15 MiB；
- maximum decoded area: 40 megapixels / 最大解码面积 4000 万像素；
- filenames are never used as filesystem paths / 原文件名绝不作为文件路径；
- browser security headers block remote connections and framing / 浏览器安全头阻止远程连接和嵌套框架。

## Error recovery / 错误恢复

| Code | English | 中文 |
|---|---|---|
| `E201` | Model, config, or inspection artifact is missing. Check the run and checkpoint. | 模型、配置或巡检文件不存在。检查运行名称和检查点。 |
| `E204` | An inspection ID already exists. Keep it and upload again for a new ID. | 巡检编号已存在。保留结果并重新上传生成新编号。 |
| `E301` | The model failed to load or infer. Check MPS, `best.pt`, and the image. | 模型加载或推理失败。检查 MPS、`best.pt` 和图片。 |
| `E302` | Run name, confidence, host, or port is invalid. Use the documented defaults. | 运行名称、置信度、地址或端口非法。使用文档默认值。 |
| `E603` | The selected port is already in use. Stop the old service or append `--port 8001`. | 端口已被占用。停止旧服务，或在命令末尾添加 `--port 8001`。 |
| `E601` | File type, byte size, pixels, or decoding is invalid. Use a supported smaller image. | 文件类型、大小、像素或解码非法。使用受支持的小型图片。 |
| `E602` | Local writing failed. Preserve partial output, check disk/permissions, and upload again. | 本地写入失败。保留半成品，检查磁盘/权限后重新上传。 |

## Safety boundary / 安全边界

Maintenance-review priority, not a road-safety verdict. A low or zero score does not prove the road is safe. The system has no physical road scale, traffic exposure, pavement history, GIS context, or certified engineering-severity calibration. It does not replace a certified engineering safety assessment. Humans decide inspection, closure, and repair.

维护复核优先级，不是道路安全判定。低分或零分不能证明道路安全。系统没有真实道路尺度、交通暴露、路面历史、GIS 背景或经过认证的工程严重度标定，不能替代经过认证的工程安全鉴定。检查、封闭和维修由人工决定。
