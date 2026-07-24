# UrbanVision-Risk v5.8 Dataset-Shift Monitoring App / 数据漂移监测本地应用指南

## Finished product / 最终产品

**English:** v5.8 automatically compares each batch with its historical local baseline through bounded visual features, a deterministic MMD permutation test, and nearest-neighbor coverage. It abstains when sample evidence is insufficient. v5.7 cumulative dual-axis readiness, batch-scoped evidence, YOLO × segmentation arbitration, content-aware self-healing, and bounded Apple MPS execution remain active.

**中文：** v5.8 会通过有界视觉特征、确定性 MMD 置换检验和最近邻覆盖率，自动比较每个批次与本机历史基线；样本证据不足时会拒答。v5.7 累计双轴就绪、本批次证据、YOLO × 分割仲裁、内容感知自愈和 Apple MPS 有界执行继续生效。

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

- policy-bounded autopilot from upload through governed snapshot preflight / 从上传到受治理快照预检的策略约束自动驾驶；
- deterministic built-in calibrated demo / 确定性内置标定 Demo；
- original-resolution mask brush, eraser, undo, and clear / 原分辨率掩膜画笔、橡皮、撤销和清空；
- pixel-only, manual `TL → TR → BR → BL`, and automatic ArUco modes / 仅像素、手动四点和 ArUco 自动模式；
- physical width, height, unit, rectification resolution, corner sigma, Monte Carlo sample count, and boundary sensitivity controls / 真实宽高、单位、矫正分辨率、点位 sigma、Monte Carlo 样本数和边界敏感性设置；
- overlay, rectified overlay, width heatmap, skeleton, topology, physical geometry, interval evidence, and complete `measurement.json` / 叠加图、矫正图、宽度热图、骨架、拓扑、真实几何量、区间证据和完整 JSON；
- immutable local output under `results/metrology/<run-id>/` / 保存到不可覆盖的本地量测目录。

One upload automatically starts transform-consensus detection and the independent local crack proposal in parallel. Ranked disagreement, synchronized correction, structured dispositions, deterministic feedback export, quality gates, and the bounded registry remain in one workflow. Version 5.0 extends `/api/metrology/feedback-curations` with a visual near-duplicate split firewall. After exact duplicate removal, it computes pairwise Hamming distance between bounded sets of 64-bit source-ROI fingerprints. Deterministic single-linkage union-find makes every transitively connected source group an indivisible allocation unit.

上传一次仍会并行启动变换共识检测和本地裂缝建议；排序分歧、同步修订、结构化处置、确定性反馈导出、质量门控和有界台账都位于同一流程。v5.0 为 `/api/metrology/feedback-curations` 增加视觉近重复切分防火墙：精确去重后，在每个来源有界的 64 位 ROI 指纹集合之间计算两两汉明距离，再由确定性单链并查集把所有传递相连的来源变成不可分割分配单元。

In the feedback panel, choose a seed, minimum independent visual-group count, and a Hamming threshold from 0 to 16 bits, then record whether privacy and label QA are complete. The default threshold is 4 bits. Each split reports items, exact sources, and visual groups. The audit separately lists exact-source and visual-group intersections plus the source pair, fingerprint pair, and distance behind every near-duplicate link. Empty holdouts, insufficient independent groups, malformed packages, truncated fingerprint inventories, missing governance confirmations, or overlap remain blockers.

在反馈区域选择种子、最少独立视觉簇数量和 0–16 bit 汉明阈值，再记录隐私复核与标签抽检是否完成。默认阈值为 4 bit。每个切分同时显示样本数、精确来源数和视觉簇数；审计分别列出精确来源与视觉簇交集，并记录每条近重复连接的来源对、指纹对和距离。留出集为空、独立簇不足、反馈包损坏、指纹清单截断、治理确认缺失或发现交集都会保留为阻断项。

The plan remains immutable JSON under `results/metrology/curations/` and references preserved ZIP members rather than extracting or deleting them. A perceptual link is deliberately one-way safety evidence: it forces co-location in a split, but it does not prove two files are identical or show the same physical road.

策划仍以不可覆盖 JSON 保存到 `results/metrology/curations/`，只引用保留 ZIP 内的成员，不解压或删除原包。感知连接只是单向安全证据：它会强制两个来源进入同一切分，但不能证明两个文件完全相同或拍摄了同一实际路段。

