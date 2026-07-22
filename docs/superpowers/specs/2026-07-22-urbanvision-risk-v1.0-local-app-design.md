# UrbanVision-Risk v1.0 Local App Design

## Goal / 目标

Complete the original v1.0 product loop on one MacBook: select one road image in a
local browser, run the trained YOLO checkpoint on MPS, calculate the existing
versioned maintenance-priority score, and show a bilingual result with the annotated
image and engineering limitations.

在一台 MacBook 上完成最初约定的 v1.0 产品闭环：在本地浏览器选择一张道路图片，
用已有 YOLO 检查点通过 MPS 推理，计算现有版本化维护优先级分数，并显示带标注图和
工程限制的双语结果。

## Learner command / 学习者命令

```bash
uv run python -m urbanvision_risk.app.serve --run-name china-baseline-001
```

The server binds to `127.0.0.1` by default and opens no cloud connection. The user
visits `http://127.0.0.1:8000`, uploads JPEG, PNG, or WebP, and receives one inspection.

服务默认只监听 `127.0.0.1`，不连接云服务。用户访问 `http://127.0.0.1:8000`，
上传 JPEG、PNG 或 WebP，并得到一次巡检结果。

## Architecture / 架构

1. `app.service.LocalInspectionService` validates the checkpoint, risk configuration,
   confidence, file type, byte size, decoded dimensions, and pixel count.
2. The model is loaded once. A process lock serializes MPS inference.
3. The service normalizes EXIF orientation, predicts from an in-memory RGB array,
   validates the prediction schema, and calls the existing `risk.score_prediction`.
4. A successful inspection is written once to
   `results/inspections/<run>/<inspection-id>/` with normalized source JPG, annotated
   JPG, prediction JSON, risk JSON, and a SHA-256 manifest.
5. `app.api.create_app` exposes the local HTML page, health metadata, one upload
   endpoint, and a traversal-safe annotated-image endpoint.
6. `app.serve` loads the service before starting Uvicorn and binds only to loopback.

1. `app.service.LocalInspectionService` 验证检查点、风险配置、置信度、文件类型、
   字节大小、解码尺寸和像素数量；
2. 模型只加载一次，并使用进程锁串行执行 MPS 推理；
3. 服务规范化 EXIF 方向，从内存 RGB 数组推理，验证预测结构，再调用已有
   `risk.score_prediction`；
4. 成功巡检只写入一次 `results/inspections/<run>/<inspection-id>/`，包括规范化原图、
   标注图、预测 JSON、风险 JSON 和 SHA-256 清单；
5. `app.api.create_app` 提供本地 HTML、健康信息、上传接口和防路径穿越的标注图接口；
6. `app.serve` 在启动 Uvicorn 前加载服务，并且只允许回环地址。

## API contract / API 契约

### `GET /api/health`

Returns the application version, run name, checkpoint name, device, confidence, and
fully-local status. It does not expose an absolute filesystem path.

返回应用版本、运行名称、检查点名称、设备、置信度和完全本地状态，不暴露绝对路径。

### `POST /api/inspect`

Accepts exactly one `image` multipart field. Success returns:

- inspection ID and annotated-image URL;
- image dimensions and four class counts;
- detections with class, confidence, and bounding box;
- risk score, maintenance-priority level, evidence quality, recommendation, audit
  flags, class breakdown, and safety limitation.

只接受一个名为 `image` 的 multipart 字段。成功响应包含巡检 ID、标注图 URL、图片尺寸、
四类数量、检测框、风险分数、维护优先级、证据质量、建议、审计标记、类别贡献和安全限制。

Project errors become structured bilingual JSON and appropriate 4xx/5xx status codes.

项目错误转换成结构化双语 JSON 和适当的 4xx/5xx 状态码。

## Input and privacy boundary / 输入与隐私边界

- accepted MIME types: `image/jpeg`, `image/png`, and `image/webp`;
- maximum upload size: 15 MiB;
- maximum decoded image area: 40 megapixels;
- filename is display-only and never used as a filesystem path;
- no remote URL input, CDN, telemetry, analytics, cloud API, or external model call;
- generated output is ignored by Git and is never silently overwritten;
- the server accepts loopback hosts only.

- 接受 JPEG、PNG、WebP；最大上传 15 MiB；最大解码面积 4000 万像素；
- 原文件名只用于显示，绝不作为文件路径；
- 不接受远程 URL，不使用 CDN、遥测、分析、云 API 或外部模型调用；
- 生成结果由 Git 忽略且绝不静默覆盖；服务只接受回环地址。

## Dashboard / 仪表板

The responsive page provides a drag/click upload area, local preview, bilingual switch,
model status, progress/error state, annotated result, 0–100 score gauge, priority and
evidence badges, class counts, contribution bars, detections, recommendation, and a
persistent safety boundary. Controls work with keyboard focus and reduced motion.

响应式页面提供拖放/点击上传、本地预览、中英切换、模型状态、进度/错误状态、标注结果、
0–100 分数仪表、优先级与证据标记、类别数量、贡献条、检测结果、建议和永久安全边界；
控件支持键盘焦点和减少动态效果。

## Errors / 错误

| Code | Meaning / 含义 |
|---|---|
| `E201` | checkpoint or risk config missing / 检查点或风险配置不存在 |
| `E204` | generated inspection ID already exists / 巡检 ID 已存在 |
| `E301` | model loading or inference failed / 模型加载或推理失败 |
| `E302` | run, confidence, host, or port invalid / 运行名称、置信度、地址或端口非法 |
| `E601` | upload MIME, size, or decoded image invalid / 上传类型、大小或图片解码非法 |
| `E602` | inspection artifact write failed / 巡检结果写入失败 |

## Acceptance / 验收

- service tests use a fake model to prove prediction, risk scoring, persistence,
  digests, non-overwrite, and input validation;
- API tests prove the page, health contract, upload contract, bilingual errors, and
  traversal-safe artifact serving;
- documentation tests prove one-command startup, offline/privacy language, and safety
  boundary;
- the full existing suite remains green;
- one real RDD2022 test image completes through YOLO on MPS and produces all five
  inspection artifacts;
- browser QA verifies desktop and mobile layouts, bilingual switching, upload,
  annotated-image loading, and absence of console errors.

