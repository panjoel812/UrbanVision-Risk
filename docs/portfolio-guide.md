# Portfolio and Interview Guide / 简历与面试表达

## What makes v4.5 different / v4.5 的差异化

Many public road-damage projects combine RDD2022, one YOLO checkpoint, and an upload page. UrbanVision-Risk v4.5 links detection, reliability, metrology, and operator review. Its review layer deterministically ranks parameter disagreement, tracks review coverage, and adds a bidirectionally synchronized ROI editor: pointer coordinates from a magnified viewport are transformed into original-image pixels and committed to the same immutable mask-difference audit.

许多公开道路检测项目只是 RDD2022、一个 YOLO 权重和上传页面。UrbanVision-Risk v4.5 把检测、可靠性、量测和操作员复核连接起来：复核层确定性排序参数分歧、记录覆盖率，并加入双向同步 ROI 编辑器，把放大视口中的指针坐标转换为原图像素，再提交到同一套不可变掩膜差异审计。

## Resume bullets / 简历要点

Use only metrics you can reproduce. A concise English version:

- Built a fully local road-infrastructure inspection system on Apple Silicon, training and evaluating a five-class YOLO detector on a deterministic RDD2022 pipeline and integrating explainable maintenance-priority scoring with immutable SHA-256 provenance.
- Designed a three-view reliability layer (640/1280/horizontal flip) with class-aware IoU association, confidence-weighted box fusion, localization-stability and uncertainty metrics, safety gating, and a deterministic active-learning review queue.
- Implemented a calibrated crack-metrology engine from first principles: Zhang-Suen skeletonization, graph-geodesic length, endpoint/junction topology, distance-transform width distributions, PCA orientation, tortuosity, and box-counting complexity.
- Built an ArUco-based field calibration workflow with exact-size printable SVG fiducials, semantic four-marker detection, homography rectification, privacy-minimized provenance, and deterministic Monte Carlo/boundary-perturbation sensitivity intervals.
- Engineered a human-in-the-loop review layer that perturbs proposal sensitivity at three levels, ranks connected disagreement regions into a bounded operator worklist, and audits inspected IDs, priority-weighted coverage, immutable hashes, pixel deltas, and IoU.
- Implemented a synchronized ROI loupe with aspect-preserving viewport math, CSS-to-canvas-to-source coordinate transforms, direct high-magnification brush/eraser editing, shared undo history, and original-resolution evidence output.
- Shipped the model as a loopback-only FastAPI product with bilingual UI, MPS inference, optional local Ollama narratives, privacy headers, structured failure recovery, and a comprehensive automated test suite.

中文版本：

- 在 Apple Silicon 上构建完全本地的道路基础设施巡检系统，完成 RDD2022 确定性数据流水线、五类 YOLO 训练/留出评估、可解释维护优先级与 SHA-256 不可变来源审计。
- 设计 640/1280/水平镜像三视图可靠性层，实现分类感知 IoU 关联、置信度加权框融合、定位稳定性/不确定性量化、安全门控和确定性主动学习复核队列。
- 从底层实现标定裂缝量测引擎：Zhang-Suen 骨架化、图测地长度、端点/分叉拓扑、距离变换宽度分布、PCA 方向、曲折度和盒计数复杂度。
- 构建 ArUco 现场标定流程，支持精确尺寸可打印 SVG、四标记语义检测、单应性矫正、隐私最小化来源记录，以及确定性 Monte Carlo/边界扰动敏感性区间。
- 设计人机协同复核层，在三个灵敏度下扰动候选算法，把连通分歧区域排序为有上限的操作员工作清单，并审计检查编号、优先影响覆盖率、不可变摘要、像素增删量与 IoU。
- 实现同步 ROI 放大编辑器，包括保持宽高比的视口计算、CSS—Canvas—原图坐标变换、高倍率画笔/橡皮修订、共享撤销历史与原分辨率证据输出。
- 使用 FastAPI 交付仅监听本机回环地址的双语产品，支持 Apple MPS、本地 Ollama 可选说明、隐私响应头、结构化故障恢复与完整自动化测试。

## Interview deep-dive / 面试追问

Be prepared to explain these decisions:

1. Why maximum confidence is optimistic and mean confidence is used after view association.
2. Why horizontal flipping tests invariance but cannot prove semantic correctness.
3. Why class-aware IoU association must prevent two boxes from the same view entering one cluster.
4. How active learning converts production uncertainty into the next dataset version.
5. Why a zero detection and an unstable consensus must never be displayed as a safe road.
6. Why `reliability.json` and content digests matter for reproducibility and incident review.
7. Why a bounding box cannot support crack-width metrology and why the mask remains independent evidence.
8. How homography assumptions fail on non-planar pavement and why markers must be coplanar.
9. Why graph-edge length is different from counting skeleton pixels.
10. Why the reported interval is a sensitivity envelope rather than a certified confidence interval.
11. Why sensitivity disagreement is useful for review triage but cannot be interpreted as calibrated epistemic or aleatoric uncertainty.

准备回答：为什么不取最高置信度、镜像一致性有什么局限、为什么聚类必须限制每个视图只贡献一次、主动学习如何形成数据闭环、为什么零检测不能解释为安全、为什么框不能量测裂缝宽度、单应性何时失效、骨架像素数为什么不等于测地长度，以及敏感性区间为什么不是认证置信区间。

## Five-minute demo / 五分钟演示

1. Run `urbanvision_risk.metrology.demo` and open `overlay.jpg`, `rectified-overlay.jpg`, and `measurement.json`.
2. Explain why the green centerline is a graph, then point to endpoints, junctions, geodesic length, and the width distribution.
3. Show the four generated ArUco SVG files and describe the marker-center field measurement.
4. Show that deleting calibration from the command produces `pixel_only` rather than fake millimetres.
5. Start the app in default `consensus` mode, upload one clear image, and explain the three-view reliability evidence.
6. Open `/api/review-queue?limit=20` and connect detection uncertainty to human review.
7. Finish with your own held-out field errors and limitations, not a certified-safety claim.

## Claims to avoid / 不要夸大的内容

Do not claim autonomous road-safety decisions, certified millimetre accuracy, complete defect taxonomy, production city-scale validation, or causal engineering risk. You may say the software implements calibrated physical measurement only when a valid coplanar field calibration and reviewed mask were supplied. Report real accuracy only after completing the held-out field protocol.

不要声称自动道路安全决策、认证毫米级精度、缺陷类别完整、城市规模生产验证或因果工程风险。只有在提供有效同平面现场标定和人工复核掩膜时，才能说软件实现了真实单位量测；只有完成留出现场实验后，才能报告精度。真正高级的表达是：系统能检测、能量测、能保留证据、能暴露误差来源，也知道何时拒绝回答。
