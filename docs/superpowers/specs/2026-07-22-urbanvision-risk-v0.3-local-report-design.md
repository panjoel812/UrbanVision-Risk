# UrbanVision-Risk v0.3 Local Report Design

## Goal / 目标

Generate a bilingual, interactive, fully offline HTML dashboard from an existing v0.2 risk batch. The report helps a human inspect and prioritize images; it never claims to determine road safety.

从已有 v0.2 风险批次生成中英双语、可交互、完全离线的 HTML 仪表板。报告帮助人工检查和排序图片，绝不声称能够判定道路安全。

## Learner command / 学习者命令

```bash
uv run python -m urbanvision_risk.reporting.build \
  --run-name china-baseline-001 \
  --prediction-name prediction-001 \
  --risk-name risk-001 \
  --output-name report-001
```

Output / 输出：

```text
results/reports/<run>/<prediction>/<risk>/<report>/
├── index.html
└── report-manifest.json
```

`index.html` opens directly from Finder or a `file://` URL. It uses no web server, CDN, fetch request, cloud API, or model inference. Annotated images remain in the existing prediction directory and are referenced with relative local paths.

`index.html` 可从 Finder 或 `file://` 直接打开，不需要 Web 服务器、CDN、fetch 请求、云 API 或模型推理。标注图片继续保存在已有预测目录中，报告使用本地相对路径引用。

## Architecture / 架构

1. `reporting.build` resolves and validates the risk batch, ranking CSV, per-image JSON, and annotated-image paths.
2. It constructs a reduced display payload containing only fields needed by the report.
3. `reporting.dashboard` renders one self-contained HTML document with inline CSS, JavaScript, and JSON data.
4. Output is created only after all inputs pass validation. Existing output returns `E204` and is never overwritten.
5. The report manifest records source paths and SHA-256 digests for the summary, ranking, resolved risk config, and generated HTML.

1. `reporting.build` 解析并验证风险批次、排序 CSV、单图 JSON 和标注图片路径；
2. 构造只包含展示所需字段的精简数据；
3. `reporting.dashboard` 生成内嵌 CSS、JavaScript 和 JSON 数据的单一 HTML；
4. 全部输入验证通过后才创建输出；已有输出返回 `E204`，绝不覆盖；
5. 报告清单记录摘要、排序、风险配置和 HTML 的路径与 SHA-256。

## Dashboard / 仪表板

The first view contains:

- image count, mean score, maximum score, and count requiring moderate-or-higher review;
- risk-level and evidence-quality distribution bars;
- a persistent bilingual limitation: maintenance-review priority, not a safety verdict;
- language toggle, filename search, risk/evidence filters, and sort control;
- a compact ranked table;
- one selected-image detail with the annotated image, score, evidence statistics, flags, recommendation, and four class contributions.

首屏包含：图片数、平均分、最高分、中等及以上复核数量；风险等级与证据质量分布；永久显示的双语安全边界；语言切换、文件名搜索、风险/证据筛选与排序；紧凑排名表；以及一个选中图片的标注图、分数、证据、标记、建议和四类贡献详情。

Interactions are presentation-only and run in the browser. No input data or results are modified.

所有交互只改变浏览器中的展示状态，不修改输入或结果。

## Validation / 验证

The builder rejects the batch before creating output when:

- the risk directory or any required root artifact is missing;
- JSON or CSV cannot be parsed;
- summary `file_count`, ranking rows, and per-image files disagree;
- ranks are not consecutive, filenames differ, or ranking scores/levels disagree with per-image JSON;
- a required evidence, class-breakdown, recommendation, or limitation field is missing;
- the matching annotated JPG does not exist.

生成器会在创建输出前拒绝以下情况：风险目录或根文件缺失；JSON/CSV 无法解析；摘要数量、排名行和单图文件不一致；排名不连续、文件名不同或分数/等级不一致；证据、类别贡献、建议或限制字段缺失；对应标注 JPG 不存在。

## Errors / 错误

| Code | Meaning / 含义 | Recovery / 恢复 |
|---|---|---|
| `E201` | Risk input directory/artifact missing / 风险输入目录或文件不存在 | Check names; run v0.2 first / 检查名称，先运行 v0.2 |
| `E204` | Report output exists / 报告输出已存在 | Keep it and use a new output name / 保留结果并换新名称 |
| `E501` | Risk artifacts are malformed or inconsistent / 风险文件损坏或互相矛盾 | Inspect or regenerate the named risk batch / 检查或重新生成风险批次 |
| `E502` | Report write failed / 报告写入失败 | Fix disk/permissions; preserve partial output and use a new name when necessary / 修复磁盘或权限；保留半成品并在需要时换新名称 |

All errors and recovery instructions are bilingual `ProjectError` messages.

所有错误和恢复说明均使用双语 `ProjectError`。

## Safety and scope / 安全与范围

- The report is a visualization of v0.2 outputs, not a new model or score.
- It does not change risk scores, evidence labels, predictions, or images.
- It has no GIS, physical road-area scale, traffic exposure, pavement history, or certified engineering calibration.
- A human decides inspection, closure, and repair actions.
- Generated `results/reports/` remains Git-ignored.

- 报告只是 v0.2 输出的可视化，不是新模型或新分数；
- 不改变风险分数、证据等级、预测或图片；
- 不包含 GIS、真实道路面积尺度、交通暴露、路面历史或认证工程标定；
- 检查、封闭和维修由人工决定；
- 生成的 `results/reports/` 保持 Git 忽略。

## Acceptance / 验收

- unit/integration tests cover valid output, malformed input, missing image, and non-overwrite;
- generated HTML contains no external URL, `fetch`, XHR, WebSocket, or model/network import;
- browser QA verifies direct file opening, language switching, filtering, sorting, row selection, image loading, and responsive layout;
- real `risk-001` acceptance produces 198 rows and loads its highest-ranked annotated image;
- `report-001` remains unused until the learner runs the documented command.
