# UrbanVision-Risk v4.9 Field Metrology / 现场裂缝量测

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

When a saved human review contains at least one structured disposition, Version 4.7 creates `active-learning-feedback.zip` beside `measurement.json`. Each dispositioned target contains four aligned PNGs: the source ROI, immutable proposal mask, final reviewed mask, and sensitivity-disagreement layer. The crop adds 15% context with an eight-pixel minimum and is proportionally reduced when it exceeds 512,000 pixels; masks always use nearest-neighbour resizing.

当保存的人工复核至少包含一项结构化处置时，v4.7 会在 `measurement.json` 旁生成 `active-learning-feedback.zip`。每个已处置目标包含四张对齐 PNG：原图 ROI、不可变候选掩膜、最终复核掩膜和灵敏度分歧层。裁剪增加 15% 上下文且至少 8 像素；超过 512,000 像素时等比例缩小，掩膜始终采用最近邻缩放。

`manifest.json` records original and exported crop geometry, scale, rank, priority, disposition, optional note, and SHA-256 for every PNG. It also binds the package to the source and immutable measurement digests. ZIP entries use fixed timestamps and sorted paths, so identical entry content produces reproducible archive bytes. No absolute path is stored.

`manifest.json` 记录原始和导出裁剪几何、比例、排名、优先级、处置、可选备注以及每张 PNG 的 SHA-256，并把反馈包绑定到源图和不可变量测摘要。ZIP 成员使用固定时间戳和排序路径，因此相同成员内容能产生可复现压缩包；不会保存绝对路径。

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

The assignment unit is the complete `source_sha256` group, never an individual ROI. A seeded greedy allocator approximates the requested train/validation/test ratios while guaranteeing that one source digest cannot cross splits. The JSON records all three pairwise source intersections, so the guarantee is machine-verifiable. This protects against same-file leakage; it cannot prove that two different files do not show the same physical location.

分配单位是完整的 `source_sha256` 组，而不是单个 ROI。带种子的贪心分配器在逼近训练/验证/测试比例时，保证同一源图摘要不会跨切分。JSON 记录三个两两源图交集，因此该保证可以机器验证。它能防止同一文件泄漏，但不能证明两个不同文件没有拍摄同一实际地点。

The plan stays `not_training_ready` when it has too few independent sources, an empty split, pending privacy or label review, malformed packages, a truncated inventory, or a failed overlap audit. Even with no blocker, its status is `candidate_plan_requires_training_approval` and `training_authorized` remains `false`. A separate accountable decision is required before materialization or training.

当独立原图不足、任一切分为空、隐私或标签复核待完成、存在损坏反馈包、清单被截断或交集审计失败时，策划保持 `not_training_ready`。即使没有阻断项，其状态也只是 `candidate_plan_requires_training_approval`，且 `training_authorized` 始终为 `false`；真正落盘为数据集或训练前仍需单独的责任审批。

Images larger than two million pixels are processed on a downsampled work raster and the binary proposal is restored to the exact source resolution. This bounds memory and runtime without sending pixels to a cloud service. The sensitivity slider changes proposal recall; it is not a calibrated probability or YOLO confidence.

超过 200 万像素的图片会在缩小的工作栅格上处理，再把二值候选恢复到原图精确分辨率，从而限制内存和耗时，且不发送到云端。灵敏度滑块改变候选召回范围，不是经过标定的概率或 YOLO 置信度。

The yellow layer is triage guidance, not model uncertainty calibration: it only answers “where did this deterministic algorithm change under a nearby parameter perturbation?” Stable green pixels can still be wrong, and real cracks can still be missed at all three settings.

黄色层是复核分流提示，不是模型不确定性校准：它只回答“确定性算法在邻近参数扰动下，哪些位置发生变化”。稳定的绿色像素仍可能是误检，三个设置都未选中的真实裂缝仍可能漏检。

An empty proposal is returned as unusable, and a proposal covering more than 35% of the image is rejected as too broad instead of being painted automatically.

空候选会标为不可用；候选覆盖超过整图 35% 时会以“范围过宽”拒绝自动载入，而不是把大面积噪声涂到画布上。

The proposal becomes the editable green base layer. Every later brush or eraser stroke is replayed above that immutable base. When metrology is submitted, `measurement.json` records the proposal ID and schema, proposal/final mask hashes, human-added pixels, human-removed pixels, changed-image ratio, and proposal-to-final IoU.

候选会成为可编辑的绿色底稿，后续画笔或橡皮笔迹都在不可变底稿之上重放。提交量测时，`measurement.json` 会记录候选编号与版本、候选/最终掩膜摘要、人工增加像素、人工删除像素、整图改动比例和候选—最终 IoU。

The first automatic pixel run records `review_state: automatic_draft` and `mask.origin: local_proposal_automatic_draft`. Saving after review records `review_state: human_reviewed`. This distinction is a workflow audit label, not a claim that the mask is objectively correct.

第一次自动像素量测会记录 `review_state: automatic_draft` 与 `mask.origin: local_proposal_automatic_draft`；人工复核后保存则记录 `review_state: human_reviewed`。这个字段是流程审计标签，不等于系统宣称掩膜客观正确。

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
