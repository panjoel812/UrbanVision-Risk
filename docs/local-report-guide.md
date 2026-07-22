# UrbanVision-Risk v0.3 Local Report / 本地报告指南

## What it does / 它做什么

**English:** v0.3 turns an existing v0.2 risk batch into an interactive bilingual dashboard. It validates the batch first, then writes one `index.html` and one provenance manifest. No server, network, CDN, or cloud API is required.

**中文：** v0.3 把已有 v0.2 风险批次转换成中英双语交互式仪表板。它先验证整个批次，再写入一个 `index.html` 和一个来源清单。不需要服务器、网络、CDN 或云 API。

The report does not run YOLO, recalculate risk, or modify predictions, images, scores, or evidence labels.

报告不会运行 YOLO、重新计算风险，也不会修改预测、图片、分数或证据等级。

## Build the learner report / 生成学习者报告

Run from the preserved project worktree / 从保留的项目工作树运行：

```bash
uv run python -m urbanvision_risk.reporting.build --run-name china-baseline-001 --prediction-name prediction-001 --risk-name risk-001 --output-name report-001
```

Expected output / 预期输出：

```text
results/reports/china-baseline-001/prediction-001/risk-001/report-001/
├── index.html
└── report-manifest.json
```

Open `index.html` in Finder or a browser. Keep it inside the project because its annotated-image links are local relative paths.

在 Finder 或浏览器中打开 `index.html`。请把报告保留在项目目录中，因为标注图片使用本地相对路径。

## What you can explore / 可以探索什么

- risk-level and evidence-quality distributions / 风险等级与证据质量分布；
- filename search and risk/evidence filters / 文件名搜索与风险、证据筛选；
- priority, filename, or confidence sorting / 按优先级、文件名或置信度排序；
- ranked images with score, evidence, and detection count / 包含分数、证据和检测数的图片排名；
- one selected annotated image with class counts, coverage, contributions, flags, and recommendation / 一个选中标注图片的类别数量、覆盖率、贡献、标记和建议；
- Chinese and English language switching / 中英文切换。

All interactions change only what the browser displays. They never edit the source files.

所有交互只改变浏览器显示内容，绝不编辑源文件。

## The two output files / 两个输出文件

### `index.html`

Contains the reduced report data, CSS, and JavaScript needed for offline exploration. It loads annotated JPG files from the matching local prediction directory and never sends data anywhere.

包含离线浏览所需的精简报告数据、CSS 和 JavaScript。它从匹配的本地预测目录加载标注 JPG，绝不向外发送数据。

### `report-manifest.json`

Records the source risk directory, batch identity, creation time, file count, and SHA-256 digests for the source summary, ranking CSV, resolved risk configuration, and generated HTML.

记录风险源目录、批次身份、创建时间、文件数，以及源摘要、排名 CSV、实际风险配置和生成 HTML 的 SHA-256。

## Error recovery / 错误恢复

| Code | English | 中文 |
|---|---|---|
| `E201` | Risk input is missing. Check the run, prediction, and risk names; run v0.2 first if necessary. | 风险输入不存在。检查运行、预测和风险名称；必要时先运行 v0.2。 |
| `E204` | The report output exists. Keep it and choose a new unused output name. | 报告输出已存在。保留它，并选择尚未使用的新输出名。 |
| `E501` | Source artifacts are malformed or inconsistent. Inspect or regenerate the named risk batch. | 源文件损坏或互相矛盾。检查或重新生成指定风险批次。 |
| `E502` | Directory creation or writing failed. Check disk space, the parent path, and permissions; preserve partial output and use a new name when necessary. | 目录创建或写入失败。检查磁盘空间、父路径和权限；保留半成品，并在需要时使用新名称。 |

Never edit risk JSON merely to make an error disappear. Regenerate the named upstream batch under a new name when its artifacts are inconsistent.

不要为了消除错误而手工编辑风险 JSON。上游文件不一致时，请使用新名称重新生成对应批次。

## Safety boundary / 安全边界

Maintenance-review priority, not a road-safety verdict. A zero or low score does not prove a road is safe. This report does not replace a certified engineering safety assessment. It has no physical road scale, GPS, traffic exposure, pavement history, or calibrated engineering-severity labels. Humans decide inspection, closure, and repair.

维护复核优先级，不是道路安全判定。零分或低分不能证明道路安全。本报告不能替代经过认证的工程安全鉴定。它没有真实道路尺度、GPS、交通暴露、路面历史或经过标定的工程严重度标签。检查、封闭和维修由人工决定。
