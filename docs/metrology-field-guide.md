# UrbanVision-Risk v5.8 Field Metrology / 现场裂缝量测

## What changed / 这次升级解决什么

**中文：** 检测框只能回答“模型认为哪里可能有缺陷”，不能回答裂缝有多长、多宽、是否分叉，也不能把像素直接当作毫米。v3.0 把巡检拆成可审计的证据链：

1. 原图与独立二值掩膜；
2. 单像素裂缝中心线；
3. 中心线图结构与拓扑统计；
4. 四点平面标定与透视矫正；
5. 真实单位的长度、宽度、面积和密度；
6. 标定点及掩膜边界扰动产生的敏感性区间。

**English:** A detection box says only where a model suspects damage. It does not provide crack length, width, branching, or a valid pixel-to-millimetre conversion. Version 3.0 turns inspection into an auditable evidence chain: source image and independent mask, one-pixel centerline, graph topology, four-point planar calibration, physical geometry, and perturbation-based sensitivity intervals.

The implementation intentionally refuses to convert a YOLO box into a crack mask. A box includes intact pavement and cannot support defensible width measurement.

本项目故意不把 YOLO 检测框伪装成裂缝掩膜。检测框包含大量完好路面，不能形成可信的宽度量测。

## Algorithms / 算法

### 1. Skeleton and graph / 骨架与图结构

The binary mask is reduced with Zhang-Suen thinning. Each remaining foreground pixel becomes a graph node. Horizontal and vertical edges have weight `1`; isolated diagonal edges have weight `sqrt(2)`. Redundant corner diagonals are removed so an L-shaped turn is not counted three times.

二值掩膜通过 Zhang-Suen 细化为单像素中心线。每个骨架像素成为图节点；水平和竖直边权重为 `1`，独立对角边权重为 `sqrt(2)`。程序会去掉拐角处重复的对角边，避免把一个 L 形拐弯重复计算。

The graph produces:

- connected components / 连通分量；
- endpoint and junction clusters / 端点和分叉簇；
- total geodesic network length / 测地网络总长；
- approximate longest main path and tortuosity / 近似最长主路径与曲折度；
- PCA principal orientation / PCA 主方向；
- box-counting dimension / 盒计数分形维数。

### 2. Width / 宽度

OpenCV's Euclidean distance transform estimates the distance from each crack pixel to the nearest background. Twice the distance sampled on the skeleton produces a local width distribution. The result contains minimum, p05, median, mean, p95, maximum, and standard deviation instead of hiding the crack behind one average.

OpenCV 欧氏距离变换计算每个裂缝像素到最近背景的距离，在骨架上取两倍距离得到局部宽度分布。系统输出最小值、p05、中位数、均值、p95、最大值和标准差，而不是只给一个容易误导的平均数。

### 3. Planar calibration / 平面标定

Four image points in semantic order `TL → TR → BR → BL` correspond to a measured physical rectangle. A homography maps this road plane into a fronto-parallel raster. Network edges are transformed directly into physical coordinates; widths are measured after nearest-neighbour mask rectification.

四个图像点按照 `TL → TR → BR → BL` 对应一个已测量真实宽高的矩形。单应性矩阵把道路平面变换为正视平面；中心线边直接映射到真实坐标计算长度，掩膜通过最近邻透视矫正后计算宽度。

Homography is a planar model. Curbs, bumps, camera parallax, and cracks outside the calibrated plane violate its assumptions. See the [OpenCV homography documentation](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html).

单应性只适用于单一平面。路缘石、隆起、视差以及标定平面外的裂缝会破坏假设。

### 4. Uncertainty / 不确定性

The software perturbs calibration corners with deterministic Gaussian noise and repeats physical-length calculation. It also erodes and dilates the source mask by a declared pixel radius. The resulting envelope is labelled:

`sensitivity_interval_not_certified_confidence_interval`

程序对四个标定点加入确定性高斯扰动，重复计算真实长度；同时按照声明的像素半径腐蚀和膨胀掩膜。这个区间是输入扰动敏感性分析，不是法定、统计认证或安全保证。

## Run the deterministic demo / 先运行确定性演示

### Browser demo / 网页 Demo

Start the unified local app:

启动巡检与精密量测合一的本地应用：

```bash
uv run python -m urbanvision_risk.app.serve --run-name china-repair-mps-003
```

Open `http://127.0.0.1:8000`, then select **Run calibrated demo / 运行完整标定 Demo**. The page displays the calibrated overlay, rectified plane, width heatmaps, topology, physical geometry, sensitivity interval, and complete JSON without requiring an upload.

打开 `http://127.0.0.1:8000`，点击 **Run calibrated demo / 运行完整标定 Demo**。无需上传图片，网页就会显示标定叠加图、矫正平面、宽度热图、拓扑、真实几何量、敏感性区间和完整 JSON。

For a real image, upload it once. Detection and the independent mask proposal start automatically in parallel, followed by an automatic pixel-only metrology draft. Review the green proposal and its yellow sensitivity-disagreement hotspots with the brush and eraser, choose a calibration mode, and save a reviewed measurement. The mask is exported at the source image's original resolution rather than the displayed CSS size.

对真实图片只需上传一次，检测与独立掩膜建议会并行自动启动，随后自动生成仅像素量测草稿。用画笔和橡皮复核绿色候选及黄色灵敏度分歧热点，选择标定模式，再保存人工复核量测。网页导出的掩膜保持原图分辨率，不会使用屏幕显示尺寸代替。

The circular cursor shows the exact brush diameter. Every brush move appears immediately as a green overlay; erasing removes both the mask alpha and the green overlay. The browser exports a transparent PNG, and the local service composites transparency onto black before thresholding, so unpainted pixels cannot accidentally become foreground.

圆形光标就是实际笔宽；拖动时绿色轨迹会立即显示，橡皮会同时清除掩膜透明度和绿色覆盖层。浏览器导出透明 PNG，本地服务先把透明区域合成到黑色背景再二值化，因此未绘制区域不会误变成前景。

## Human-in-the-loop mask proposal / 人机协同候选掩膜

After choosing a source image, the page automatically runs two complementary feature responses and a deterministic component selector on the Mac—there is no separate proposal button:

选择原图后，页面会自动在 Mac 上运行两个互补特征响应和一个确定性连通区域筛选器，不再需要单独点击建议按钮：

1. multi-scale morphological blackhat for locally dark structures / 多尺度形态学黑帽提取局部暗结构；
2. multi-scale Hessian eigenvalue response for thin dark ridges / 多尺度 Hessian 特征值响应提取细暗脊；
3. strong-seed/weak-neighbour hysteresis with connected-component geometry filtering / 强种子—弱邻域迟滞与连通区域几何过滤。

Version 4.4 evaluates the selector at the nominal sensitivity and its two neighbours (`−0.15`, `+0.15`, clamped to 0–1). Pixels selected at every sampled setting form the stable set; pixels present in the union but absent from the stable set form the disagreement set. A small display dilation makes these regions visible as yellow hotspots without adding them to the editable green mask. `evidence.json` records `review_guidance.method: three_level_sensitivity_vote_disagreement`, sampled sensitivities, stable/union/disagreement counts, disagreement ratio, hotspot area, and hotspot component count. `review-hotspots.png` preserves the exact review layer.