Version 5.1 adds **Verify content-addressed snapshot** directly below the curation result. It binds the current curation JSON by SHA-256, confirms that every package manifest still matches the curated inventory, and reads only each selected `source_roi` and `final_mask` member. Every member is size-bounded and hash-verified before OpenCV decoding. The source and target must share dimensions, remain under the ROI pixel ceiling, and the target may contain only 0 and 255.

v5.1 在策划结果下方直接加入 **验证内容寻址快照**。它用 SHA-256 绑定当前策划 JSON，确认每个反馈包清单仍与策划时的清单一致，并且只读取入选数据对的 `source_roi` 和 `final_mask` 成员。每个成员先经过大小限制和摘要核对，再由 OpenCV 解码；原图与目标掩膜必须同尺寸、不超过 ROI 像素上限，目标只能包含 0 和 255。

Preflight independently recomputes exact-source, visual-group, and identical source-member overlaps across splits. It reports verified/invalid pairs, bytes read, empty-mask counts, foreground ratios, and dispositions. Canonical sorted leaves bind split, run, hotspot, source, visual group, source-member hash, and target-member hash. Leaf and parent domains use distinct `0x00` and `0x01` prefixes; odd nodes are duplicated. The resulting immutable JSON is stored under `results/metrology/snapshots/`.

预检会独立重算精确来源、视觉簇和相同原图成员在切分间的交集，并报告通过/无效数据对、读取字节、空掩膜、前景比例和处置分布。规范化排序叶节点绑定切分、运行、热点、来源、视觉簇、原图成员摘要和目标成员摘要；叶与父节点分别使用 `0x00`、`0x01` 域前缀，奇数节点复制末项。最终不可覆盖 JSON 保存到 `results/metrology/snapshots/`。

The Merkle root proves that one exact set of references produced the recorded root; it does not prove privacy clearance, label correctness, or model quality. `training_authorized` remains `false`.

Merkle 根只能证明某一精确引用集合产生了记录中的根，不能证明隐私合规、标签正确或模型质量；`training_authorized` 仍为 `false`。

Version 5.2 checks **Autopilot** by default. It dispositions ranked hotspots with the published overlap rule, saves a `machine_reviewed_candidate`, builds curation, and invokes snapshot preflight without more clicks. Provenance records `machine_heuristic`; selected machine labels add a training blocker until a human operator independently approves them. Brush/eraser correction remains available as an explicit `human_reviewed` override.

v5.2 默认勾选 **自动驾驶**。它使用公开的重叠规则处置排序热点，保存 `machine_reviewed_candidate`，随后无需额外点击即可生成策划并调用快照预检。来源记录明确写入 `machine_heuristic`；入选机器标签会添加训练阻断，直到人工操作员独立批准。画笔/橡皮修订仍可作为明确的 `human_reviewed` 覆盖版本保存。

Version 5.3 turns that single-image path into a **resilient batch autopilot**. Keep Autopilot enabled, select up to 100 images in one file dialog, and watch every queue item move through pending, running, complete, or failed. The browser deliberately processes one image at a time so Apple MPS memory remains bounded; detection and proposal still execute concurrently inside that image. An exception on one item is recorded in the live queue and does not cancel later items.

v5.3 把单图路径扩展为 **弹性批量自动驾驶**。保持自动驾驶开启，在一次文件选择中最多选择 100 张图片，即可观察每项依次进入等待、运行、完成或失败状态。浏览器刻意一次只处理一张图片，从而限制 Apple MPS 内存；但该图片内部的检测与候选仍并发执行。某一项发生异常时只会在当前队列中记录，不会取消后续图片。

After the queue ends, `POST /api/metrology/autopilot-batches/finalize` sends only successful run IDs to the service. The service reloads and revalidates every measurement, creates immutable batch-scoped and cumulative curation/snapshot records, then automatically compares the current sources with historical sources. The immutable `urbanvision-autopilot-batch-v1.4.0` binds `governance`, `cumulative_registry`, and `distribution_monitoring`. Historical samples never enter the current-batch evidence, and current source digests are excluded from the drift reference.

队列结束后，`POST /api/metrology/autopilot-batches/finalize` 只把成功运行编号交给服务端。服务端重新读取并复核每份量测，生成本批次与累计策划/快照，再自动比较当前来源和历史来源。`urbanvision-autopilot-batch-v1.4.0` 会绑定 `governance`、`cumulative_registry` 与 `distribution_monitoring`；历史样本不会进入本批次证据，当前来源摘要也会从漂移参考基线中排除。

