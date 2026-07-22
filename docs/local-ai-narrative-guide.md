# UrbanVision-Risk v1.2 Local AI Narrative / 本地 AI 巡检说明

## What this milestone adds / 本阶段新增内容

**English:** The detector and risk engine produce structured JSON. v1.2 converts only a small, filtered subset of that JSON into a bilingual inspection narrative. It prefers a local Ollama model and automatically falls back to a deterministic template when Ollama is absent, stopped, too slow, or returns invalid JSON.

**中文：** 检测器和风险引擎先生成结构化 JSON。v1.2 只选择其中一小部分经过过滤的数据，生成双语巡检说明。它优先使用本机 Ollama；当 Ollama 未安装、未启动、超时或返回非法 JSON 时，自动降级到确定性模板。

```text
prediction.json + risk.json
            ↓
privacy filter / 隐私过滤
            ↓
counts · coverage · confidence · audit flags
数量 · 覆盖率 · 置信度 · 审计标记
            ↓
local Ollama/Qwen ── unavailable/invalid ──→ audited template
本地 Ollama/Qwen ── 不可用或非法 ────────→ 审计模板
            ↓
narrative.json
```

## Important beginner concept / 初学者需要理解的概念

An LLM does not inspect the road image in this stage. YOLO already performed visual detection. The LLM only rewrites verified structured facts into readable Chinese and English. It is a **writing layer**, not another safety assessor.

本阶段的大语言模型不会查看道路原图。视觉检测已经由 YOLO 完成；LLM 只把经过验证的结构化事实改写成易读的中英文。它是一个**文字表达层**，不是新的安全鉴定器。

## Start the app / 启动应用

The ordinary command enables automatic local behavior:

普通启动命令会启用自动本地模式：

```bash
uv run python -m urbanvision_risk.app.serve --run-name china-repair-mps-003
```

After an image inspection finishes, click **Generate locally / 生成本地说明**.

图片巡检完成后，点击 **生成本地说明**。

- If Ollama and `qwen3:4b` are available at `127.0.0.1:11434`, the result records `generator.mode = "ollama"`.
- 如果 `127.0.0.1:11434` 上存在 Ollama 和 `qwen3:4b`，结果会记录 `generator.mode = "ollama"`。
- Otherwise the result records `generator.mode = "template"` and a machine-readable fallback reason.
- 否则结果记录 `generator.mode = "template"` 和机器可读的降级原因。

Ollama is optional. The current project remains runnable and testable without installing it.

Ollama 是可选项。即使不安装，当前项目仍然可以完整运行和测试。

## Force deterministic template mode / 强制确定性模板模式

Use this when you want guaranteed repeatability or do not want any localhost model request:

如果你需要完全可重复的文字，或者不希望发出任何本机模型请求，使用：

```bash
uv run python -m urbanvision_risk.app.serve \
  --run-name china-repair-mps-003 \
  --narrative-mode template
```

The template is generated from tested rules. It does not pretend to be LLM output.

模板由经过测试的规则生成，不会伪装成 LLM 输出。

## Use an already installed local Ollama model / 使用已经安装的本地 Ollama 模型

If Ollama is already installed, make sure its local service is running and that the selected model exists. Then start UrbanVision with the model name:

如果已经安装 Ollama，请确认本地服务正在运行且模型已经存在，然后把模型名称传给 UrbanVision：

```bash
uv run python -m urbanvision_risk.app.serve \
  --run-name china-repair-mps-003 \
  --ollama-model qwen3:4b \
  --ollama-timeout 30
```

The endpoint is fixed in code to `http://127.0.0.1:11434/api/generate`. A command-line option cannot redirect it to a cloud URL.

端点在代码中固定为 `http://127.0.0.1:11434/api/generate`，命令行参数不能把它重定向到云端。

## Privacy boundary / 隐私边界

The narrative prompt may contain only:

说明提示词只允许包含：

- counts for D00, D10, D20, D40, and Repair / 五类数量；
- union bounding-box coverage / 检测框联合覆盖率；
- audited risk value and decision status / 审计分值和决策状态；
- evidence quality and mean confidence / 证据质量和平均置信度；
- audit-flag codes / 审计标记代码。

It never contains:

它绝不包含：

- source or annotated image bytes / 原图或标注图内容；
- original filename / 原文件名；
- absolute local paths / 本机绝对路径；
- browser history, account data, or credentials / 浏览历史、账户数据或凭据；
- free-form user text / 用户自由文本。

Generated text is rendered with browser `textContent`, not HTML, so model output cannot inject executable markup into the page.

生成文字使用浏览器 `textContent` 渲染，而不是 HTML，因此模型输出不能向页面注入可执行标记。

## Saved narrative contract / 保存格式

The first successful click creates one immutable file:

第一次成功点击会创建一个不可覆盖文件：

```text
results/inspections/<run>/<inspection-id>/narrative.json
```

Important fields:

重要字段：

| Field / 字段 | Meaning / 含义 |
|---|---|
| `schema_version` | Narrative data contract version / 说明数据契约版本 |
| `generator.mode` | `ollama` or `template` / 使用 Ollama 或模板 |
| `generator.fallback_reason` | Why the template was selected / 为什么发生模板降级 |
| `summary` | Bilingual concise conclusion / 双语简要结论 |
| `observations` | Bilingual facts derived from detections / 来自检测的双语事实 |
| `actions` | Bilingual human-review actions / 双语人工复核动作 |
| `limitation` | Existing engineering safety boundary / 既有工程安全边界 |
| `source_*_sha256` | Digests tying the narrative to prediction and risk JSON / 绑定预测与风险 JSON 的摘要 |

Repeated requests reuse the existing file instead of silently changing the wording.

重复请求会复用已有文件，不会静默改变文字。

## Safety boundary / 安全边界

The narrative is not a certified engineering report, road-safety verdict, repair design, cost estimate, or traffic-closure decision. It cannot infer real crack length, depth, material condition, structural capacity, or traffic exposure from one image. Qualified people make final decisions.

本说明不是认证工程报告、道路安全结论、维修设计、成本估算或交通封闭决策。它不能从单张图片推断真实裂缝长度、深度、材料状况、结构承载力或交通暴露。最终决定必须由具备资质的人员作出。