v4.4 会在当前灵敏度及其两个邻域值（`−0.15`、`+0.15`，限制在 0–1）运行筛选器。所有设置都选中的像素构成稳定集；并集中存在但未进入稳定集的像素构成分歧集。系统只为显示而对分歧区做小范围膨胀，形成黄色热点，不会把黄色自动加入绿色可编辑掩膜。`evidence.json` 记录采样灵敏度、稳定/并集/分歧像素数、分歧比例、热点面积和热点连通区域数；`review-hotspots.png` 保存精确复核层。

The service preserves the exact yellow display layer, then uses a scale-aware odd-diameter dilation only for worklist grouping. It extracts connected review zones from that grouping layer and ranks at most 24 with:

```text
priority score = disagreement pixels × (1 + nominal-proposal overlap ratio)
```

This places large unstable regions that directly intersect the current editable proposal before smaller or proposal-external regions. Ties are resolved deterministically by disagreement size, hotspot area, then image position. Every ranked item records its stable ID, rank, source-resolution bounding box, centroid, hotspot/disagreement/nominal pixel counts, overlap ratio, and score. The queue also records its share of all disagreement pixels and of total component-priority mass, so limiting the operator worklist cannot be mistaken for covering every detected component.

服务保留精确黄色显示层，再以随图像尺寸变化的奇数直径膨胀层专门进行工作清单分组；它从分组层提取连通复核区域，并最多排序 24 项：

```text
优先分数 = 分歧像素数 ×（1 + 当前候选重叠比例）
```

因此，面积较大且直接影响当前绿色候选的区域会排在更小或候选之外的区域之前。分数相同时依次按分歧规模、热点面积和图像位置确定顺序，保证复现。每项记录稳定编号、名次、原图分辨率边界框、质心、热点/分歧/候选像素数、重叠比例与分数。队列还记录其覆盖全部分歧像素和组件总优先质量的比例，避免把“限制操作员工作量”误解为“覆盖了所有热点”。

The browser can mark ranked items as inspected without changing mask pixels. On save, `measurement.json` records the inspected IDs, count completion ratio, and priority-weighted coverage under `mask.proposal_revision.hotspot_review`. The status is `not_started`, `partial`, `complete`, or `not_available`. “Complete” means every ranked target was marked; it does not mean every raw component was ranked, every crack was found, or the mask is correct.

网页可把排序项标记为已检查，而不改变掩膜像素。保存后，`measurement.json` 在 `mask.proposal_revision.hotspot_review` 下记录已检查编号、数量完成率和优先影响覆盖率；状态为 `not_started`、`partial`、`complete` 或 `not_available`。“complete”只表示所有排序目标都被标记，不代表所有原始热点都进入队列、所有裂缝都被发现或掩膜正确。

### Synchronized review loupe / 同步复核放大窗

Version 4.5 places a fixed `640 × 360` internal-pixel loupe next to the ranked queue. For the current hotspot, the browser expands the source-resolution bounding box by at least `2.2×`, enforces the loupe's `16:9` aspect ratio, keeps a minimum source viewport of `72 × 54` pixels, and clamps that viewport to the image boundary. The zoom badge reports both effective magnification and the source viewport size.

v4.5 在排序队列旁加入内部像素固定为 `640 × 360` 的同步放大窗。浏览器以当前热点的原图边界框为中心，至少扩展 `2.2×`，保持放大窗的 `16:9` 比例，原图视口最小为 `72 × 54` 像素，并把视口限制在原图边界内。角标同时显示有效放大倍数和原图视口尺寸。

Pointer positions are first normalized from the loupe's CSS display size to its internal `640 × 360` raster. They are then mapped back to source-image coordinates:

指针位置先从放大窗的 CSS 显示尺寸归一化到内部 `640 × 360` 栅格，再映射回原图坐标：

```text
source_x = viewport_x + loupe_x / loupe_width × viewport_width
source_y = viewport_y + loupe_y / loupe_height × viewport_height
```

The main canvas and loupe therefore share one original-resolution mask, stroke history, brush diameter, eraser behaviour, and undo stack. A brush or eraser stroke in the loupe immediately updates both views and marks the active ranked target as inspected. Calibration points remain restricted to the main canvas because their four-point ordering requires whole-image context.

因此，主画布和放大窗共用同一张原图分辨率掩膜、笔迹历史、笔刷直径、橡皮行为和撤销栈。在放大窗画或擦会立即同步更新两处，并把当前排序目标标为已检查。四点标定仍只允许在主画布操作，因为点位顺序需要完整画面上下文。

Magnification improves review ergonomics but does not create new image information or guarantee that a subtle crack is detected. The audit record stores the resulting proposal-to-final pixel difference and reviewed hotspot ID; it does not treat the loupe as additional model evidence.

放大只改善复核操作，不会创造新的图像信息，也不保证发现细微裂缝。审计记录保存候选到最终掩膜的像素差异和已检查热点编号，不会把放大窗当作额外模型证据。

### Structured hotspot dispositions / 结构化热点处置

Version 4.6 gives every ranked target one bounded operator disposition: `accepted_as_proposed`, `false_positive_removed`, `missed_crack_added`, or `deferred_for_follow_up`. A loupe brush stroke selects the added-miss disposition automatically; an eraser stroke selects removed-false-positive. The operator can override either and attach an optional note of at most 160 characters.

v4.6 为每个排序目标提供一个受限的操作员处置：接受候选、误检已删除、漏检已补画或暂缓跟进。放大窗画笔会自动选择“漏检已补画”，橡皮会选择“误检已删除”；操作员可以改写，并附加最多 160 字的可选备注。

The browser submits decisions in queue order. The service independently validates the JSON shape, category allow-list, unique hotspot IDs, membership in the current proposal, note bound, and the invariant that every decisioned target is also inspected. `measurement.json` stores rank-ordered decisions, per-category counts, `ranked_decision_completion_ratio`, and `ranked_decision_priority_coverage_ratio` under `mask.proposal_revision.hotspot_review`.

浏览器按队列顺序提交处置。服务端独立验证 JSON 结构、类别白名单、热点编号唯一性、编号是否属于当前候选、备注长度，以及“有处置的目标必须同时已检查”这一约束。`measurement.json` 在 `mask.proposal_revision.hotspot_review` 下保存按排名排列的处置、分类计数、数量完成率和优先级加权决策覆盖率。

The disposition describes what the operator did or concluded during this review. It is not an automatic truth label, engineering diagnosis, repair order, or proof that deferred targets are safe.

处置只描述操作员在本次复核中的操作或结论，不是自动真值标签、工程诊断、维修工单，也不能证明暂缓目标是安全的。

### Active-learning feedback package / 主动学习反馈包