Version 5.4 adds two independent deduplication boundaries. The browser hashes each eligible file with `crypto.subtle.digest("SHA-256", ...)`, retains the first occurrence, and marks later byte-identical selections as `duplicate`. The service does not trust that decision: it compares each browser digest with the SHA-256 already preserved in `measurement.json`, rejects repeated server-side source evidence, and verifies that completed + failed + duplicate counts equal the selected count.

v5.4 增加两道相互独立的去重边界。浏览器使用 `crypto.subtle.digest("SHA-256", ...)` 计算每个合格文件的摘要，只保留第一次出现的内容，后续完全相同文件标记为 `duplicate`。服务端不会盲信浏览器：它把浏览器摘要与 `measurement.json` 已保存的 SHA-256 逐项比较，拒绝服务端重复来源，并验证完成数 + 失败数 + 去重数必须等于选择总数。

Only `pipeline_incomplete` and `unexpected_error` are retryable, with `MAX_BATCH_ATTEMPTS = 2`. Unsupported format, over 15 MiB, decode failure, and over 20 megapixels are deterministic failures and are not retried. The `urbanvision-autopilot-batch-v1.4.0` ledger records validated aggregate counts, retry policy, digest-match count, arbitration bindings, dual-scope governance, and drift-audit references without persisting the live queue's filenames.

只有 `pipeline_incomplete` 与 `unexpected_error` 可以重试，且 `MAX_BATCH_ATTEMPTS = 2`。格式不支持、超过 15 MiB、解码失败或超过 2000 万像素属于确定性失败，不会重试。`urbanvision-autopilot-batch-v1.4.0` 账本记录已校验汇总数、重试策略、摘要匹配数、仲裁绑定、双范围治理和漂移审计引用，但不会保存页面队列里的文件名。

Version 5.5 adds **YOLO × segmentation evidence arbitration** automatically after both parallel channels finish. `POST /api/evidence/arbitrate` reloads the immutable inspection manifest, prediction, risk, measurement, and final mask. It rejects a mismatched upload SHA-256, changed JSON hash, run identity mismatch, dimension mismatch, or mask-evidence mismatch before comparing pixels.

v5.5 在两个并行通道结束后自动执行 **YOLO × 分割证据仲裁**。`POST /api/evidence/arbitrate` 重新读取不可变巡检清单、预测、风险、量测和最终掩膜；在比较像素前，会拒绝上传 SHA-256 不一致、JSON 摘要变化、运行身份不一致、尺寸不一致或掩膜证据不一致。

The policy compares only crack classes D00, D10, and D20 with the segmentation mask. It reports `proposal_only_semantic_miss`, `detector_only_semantic_evidence`, `cross_channel_supported`, `spatial_disagreement`, or `inconclusive_no_positive_evidence`. A proposal needs at least 64 pixels and 0.005% image coverage; cross-channel support requires at least 10% of proposal pixels inside semantic boxes. These published constants are operational rules—not learned confidence, probability, or ground truth.

策略只把 D00、D10 和 D20 裂缝类别与分割掩膜比较，输出 `proposal_only_semantic_miss`、`detector_only_semantic_evidence`、`cross_channel_supported`、`spatial_disagreement` 或 `inconclusive_no_positive_evidence`。候选至少需要 64 像素和画面 0.005% 覆盖；双通道支持要求至少 10% 候选像素落在语义框内。这些公开常量是运行规则，不是学习置信度、概率或真值。

Every successful queue item now needs detection, metrology, and arbitration. The immutable `urbanvision-cross-channel-arbitration-v1.0.0` record is stored under `results/metrology/arbitrations/` and then SHA-256-bound into the batch ledger. Agreement strengthens evidence but never proves correctness; disagreement forces abstention but does not prove which channel is wrong.

每个成功队列项现在必须同时完成检测、量测和仲裁。不可覆盖的 `urbanvision-cross-channel-arbitration-v1.0.0` 记录保存在 `results/metrology/arbitrations/`，随后以 SHA-256 绑定进批次账本。一致只能增强证据，不能证明正确；分歧会触发拒答，但不能证明哪个通道错误。

Version 5.6 adds **self-remediating data readiness**. The allocator first orders complete visual groups deterministically, then reserves one group for every split with a positive ratio whenever enough groups exist. With three independent groups, train, validation, and test therefore become non-empty automatically; no ROI or exact source can cross a split. Remaining groups are assigned by ratio deficit.

v5.6 增加 **自修复数据就绪**。分配器先对完整视觉簇做确定性排序，只要视觉簇数量足够，就为每个正比例切分预留一个视觉簇。因此三个独立簇会自动形成非空 train、val、test；任何 ROI 或精确来源都不会跨切分，剩余视觉簇再按比例缺口分配。

