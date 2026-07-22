# UrbanVision-Risk v1.1 Local App / 本地应用指南

## Finished product / 最终产品

**English:** v1.1 runs the five-class corrected YOLO model locally on Apple MPS. Large images receive both full-image inference and overlapping 1024-pixel tile inference. The fifth `Repair` class makes previously repaired pavement visible but never silently treats a repair as damage.

**中文：** v1.1 在 Apple MPS 上运行修正后的五类 YOLO 模型。大图会同时进行全图推理与 1024 像素重叠分块推理。第五类 `Repair` 让历史修补区域可见，但绝不会悄悄把修补区域当成缺陷计分。

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

## What happens after upload / 上传后发生什么

```text
Road image / 道路图片
        ↓
Input validation / 输入验证
        ↓
YOLO + Apple MPS full/tiled inference / 全图与分块本地推理
        ↓
D00 · D10 · D20 · D40 scored damage / 计分缺陷
Repair auxiliary observation / 历史修补辅助观察
        ↓
Versioned risk engine / 版本化风险引擎
        ↓
Bilingual result + local audit files / 双语结果与本地审计文件
```

The model is loaded once when the server starts. Each upload is normalized for EXIF orientation and converted to RGB. Images larger than 1280 pixels on either axis receive a full-image pass plus overlapping 1024 × 1024 tiles; class-aware non-maximum suppression merges duplicate boxes. The four damage classes enter the tested `risk-v0.2.0` formula; `Repair` remains an unscored auxiliary observation.

服务启动时只加载一次模型。每次上传都会规范化 EXIF 方向并转换成 RGB。任一边大于 1280 像素时，会同时运行全图与 1024 × 1024 重叠分块，再用分类非极大值抑制合并重复框。四类缺陷进入经过测试的 `risk-v0.2.0` 公式；`Repair` 始终是零分辅助观察项。

## What the page shows / 页面显示内容

- annotated image and detected bounding boxes / 标注图和检测框；
- D00 longitudinal, D10 transverse, D20 alligator cracks, and D40 potholes / 四类道路缺陷；
- Repair previously repaired area as an unscored observation / Repair 历史修补区域作为不计分观察项；
- 0–100 maintenance-review priority and level / 0–100 维护复核优先级与等级；
- evidence quality, mean/minimum confidence, and audit flags / 证据质量、平均/最低置信度和审计标记；
- count, coverage, and score contribution for every class / 每类数量、覆盖率与分数贡献；
- bilingual recommendation and safety limitation / 双语建议与安全限制；
- immutable local inspection ID / 不可覆盖的本地巡检编号。

## Uncertain evidence is not low risk / 不确定证据不等于低风险

When none of the four scored damage classes is detected, or when mean detection confidence is low, the page withholds the score and displays **Human review required / 需要人工复核**. The numeric formula remains in `risk.json` as an audit value. This is intentional: a model can miss an obvious defect, and uncertain bounding boxes are not evidence of a safe road.

四类计分缺陷均未检测到，或平均检测置信度较低时，页面不会展示“低优先级”，而是显示 **需要人工复核**；公式数值只在 `risk.json` 中作为审计值保留。这是刻意的安全设计：模型可能漏掉肉眼明显的缺陷，不确定的检测框也不能证明道路安全。

## Five saved artifacts / 五份保存文件

Every successful upload creates a new directory:

每次成功上传都会创建新目录：

```text
results/inspections/china-repair-mps-003/<inspection-id>/
├── source.jpg
├── annotated.jpg
├── prediction.json
├── risk.json
└── inspection-manifest.json
```

- `source.jpg`: normalized local copy / 规范化本地副本；
- `annotated.jpg`: model boxes and labels / 模型检测框与标签；
- `prediction.json`: dimensions, detections, confidence, and counts / 尺寸、检测、置信度与数量；
- `risk.json`: formula, priority, evidence, flags, recommendation, and limitation / 公式、优先级、证据、标记、建议与限制；
- `inspection-manifest.json`: timestamp, model/config identity, and SHA-256 digests / 时间、模型/配置身份和 SHA-256。

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
| `E601` | File type, byte size, pixels, or decoding is invalid. Use a supported smaller image. | 文件类型、大小、像素或解码非法。使用受支持的小型图片。 |
| `E602` | Local writing failed. Preserve partial output, check disk/permissions, and upload again. | 本地写入失败。保留半成品，检查磁盘/权限后重新上传。 |

## Safety boundary / 安全边界

Maintenance-review priority, not a road-safety verdict. A low or zero score does not prove the road is safe. The system has no physical road scale, traffic exposure, pavement history, GIS context, or certified engineering-severity calibration. It does not replace a certified engineering safety assessment. Humans decide inspection, closure, and repair.

维护复核优先级，不是道路安全判定。低分或零分不能证明道路安全。系统没有真实道路尺度、交通暴露、路面历史、GIS 背景或经过认证的工程严重度标定，不能替代经过认证的工程安全鉴定。检查、封闭和维修由人工决定。