When a saved human review or machine-reviewed candidate contains at least one structured disposition, the service creates `active-learning-feedback.zip` beside `measurement.json`. Each dispositioned target contains four aligned PNGs: the source ROI, immutable proposal mask, submitted candidate mask, and sensitivity-disagreement layer. The crop adds 15% context with an eight-pixel minimum and is proportionally reduced when it exceeds 512,000 pixels; masks always use nearest-neighbour resizing.

当保存的人工复核或机器复核候选至少包含一项结构化处置时，服务会在 `measurement.json` 旁生成 `active-learning-feedback.zip`。每个已处置目标包含四张对齐 PNG：原图 ROI、不可变候选掩膜、提交的候选掩膜和灵敏度分歧层。裁剪增加 15% 上下文且至少 8 像素；超过 512,000 像素时等比例缩小，掩膜始终采用最近邻缩放。

`manifest.json` records original and exported crop geometry, scale, rank, priority, disposition, optional note, `review_authority`, `decision_authority`, and SHA-256 for every PNG. It also binds the package to the source and immutable measurement digests. ZIP entries use fixed timestamps and sorted paths, so identical entry content produces reproducible archive bytes. No absolute path is stored.

`manifest.json` 记录原始和导出裁剪几何、比例、排名、优先级、处置、可选备注、`review_authority`、`decision_authority` 以及每张 PNG 的 SHA-256，并把反馈包绑定到源图和不可变量测摘要。ZIP 成员使用固定时间戳和排序路径，因此相同成员内容能产生可复现压缩包；不会保存绝对路径。

### Policy-bounded local autopilot / 受策略约束的本地自动驾驶

Version 5.2 enables autopilot by default. After proposal generation, the browser deterministically marks every ranked hotspot as inspected and applies one transparent rule: `candidate_overlap_ratio >= 0.10` becomes `accepted_as_proposed`; otherwise the hotspot becomes `deferred_for_follow_up`. The service independently recomputes this rule and rejects incomplete or mismatched machine decisions. It then submits pixel metrology as `review_state: machine_reviewed_candidate` with `review_authority: machine_heuristic`, automatically builds curation, and automatically runs snapshot preflight. The threshold is source code and audit evidence—not a learned confidence or a hidden prompt.

v5.2 默认开启自动驾驶。候选生成后，浏览器会确定性地把所有排序热点标为已检查，并执行一条透明规则：`candidate_overlap_ratio >= 0.10` 时记录为 `accepted_as_proposed`，否则记录为 `deferred_for_follow_up`。服务端会独立重算该规则，拒绝不完整或不匹配的机器决策。随后以 `review_state: machine_reviewed_candidate` 和 `review_authority: machine_heuristic` 提交像素量测，自动生成策划并运行快照预检。这个阈值是源码与审计证据，不是学习得到的置信度，也不是隐藏提示词。

The automated chain saves work without fabricating accountability. A machine candidate may pass pixel-consistency gates, but any selected non-human label adds `machine_labels_require_human_approval`; `training_authorized` remains `false`. A later brush/eraser correction is submitted separately as `human_reviewed` with `human_operator` authority. Disabling the toggle preserves the older `automatic_draft` path.

自动链路减少操作，但不伪造责任归属。机器候选可能通过像素一致性门控，但任何入选的非人工标签都会加入 `machine_labels_require_human_approval`，且 `training_authorized` 保持 `false`。后续画笔/橡皮修订会单独以 `human_reviewed` 和 `human_operator` 身份保存。关闭开关则保留旧的 `automatic_draft` 路径。

### Resilient batch autopilot / 弹性批量自动驾驶

Version 5.3 accepts up to 100 images from one browser selection. It processes images serially to bound Apple MPS memory while retaining the existing per-image parallelism between multi-view inspection and crack proposal. Every queue entry has an independent `pending`, `running`, `complete`, or `failed` state. Decode, size, proposal, inference, or measurement failure marks only that entry as failed; the next image still runs.

v5.3 支持在一次浏览器选择中加入最多 100 张图片。图片之间串行处理以限制 Apple MPS 内存峰值，同时保留每张图片内部多视图巡检与裂缝候选的并行。每个队列项独立处于 `pending`、`running`、`complete` 或 `failed` 状态。解码、尺寸、候选、推理或量测失败只会标记当前项，下一张仍继续运行。

The browser defers governance during the queue and submits only successful metrology run IDs to `POST /api/metrology/autopilot-batches/finalize`. The service reloads every immutable `measurement.json`, requires `machine_reviewed_candidate` plus `machine_heuristic`, and rejects duplicates, missing runs, or non-machine records. Curation is scoped to feedback packages from that explicit run set, preventing unrelated historical packages from entering the batch.

浏览器在队列期间暂缓治理，只把成功量测编号提交给 `POST /api/metrology/autopilot-batches/finalize`。服务端重新读取每份不可变 `measurement.json`，强制要求 `machine_reviewed_candidate` 与 `machine_heuristic`，并拒绝重复编号、缺失运行或非机器记录。策划仅限该明确运行集合的反馈包，防止不相关历史包混入本批次。

The immutable `urbanvision-autopilot-batch-v1.4.0` record binds measurement SHA-256, source SHA-256, cross-channel arbitration, feedback presence, configuration, two governance scopes, and the automatic distribution-monitoring record. `governance` references the exact batch; `cumulative_registry` references all-session local curation and snapshot; `distribution_monitoring` references the current-versus-history audit. It deliberately omits original filenames and absolute paths.

不可覆盖的 `urbanvision-autopilot-batch-v1.4.0` 记录绑定量测 SHA-256、来源 SHA-256、双通道仲裁、反馈是否存在、配置、两个治理范围和自动分布监测记录：`governance` 仅引用当前批次，`cumulative_registry` 引用跨会话累计策划与快照，`distribution_monitoring` 引用当前批次与历史基线的审计。记录有意省略原文件名与绝对路径。

### Content-aware self-healing / 内容感知自愈

Version 5.4 computes each eligible browser file's content digest with `crypto.subtle.digest("SHA-256", ...)` before inference. The first digest enters the serial queue; later exact matches become `duplicate` and consume no MPS inference. This is byte-level equality, not perceptual similarity. Filenames remain visible only in live browser memory so the operator can follow progress.

v5.4 在推理前使用 `crypto.subtle.digest("SHA-256", ...)` 计算每个合格浏览器文件的内容摘要。第一次出现的摘要进入串行队列，后续完全相同内容标为 `duplicate`，不再消耗 MPS 推理。这证明的是字节级相等，不是感知相似；文件名只停留在当前浏览器内存中，供操作员查看进度。

Failures are classified before retry. Unsupported content type, more than 15 MiB, decode failure, and more than 20 megapixels are deterministic and immediately skipped. Only `pipeline_incomplete` and `unexpected_error` are recoverable; `MAX_BATCH_ATTEMPTS = 2` gives them one automatic retry. The live queue exposes `hashing`, `running`, `retrying`, `complete`, `failed`, and `duplicate` rather than hiding recovery.