Version 5.7 writes `urbanvision-feedback-curation-v2.3.0`. Its backward-compatible `readiness.blockers` list is now classified into `readiness.technical` and `readiness.governance`. Too few independent sources, empty positive-ratio splits, corrupt packages, truncated inventories, and leakage are technical blockers. Privacy review, label QA, and independent approval of machine labels are governance blockers. `urbanvision-feedback-snapshot-preflight-v1.2.0` separately reports byte-integrity status and inherited governance state.

v5.7 写入 `urbanvision-feedback-curation-v2.3.0`。兼容旧调用者的 `readiness.blockers` 仍保留，但现在被分类到 `readiness.technical` 与 `readiness.governance`：独立来源不足、正比例切分为空、包损坏、清单截断和泄漏属于技术阻断；隐私复核、标签抽检和机器标签独立批准属于治理阻断。`urbanvision-feedback-snapshot-preflight-v1.2.0` 会分别报告字节完整性状态和继承的治理状态。

This distinction explains the earlier “67/67 verified but not ready” output. It means all 67 referenced image-mask pairs passed structural and hash verification, while the registry still lacked enough independent full-frame sources and machine labels lacked accountable approval. v5.7 displays those facts independently. Across later uploads, the cumulative source and visual-group counts increase automatically; no manual merge button is required.

这也解释了之前“67/67 已验证但尚未就绪”：67 个原图—掩膜引用都通过了结构和摘要验证，但独立全幅原图仍不足，且机器标签尚无责任人批准。v5.7 会把这些事实分开显示；以后继续上传时，累计独立原图和视觉簇数量会自动增加，不需要手动合并按钮。

## Automatic dataset-shift audit / 自动数据漂移审计

`urbanvision-feedback-drift-audit-v1.0.0` uses one source-level feature vector per exact `source_sha256`, averaging at most eight verified ROIs so a source with many hotspots cannot dominate the test. Its nine bounded features cover luminance mean/variance, saturation, dark-pixel ratio, edge density, Laplacian texture energy, 16-bin luminance entropy, final-mask foreground ratio, and landscape geometry.

`urbanvision-feedback-drift-audit-v1.0.0` 为每个精确 `source_sha256` 生成一个来源级特征向量，每个来源最多平均八个已验证 ROI，避免热点多的图片支配检验。九个有界特征包括亮度均值/标准差、饱和度、暗像素比例、边缘密度、Laplacian 纹理能量、16 档亮度熵、最终掩膜前景比例与横向几何比例。

The audit computes biased RBF-MMD and calibrates it with 199 deterministic permutations. It separately compares each current source with its nearest historical neighbor and derives a robust threshold from historical leave-one-out distances. At least three current and five historical independent sources are required. Before that point the correct result is `insufficient_or_invalid_evidence`, not “no drift.”

审计计算有偏 RBF-MMD，并用 199 次确定性置换校准；同时把每个当前来源与最近历史来源比较，并由历史留一最近邻距离推导稳健阈值。至少需要 3 个当前独立来源和 5 个历史独立来源；达到门槛之前，正确结果是 `insufficient_or_invalid_evidence`，而不是“没有漂移”。

A detected difference is a monitoring warning. It can reveal changing lighting, camera framing, pavement texture, damage coverage, or crop geometry, but cannot identify causality or prove model degradation. No drift result changes `training_authorized`.

检测到差异只产生监测警告。它可以暴露光照、拍摄构图、路面纹理、缺陷覆盖或裁剪几何变化，但不能识别因果关系或证明模型性能下降；任何漂移结果都不会改变 `training_authorized`。

The vetted external reference is the official [RDD2022 repository](https://github.com/sekilab/RoadDamageDetector), which provides multi-country D00/D10/D20/D40 bounding-box annotations and identifies the image license as CC BY-SA 4.0. It remains a detector benchmark, not a substitute for approving locally generated segmentation masks. A newly published RDD2022-derived mask record was not auto-imported because its Zenodo CC BY metadata does not by itself resolve the upstream ShareAlike obligation.

经过核实的外部参考是官方 [RDD2022 仓库](https://github.com/sekilab/RoadDamageDetector)：它提供多国家 D00/D10/D20/D40 框标注，并明确图片采用 CC BY-SA 4.0。它只作为检测器基准，不替代对本地生成分割掩膜的批准。新发布的 RDD2022 派生掩膜记录没有被自动导入，因为其 Zenodo CC BY 元数据本身不能解释上游 ShareAlike 义务如何落实。

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