系统会先分类再决定是否重试。格式不支持、超过 15 MiB、解码失败和超过 2000 万像素属于确定性错误，直接跳过；只有 `pipeline_incomplete` 和 `unexpected_error` 属于可恢复错误，`MAX_BATCH_ATTEMPTS = 2` 表示自动再试一次。页面明确显示 `hashing`、`running`、`retrying`、`complete`、`failed` 和 `duplicate`，不会隐藏恢复过程。

The finalize request sends successful run IDs, same-order browser digests and arbitration IDs, plus aggregate selected/failed/duplicate/retry counts. The service reloads immutable measurements, verifies run identity and `machine_heuristic` authority, compares every browser digest with server-preserved source SHA-256, verifies every arbitration-to-run binding, rejects repeated sources, and requires accounting equality. The v1.2 ledger exposes `browser_digest_match_count`, `server_duplicate_source_rejection`, and `cross_channel_arbitration`; client-reported failure counts never authorize labels or training.

最终请求提交成功运行编号、同顺序浏览器摘要与仲裁编号，以及选择/失败/重复/重试汇总数。服务端重新读取不可变量测，验证运行身份和 `machine_heuristic` 权限，把每个浏览器摘要与服务端保存的来源 SHA-256 比较，验证每条仲裁—运行绑定，拒绝重复来源，并强制账目等式成立。v1.2 账本公开 `browser_digest_match_count`、`server_duplicate_source_rejection` 和 `cross_channel_arbitration`；客户端报告的失败数量绝不会授权标签或训练。

### Cross-channel selective prediction / 双通道选择性预测

Version 5.5 does not make YOLO boxes pretend to be a crack mask, and it does not let a classical segmentation candidate pretend to know D00/D10/D20 semantics. The two channels remain independent until `POST /api/evidence/arbitrate` reloads their immutable evidence. The inspection manifest now binds the original upload bytes as `source_upload_sha256`; arbitration requires that digest to equal metrology `input_evidence.source.sha256`.

v5.5 不会把 YOLO 框伪装成裂缝掩膜，也不会让传统分割候选假装理解 D00/D10/D20 语义。两个通道保持独立，直到 `POST /api/evidence/arbitrate` 重新加载各自不可变证据。巡检清单新增原始上传字节的 `source_upload_sha256`；仲裁强制它与量测 `input_evidence.source.sha256` 相等。

For D00, D10, and D20 detections, the service rasterizes the clipped semantic box union at source resolution and intersects it with the final binary mask. It records proposal pixels, image coverage, semantic-box union pixels, overlap pixels, proposal-supported ratio, and semantic-region-supported ratio. A proposal is significant only when it has at least 64 foreground pixels and covers at least 0.00005 of the image. `cross_channel_supported` requires at least 0.10 of proposal pixels inside crack boxes.

对 D00、D10 和 D20 检测，服务端在原图分辨率栅格化裁剪后的语义框并集，再与最终二值掩膜求交。记录包括候选像素、画面覆盖、语义框并集像素、交集像素、候选支持比例和语义区域支持比例。候选只有同时达到 64 个前景像素和画面 0.00005 覆盖才算显著；`cross_channel_supported` 要求至少 0.10 候选像素落入裂缝框。

The deterministic state machine is:

- significant proposal + no semantic crack box → `proposal_only_semantic_miss`;
- semantic crack box + no significant proposal → `detector_only_semantic_evidence`;
- both channels + proposal-supported ratio at least 0.10 → `cross_channel_supported`;
- both channels + support below 0.10 → `spatial_disagreement`;
- neither positive → `inconclusive_no_positive_evidence`.

确定性状态机如下：

- 显著分割候选 + 无语义裂缝框 → `proposal_only_semantic_miss`；
- 有语义裂缝框 + 无显著分割候选 → `detector_only_semantic_evidence`；
- 两通道都有证据 + 候选支持比例至少 0.10 → `cross_channel_supported`；
- 两通道都有证据 + 支持低于 0.10 → `spatial_disagreement`；
- 两通道都无正证据 → `inconclusive_no_positive_evidence`。

Every state except unblocked `cross_channel_supported` forces selective abstention: the UI replaces the maintenance score with `—` and shows the arbitration recommendation. Upstream risk or multi-view review gates still take precedence, so even cross-channel agreement cannot clear an already unsafe result. The immutable `urbanvision-cross-channel-arbitration-v1.0.0` record binds inspection manifest, prediction, risk, measurement, final mask, source digest, policy, metrics, and claim boundary without storing a filename or absolute path. A normalized binary-mask SHA-256 prevents a same-pixel-count but spatially altered mask from passing, and batch finalization rechecks both measurement and mask digests.

除未被上游阻断的 `cross_channel_supported` 外，其余状态都会触发选择性拒答：页面用 `—` 替代维护分数并显示仲裁建议。上游风险或多视图复核门控仍优先，因此双通道一致也不能放行原本不安全的结果。不可覆盖的 `urbanvision-cross-channel-arbitration-v1.0.0` 记录绑定巡检清单、预测、风险、量测、最终掩膜、来源摘要、策略、指标和使用边界，不保存文件名或绝对路径。规范化二值掩膜 SHA-256 会阻止“像素数量相同但空间位置被替换”的掩膜通过，批次封账还会重新核对量测和掩膜摘要。

This layer detects a class of cross-method inconsistency; it does not establish which method is correct. Box overlap is coarse spatial support, not segmentation IoU, calibrated probability, causal pavement diagnosis, or ground truth.

这一层发现的是跨方法不一致，不能判定哪个方法正确。框重叠只是粗粒度空间支持，不是分割 IoU、校准概率、因果路面诊断或真值。

This package is a candidate pool for separately governed relabeling, error analysis, and future training—not an automatic training set. Source ROIs may contain people, vehicles, licence plates, or location cues, so a dataset owner must apply privacy review, split control, deduplication, and label QA before training.

该反馈包只是供独立治理的再标注、误差分析和未来训练候选池，不是可以直接训练的自动数据集。原图 ROI 可能包含人员、车辆、车牌或地点线索；训练前必须由数据负责人执行隐私复核、数据划分控制、去重和标签质检。

### Feedback quality gates and registry / 反馈质量门控与台账

Version 4.8 compares proposal and final pixels inside every exported ROI. It records foreground, added, removed, and changed pixel counts plus proposal-to-final IoU. The gate reports `warning` when the observed change contradicts the disposition: accepted with changed pixels, removal without removed pixels, addition without added pixels, or a single-direction correction that also changes pixels in the opposite direction. Deferred items remain explicitly `deferred`; they do not silently pass.

v4.8 会在每个导出 ROI 内比较候选与最终像素，记录前景、增加、删除、改动像素数和候选—最终 IoU。当观察变化与处置矛盾时，门控报告 `warning`：接受候选但像素发生变化、删除处置却没有删除像素、补画处置却没有增加像素，或单向修正同时出现反向像素变化。暂缓项明确保持 `deferred`，不会悄悄标为通过。

Each source ROI also receives a deterministic 64-bit difference hash. Equal hashes are exposed as duplicate candidates, not automatically deleted or asserted to be identical. Difference hashing is deliberately a low-cost curation signal and can collide.

每个原图 ROI 还会生成确定性 64 位差分指纹。相同指纹只会暴露为重复候选，不会自动删除，也不会断言图片完全相同。差分指纹只是低成本治理信号，可能发生碰撞。

`GET /api/metrology/feedback-catalog?limit=100` reads only bounded `manifest.json` members and aggregates package count, item count, unique source digests, disposition distribution, quality states, malformed-package count, and duplicate-fingerprint groups. The endpoint never extracts source PNGs and remains loopback-only. Its counts support triage; they are not training-readiness certification.

`GET /api/metrology/feedback-catalog?limit=100` 只读取有大小上限的 `manifest.json`，聚合反馈包数、样本数、唯一源图摘要、处置分布、质量状态、格式错误包数量和重复指纹组。接口不会解压原图 PNG，并且只监听本机回环地址。这些计数用于分流，不是训练就绪认证。

### Leakage-safe candidate curation / 防泄漏候选数据策划

`POST /api/metrology/feedback-curations` creates an immutable candidate plan from at most 100 local package manifests. Only `quality_gate.status == "pass"` is eligible. Warning, deferred, unknown, and malformed candidates are counted and excluded. Equal 64-bit difference fingerprints retain one representative by descending priority and deterministic run/hotspot tie-breaks; no source ZIP is modified or deleted.

`POST /api/metrology/feedback-curations` 从至多 100 个本地反馈包清单生成不可覆盖的候选策划。只有 `quality_gate.status == "pass"` 可以入选；警告、暂缓、未知和格式错误候选都会计数并排除。相同 64 位差分指纹按优先级降序及确定性的运行/热点规则只保留一个代表；原始 ZIP 不会被修改或删除。

The assignment unit is the complete `source_sha256` group, never an individual ROI. In v5.6, a seeded deterministic allocator first reserves one complete visual group for each positive-ratio split whenever enough groups exist, then assigns the remainder by ratio deficit. The JSON records all three pairwise source intersections, so the guarantee is machine-verifiable. This protects against same-file leakage; it cannot prove that two different files do not show the same physical location.

分配单位是完整的 `source_sha256` 组，而不是单个 ROI。v5.6 的带种子确定性分配器会在视觉簇足够时，先为每个正比例切分预留一个完整视觉簇，再按比例缺口分配剩余簇。JSON 记录三个两两源图交集，因此该保证可以机器验证。它能防止同一文件泄漏，但不能证明两个不同文件没有拍摄同一实际地点。

The v5.7 plan separates readiness into two axes. Too few independent sources, an empty positive-ratio split, malformed packages, a truncated inventory, or a failed overlap audit produce `technical_data_not_ready`. If those checks pass while privacy, label QA, or machine-label approval remains pending, the status is `technical_data_ready_governance_blocked`. With neither axis blocked, the status is still only `candidate_plan_requires_training_approval`; `training_authorized` remains `false`.

v5.7 把就绪状态拆成两轴。独立原图不足、正比例切分为空、反馈包损坏、清单截断或交集审计失败时，状态为 `technical_data_not_ready`；技术检查通过但隐私、标签质量或机器标签审批待完成时，状态为 `technical_data_ready_governance_blocked`。两轴都无阻断时，状态仍只是 `candidate_plan_requires_training_approval`，且 `training_authorized` 始终为 `false`。

The v5.7 `urbanvision-feedback-curation-v2.3.0` record retains `allocation` and `readiness.remediation`, then adds structured `readiness.technical` and `readiness.governance`. For “67 candidates from 3 independent sources,” the technical axis reports seven additional independent sources while the governance axis reports all 67 machine candidates awaiting approval. Every batch finalization also rebuilds an all-local-feedback curation, so three sources from this session plus seven independent sources from later sessions can satisfy the cumulative technical threshold without weakening the immutable batch scope.

v5.7 的 `urbanvision-feedback-curation-v2.3.0` 保留 `allocation` 与 `readiness.remediation`，并新增结构化 `readiness.technical` 和 `readiness.governance`。对于“67 个候选来自 3 张独立原图”，技术轴报告还差 7 个来源，治理轴报告 67 个机器候选待批准。每次批次结束还会重建包含全部本机反馈的策划，因此本次 3 个来源与以后会话采集的 7 个独立来源可以共同满足累计技术门槛，同时不弱化不可变的本批次范围。

Internet research is recorded as a bounded reference rather than an automatic download. The official [RDD2022 source](https://github.com/sekilab/RoadDamageDetector) provides six-country data, D00/D10/D20/D40 Pascal VOC annotations, and CC BY-SA 4.0 image licensing. It is valid as an external detector benchmark but not as pixel-mask approval. A 400-image RDD2022-derived mask deposit was deliberately excluded from automatic ingestion because its downstream CC BY metadata does not explain how the upstream ShareAlike condition is preserved; license review is required before reuse.

联网调研结果只作为有界参考记录，不会触发自动下载。官方 [RDD2022 来源](https://github.com/sekilab/RoadDamageDetector) 提供六国数据、D00/D10/D20/D40 Pascal VOC 标注及 CC BY-SA 4.0 图片许可，可作为外部检测基准，但不能冒充分割掩膜批准。一个含 400 张图片的 RDD2022 派生掩膜存档被明确排除出自动导入，因为其下游 CC BY 元数据没有说明如何保留上游 ShareAlike 条件；复用前必须单独审查许可证。

### Fail-loudly dataset-shift monitoring / 主动暴露数据漂移

After batch and cumulative preflight, v5.8 creates `urbanvision-feedback-drift-audit-v1.0.0`. The current sample is the exact batch curation; the reference is the cumulative curation after excluding every current `source_sha256`. Each exact source contributes one vector, averaged over no more than eight SHA-256-verified ROI/mask pairs. This prevents hotspot-rich images from receiving extra statistical weight.

批次与累计预检结束后，v5.8 会生成 `urbanvision-feedback-drift-audit-v1.0.0`。当前样本来自精确批次策划，参考样本来自排除所有当前 `source_sha256` 后的累计策划。每个精确来源只贡献一个向量，由最多八个通过 SHA-256 验证的 ROI/掩膜对平均得到，避免热点较多的图片获得额外统计权重。

The audit uses nine bounded, interpretable image/mask features and an RBF maximum mean discrepancy statistic. A fixed 199-permutation test estimates the null tail deterministically from the two bound curation files. Nearest-neighbor coverage is reported separately using root-mean-square feature distance and a historical median-plus-three-scaled-MAD threshold. The JSON records every source digest, feature vector, p-value, bandwidth, permutation seed, novelty distance, top mean-shift features, byte budget, and blocker.

审计使用九个有界、可解释的图像/掩膜特征与 RBF 最大均值差异统计量，通过固定 199 次置换，从两份已绑定策划文件确定性估计零假设尾部。最近邻覆盖率单独使用特征均方根距离，并以历史留一距离的中位数加三倍缩放 MAD 作为阈值。JSON 会记录来源摘要、特征向量、p 值、带宽、置换种子、新颖距离、主要均值变化特征、字节预算和阻断项。

The minimum evidence is three current and five historical independent sources. Below either threshold, the audit status is `insufficient_or_invalid_evidence`; it does not silently equate low statistical power with “no shift.” Above the threshold it reports either `no_statistically_detectable_shift` or `distribution_shift_or_coverage_warning`.

最低证据要求是当前 3 个、历史 5 个独立来源。任何一侧不足时，状态为 `insufficient_or_invalid_evidence`，不会把低统计功效静默解释成“没有漂移”；达到门槛后，状态才可能是 `no_statistically_detectable_shift` 或 `distribution_shift_or_coverage_warning`。

MMD detects a difference in the monitored feature distribution, not why it changed or whether model error increased. This monitor cannot prove concept drift, label quality, field validity, or road danger, and it never authorizes training.

MMD 只能检测受监测特征分布的差异，不能解释变化原因或证明模型误差上升。该监测器不能证明概念漂移、标签质量、现场有效性或道路危险，也绝不会授权训练。

### Visual-scene leakage firewall / 视觉场景泄漏防火墙

Version 5.0 addresses a harder failure mode: two different files can show nearly the same texture, crop, or physical scene while having different SHA-256 values. For each selected source, the curator retains at most 128 bounded source-ROI difference hashes. It compares every source pair by the minimum Hamming distance between their fingerprints and records a link when that distance is at or below `max_scene_hamming_distance` (default 4, allowed 0–16).

v5.0 处理更难的失败模式：两个不同文件可能呈现几乎相同的纹理、裁剪或实际场景，但 SHA-256 完全不同。策划器为每个入选来源最多保留 128 个有界原图 ROI 差分指纹，在所有来源对之间计算指纹集合的最小汉明距离；当距离不大于 `max_scene_hamming_distance`（默认 4，允许 0–16）时记录一条连接。

The links enter deterministic single-linkage union-find. Therefore A≈B and B≈C place A, B, and C in one transitive visual group even when A and C do not directly meet the threshold. The allocation algorithm receives complete visual groups instead of individual sources. Each item records `visual_scene_group_id`; every split lists its scene-group IDs; and `leakage_audit` verifies that neither exact sources nor visual groups overlap.

连接进入确定性单链并查集。因此即使 A 与 C 没有直接达到阈值，只要 A≈B 且 B≈C，三者也会进入同一个传递视觉簇。切分算法接收完整视觉簇，而不是单个来源。每个样本记录 `visual_scene_group_id`，每个切分列出视觉簇编号，`leakage_audit` 同时验证精确来源和视觉簇均无交集。

This is intentionally conservative. Difference hashes can collide, single linkage can chain unrelated scenes, and ROI similarity is not geolocation. Raising the threshold reduces leakage risk but increases false grouping and may leave validation or test empty. Every link stores both source digests, both fingerprints, and the measured distance so a reviewer can audit the grouping rather than trust a hidden heuristic.

该机制有意保持保守。差分指纹可能碰撞，单链可能把无关场景串联，ROI 相似也不等于地理位置相同。调高阈值会降低泄漏风险，但增加误合并概率，并可能使验证集或测试集为空。每条连接保存两侧来源摘要、指纹和实际距离，让复核者审计分组，而不是盲目信任隐藏启发式规则。

### Content-addressed snapshot preflight / 内容寻址快照预检

`POST /api/metrology/feedback-curations/{curation_id}/snapshot-preflight` verifies a v5.2 curation without extracting a dataset. It SHA-256 binds the curation JSON, reloads the current bounded manifest inventory, and rejects missing or changed manifests. For every selected pair, it revalidates the run/hotspot/manifest binding and reads only the referenced source ROI and final mask from the preserved ZIP.

`POST /api/metrology/feedback-curations/{curation_id}/snapshot-preflight` 在不解压数据集的情况下验证 v5.2 策划。它用 SHA-256 绑定策划 JSON，重新加载当前有界清单，并拒绝缺失或变化的清单。对每个入选数据对，它重新校验运行、热点与清单绑定，只从保留 ZIP 中读取被引用的原图 ROI 和最终掩膜。

Each member is capped at 8 MiB and the full read is capped at 512 MiB. SHA-256 is checked before decoding. The source and mask must decode, share dimensions, remain within 512,000 pixels, and the final mask may contain only binary 0/255 values. A valid all-zero final mask is retained and counted because reviewed negative segmentation examples can be meaningful.

每个成员上限为 8 MiB，完整读取预算为 512 MiB；解码前先验证 SHA-256。原图与掩膜必须可解码、尺寸一致、不超过 512,000 像素，最终掩膜只能含 0/255 二值。合法全零最终掩膜会被保留并计数，因为人工复核后的负分割样本同样可能有价值。

Preflight independently recomputes cross-split exact-source, visual-group, and identical source-member overlaps. Canonical JSON leaves contain split, run, hotspot, source digest, visual group, source-member digest, target-member digest, and review authority. Sorted leaves use SHA-256 with `0x00` leaf-domain separation; parents use `0x01`; the final node is duplicated on odd levels. The result is an immutable `urbanvision-feedback-snapshot-preflight-v1.2.0` JSON with a reproducible Merkle root, upstream remediation, and separate technical-integrity and governance axes.

预检会独立重算切分间的精确来源、视觉簇和相同原图成员交集。规范化 JSON 叶节点包含切分、运行、热点、来源摘要、视觉簇、原图成员摘要、目标成员摘要和审核身份。排序叶使用带 `0x00` 叶域分离的 SHA-256，父节点使用 `0x01`，奇数层复制最后节点。结果是带可复现 Merkle 根、上游修复建议、技术完整性轴和治理轴的不可覆盖 `urbanvision-feedback-snapshot-preflight-v1.2.0` JSON。

When byte and split integrity pass but governance remains pending, status is `integrity_verified_governance_blocked`. With neither kind of blocker, status is `verified_candidate_snapshot_requires_training_approval`, never “training ready.” Member integrity and Merkle reproducibility do not establish privacy clearance, semantic label correctness, field validity, or model performance.

字节与切分完整性通过但治理待完成时，状态为 `integrity_verified_governance_blocked`；两类阻断都不存在时，状态也只是 `verified_candidate_snapshot_requires_training_approval`，绝不是“训练就绪”。成员完整性和 Merkle 可复现性不能证明隐私许可、语义标签正确、现场有效性或模型性能。

Images larger than two million pixels are processed on a downsampled work raster and the binary proposal is restored to the exact source resolution. This bounds memory and runtime without sending pixels to a cloud service. The sensitivity slider changes proposal recall; it is not a calibrated probability or YOLO confidence.

超过 200 万像素的图片会在缩小的工作栅格上处理，再把二值候选恢复到原图精确分辨率，从而限制内存和耗时，且不发送到云端。灵敏度滑块改变候选召回范围，不是经过标定的概率或 YOLO 置信度。

The yellow layer is triage guidance, not model uncertainty calibration: it only answers “where did this deterministic algorithm change under a nearby parameter perturbation?” Stable green pixels can still be wrong, and real cracks can still be missed at all three settings.

黄色层是复核分流提示，不是模型不确定性校准：它只回答“确定性算法在邻近参数扰动下，哪些位置发生变化”。稳定的绿色像素仍可能是误检，三个设置都未选中的真实裂缝仍可能漏检。

An empty proposal is returned as unusable, and a proposal covering more than 35% of the image is rejected as too broad instead of being painted automatically.

空候选会标为不可用；候选覆盖超过整图 35% 时会以“范围过宽”拒绝自动载入，而不是把大面积噪声涂到画布上。

The proposal becomes the editable green base layer. Every later brush or eraser stroke is replayed above that immutable base. When metrology is submitted, `measurement.json` records the proposal ID and schema, proposal/final mask hashes, human-added pixels, human-removed pixels, changed-image ratio, and proposal-to-final IoU.

候选会成为可编辑的绿色底稿，后续画笔或橡皮笔迹都在不可变底稿之上重放。提交量测时，`measurement.json` 会记录候选编号与版本、候选/最终掩膜摘要、人工增加像素、人工删除像素、整图改动比例和候选—最终 IoU。

With autopilot disabled, the first automatic pixel run records `review_state: automatic_draft` and `mask.origin: local_proposal_automatic_draft`. With autopilot enabled, it records `machine_reviewed_candidate` and `local_proposal_machine_reviewed_candidate`. Saving after human review records `review_state: human_reviewed`. These are workflow audit labels, not claims that any mask is objectively correct.

关闭自动驾驶时，第一次自动像素量测记录 `review_state: automatic_draft` 与 `mask.origin: local_proposal_automatic_draft`；开启时记录 `machine_reviewed_candidate` 与 `local_proposal_machine_reviewed_candidate`；人工复核后保存则记录 `review_state: human_reviewed`。这些字段是流程审计标签，不等于系统宣称任何掩膜客观正确。

This is intentionally called a **proposal**, not automatic segmentation truth. Shadows, expansion joints, road markings, stains, patched seams, and low contrast can produce false positives or false negatives. A person must inspect the entire mask before using physical measurements.

它被明确称为**建议**，不是自动分割真值。阴影、伸缩缝、道路标线、污渍、修补接缝和低对比度都可能产生误检或漏检；使用真实尺寸前，必须由人工检查完整掩膜。

## Practical maintenance workflow / 实际维护工作流

### Material and cost planning / 材料与成本规划

After a physically calibrated run, enter the intended routed-joint width, depth, waste percentage, and optional price per litre. The app calculates:

完成真实平面标定后，填写计划开槽宽度、深度、损耗率和可选的每升单价。网页计算：

```text
base litres = calibrated length (m) × route width (mm) × route depth (mm) ÷ 1000
procurement litres = base litres × (1 + waste % ÷ 100)
estimated cost = procurement litres × optional unit price
```

The result is useful for a property manager, campus maintenance team, parking-facility operator, or contractor preparing a survey-based material estimate. It stores the exact assumptions and the SHA-256 digest of the source measurement in an immutable JSON record. It is **not** a construction specification, vendor quote, or safety verdict; field routing dimensions and material choice still require a qualified maintainer.

它适用于物业、校园养护、停车设施运维或承包商根据巡检结果预估材料。记录会不可覆盖地保存全部假设和源量测 SHA-256。它**不是**施工规范、供应商报价或道路安全结论；开槽尺寸和材料选择仍需专业养护人员确认。

### Multi-date growth comparison / 多期增长对比

Measure the same crack region again with the same physical control points, mask policy, and camera procedure. Choose the older run as baseline, enter elapsed days, a spatial matching tolerance in millimetres, and your organization’s review thresholds, then compare. The service normalizes `m`, `cm`, and `mm` into SI units and reports network-length change, mean/P95 width change, junction change, and growth per day.

对同一裂缝区域采用相同物理控制点、掩膜规则和拍摄流程再次量测。选择旧记录作为基线，填写间隔天数、毫米级空间匹配容差和组织内部复核阈值后执行对比。服务会把 `m`、`cm`、`mm` 统一到 SI 单位，输出网络长度、平均/P95 宽度、分叉数量变化和每日增长率。

The v3.3 spatial layer uses each run’s four-point homography as a physical coordinate frame. It crops both calibrated planes to their common physical area, resamples them at the lower available resolution, and uses the declared millimetre tolerance to classify pixels:

v3.3 空间层把每次量测的四点单应性作为物理坐标框，裁取共同真实区域，按两者较低分辨率重采样，再使用声明的毫米容差分类：

- green: stable within tolerance / 绿色：容差内稳定；
- orange: suspected addition in the current mask / 橙色：当前掩膜中疑似新增；
- blue: suspected missing region / 蓝色：当前掩膜中疑似消失。

If calibrated-frame width or height differs by more than 5%, the service refuses the spatial comparison. At 2% or less the alignment label is `strong`; between 2% and 5% it is `acceptable`. This is a quality gate, not an image-similarity guess.

如果两次标定框宽度或高度差异超过 5%，服务拒绝空间对比；差异不超过 2% 标为 `strong`，2%–5% 标为 `acceptable`。这是明确的质量门槛，不是根据画面相似度猜测位置。

This turns a one-off image demo into a repeatable maintenance record. Orange and blue mean **suspected** change because mask inconsistency, occlusion, dirt, or calibration error can produce the same colours. A missing region must not be called “repaired” without field confirmation. Review thresholds decide only whether a person should inspect the evidence; they are not road-safety thresholds.

这把一次性图片 Demo 变成可重复的养护记录。橙色和蓝色只能称为**疑似变化**，因为掩膜不一致、遮挡、污渍或标定误差也可能产生相同颜色；未经现场确认，蓝色区域不能直接称为“已经修复”。阈值只决定是否要求人工查看证据，不是道路安全阈值。

### CLI demo / 命令行 Demo

```bash
uv run python -m urbanvision_risk.metrology.demo \
  --output-name metrology-demo-001
```

Expected terminal result / 预期终端结果：

```text
[PASS] v3 量测演示完成 / v3 metrology demo complete: .../results/metrology/metrology-demo-001
```

Inspect these files / 查看这些文件：

- `measurement.json`: all values, units, methods, provenance, and decision boundaries / 数值、单位、方法、来源和使用边界；
- `overlay.jpg`: mask, centerline, endpoints, junctions, and calibration quadrilateral / 掩膜、中心线、端点、分叉和标定四边形；
- `rectified-overlay.jpg`: fronto-parallel physical plane / 透视矫正后的真实平面；
- `width-heatmap.png`: local pixel-width field / 局部像素宽度场；
- `rectified-width-heatmap.png`: calibrated width field / 标定后的宽度场。

The demo proves deterministic software behaviour. It does **not** prove field accuracy.

演示只能证明算法和复现流程工作正常，不能代替现场精度实验。

## Field workflow / 现场实践流程

### Step 1 — Generate and print the marker kit / 生成并打印标记

```bash
uv run python -m urbanvision_risk.metrology.target \
  --output-name aruco-field-kit-001
```

Open the four SVG files under `results/metrology/calibration-targets/aruco-field-kit-001`. Print each at exactly **100%**, with “fit to page” disabled. Verify the black marker is exactly `50 mm × 50 mm` with a ruler. If it is not, the printer scaled the page and the field result is invalid.

打开生成的四张 SVG，必须按 **100% 原始比例**打印并关闭“适合页面”。用直尺确认黑色标记正好是 `50 mm × 50 mm`。不符合时说明打印机缩放了页面，本次现场结果无效。

### Step 2 — Place and measure / 摆放并实测

Place ID `17/TL`, `23/TR`, `42/BR`, and `56/BL` around the crack on the same pavement plane. Measure the marker-center-to-center physical width and height independently with a tape. Do not infer those values from the printed tile size.

按照 `17/TL`、`23/TR`、`42/BR`、`56/BL` 把四张标记围在裂缝周围，并确保它们与路面处于同一平面。用卷尺独立测量标记中心之间的真实宽和高；不能拿打印纸尺寸代替现场中心距。

Capture rules / 拍摄要求：

- all four markers and the entire crack are visible / 四张标记和完整裂缝都入镜；
- no motion blur, glare, or clipped marker border / 没有运动模糊、反光或标记裁切；
- keep the camera reasonably high and avoid an almost-horizontal view / 相机尽量高，避免接近水平的极端视角；
- do not move markers between measuring and photographing / 测量后到拍照前不能移动标记；
- do not use this planar method across a curb or obvious bump / 不跨越路缘或明显隆起使用单平面标定。

### Step 3 — Detect calibration automatically / 自动检测标定

Example: the measured center rectangle is `1.20 m × 0.80 m`.

示例：现场测得四个标记中心矩形为 `1.20 m × 0.80 m`。

```bash
uv run python -m urbanvision_risk.metrology.fiducials \
  --source-image field-road.jpg \
  --physical-width 1.20 \
  --physical-height 0.80 \
  --unit m \
  --pixels-per-unit 1000 \
  --point-sigma-pixels 1.0 \
  --output field-calibration.json
```

The detector fails closed if one marker is absent, IDs are wrong, or the four centers form a crossed/degenerate quadrilateral. The calibration JSON stores only the source filename and SHA-256 digest, not an absolute path.

如果缺少标记、ID 错误，或四个中心形成交叉/退化四边形，程序会直接失败而不是猜测。标定 JSON 只保存文件名和 SHA-256，不保存可能泄漏用户名的绝对路径。

### Step 4 — Create an independent binary mask / 制作独立二值掩膜

Create a PNG with exactly the same width and height as the source:

- crack = white (`255`);
- background = black (`0`);
- no semi-transparent layers;
- include only the crack surface you intend to measure.

制作一张与原图宽高完全相同的 PNG：

- 裂缝为白色（`255`）；
- 背景为黑色（`0`）；
- 不保留半透明图层；
- 只标注确实需要量测的裂缝表面。

For a defensible first field experiment, manually review the mask at 200–400% zoom. A future segmentation model may propose masks, but a model-generated mask must remain a separate evidence layer and must not silently replace ground truth.

第一次现场实验应在 200–400% 放大下人工复核掩膜。未来的分割模型可以提出候选掩膜，但模型掩膜必须保留独立来源，不能静默冒充人工真值。

### Step 5 — Measure / 执行量测

```bash
uv run python -m urbanvision_risk.metrology.measure \
  --source-image field-road.jpg \
  --mask field-crack-mask.png \
  --calibration field-calibration.json \
  --uncertainty-samples 128 \
  --segmentation-radius-pixels 2 \
  --output-name field-crack-001
```

Without `--calibration`, the same command intentionally returns `pixel_only` and sets `physical_measurement_valid` to `false`.

如果不提供 `--calibration`，同一命令只会输出 `pixel_only`，并把 `physical_measurement_valid` 设为 `false`。

## First-hand validation protocol / 亲身实践验证方案

The code is only half of the portfolio story. The difficult, credible half is your own measurement experiment.

代码只是简历故事的一半；真正体现亲身实践的是你自己完成并公开方法的量测实验。

Recommended dataset / 建议实验集：

1. Select at least 10 accessible pavement surfaces with different widths, branches, lighting, and texture.
2. Mark 3–5 crack segments per surface.
3. Capture each plane from three camera poses without moving the markers.
4. Measure reference length with flexible tape or a traced string; measure width at declared stations with a crack-width card or calliper where safe.
5. Have a second person repeat a subset without seeing the first result.
6. Preserve raw images privately; commit only anonymized aggregate metrics and redacted examples.

1. 选择至少 10 个可安全接近、宽度/分叉/光照/纹理不同的路面；
2. 每个路面选择 3–5 段裂缝；
3. 不移动标记，从三个相机姿态拍摄同一平面；
4. 用软卷尺或贴合曲线的线测长度，在预先声明的位置用裂缝宽度卡或安全条件下的卡尺测宽；
5. 让第二个人在不知道第一次结果的条件下复测一部分样本；
6. 原始图片私下保存，GitHub 只提交匿名汇总和脱敏示例。

Report these metrics / 报告这些指标：

- length MAE, RMSE, median absolute percentage error / 长度 MAE、RMSE、中位绝对百分比误差；
- width MAE at fixed stations and p95 error / 固定测点宽度 MAE 与 p95 误差；
- repeatability coefficient of variation across camera poses / 不同拍摄姿态的重复性变异系数；
- calibration failure rate and reasons / 标定失败率与原因；
- sensitivity-interval empirical coverage / 敏感性区间对参考值的经验覆盖率；
- runtime and peak memory on the 24 GB MacBook Pro / 24GB MacBook Pro 的运行时间和峰值内存。

Do not write “millimetre-level accuracy” on a résumé until your own held-out field measurements support that claim.

在自己的留出现场测量支持之前，不要在简历写“毫米级精度”。

## Why this is portfolio-grade / 为什么这比普通 Demo 难

This component crosses computer vision, computational geometry, graph algorithms, projective geometry, uncertainty analysis, reproducibility, privacy, and field experimental design. It also contains explicit failure states: missing markers, invalid quadrilaterals, absent masks, output collisions, and uncalibrated pixel-only mode.

这个模块同时涉及计算机视觉、计算几何、图算法、射影几何、不确定性分析、可复现性、隐私与现场实验设计；并对缺少标记、无效四边形、空掩膜、输出冲突和未标定像素模式进行明确失败处理。

Research context / 研究背景：

- [Deep CNN ensemble for pavement crack detection and measurement](https://arxiv.org/abs/2002.03241): probability maps, skeleton extraction, and crack length/width measurement.
- [Segment-based pavement crack quantification](https://www.sciencedirect.com/science/article/pii/S0926580518312196): skeleton decomposition and segment-aware width measurement.
- [OpenCV homography tutorial](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html): planar point mapping and perspective geometry.

These sources motivate the engineering choices; they do not validate this repository's field accuracy. That validation must come from the protocol above.

这些资料解释方法依据，但不能替本项目背书现场精度；现场精度必须由上面的亲身实验获得。
