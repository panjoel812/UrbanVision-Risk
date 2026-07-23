# Portfolio and Interview Guide / 简历与面试表达

## What makes v2.0 different / v2.0 的差异化

Many public road-damage projects combine RDD2022, one YOLO checkpoint, and a Streamlit or Gradio upload page. UrbanVision-Risk v2.0 instead demonstrates the full local ML lifecycle: deterministic data preparation, training and held-out evaluation, transform-consensus inference, uncertainty and safety gating, explainable domain scoring, immutable provenance, a human-review queue, tests, and a bilingual local product.

许多公开道路检测项目只是 RDD2022、一个 YOLO 权重和 Streamlit/Gradio 上传页面。UrbanVision-Risk v2.0 展示完整本地 ML 生命周期：确定性数据准备、训练与留出评估、变换共识推理、不确定性与安全门控、可解释领域评分、不可变来源记录、人工复核队列、自动测试和双语本地产品。

## Resume bullets / 简历要点

Use only metrics you can reproduce. A concise English version:

- Built a fully local road-infrastructure inspection system on Apple Silicon, training and evaluating a five-class YOLO detector on a deterministic RDD2022 pipeline and integrating explainable maintenance-priority scoring with immutable SHA-256 provenance.
- Designed a three-view reliability layer (640/1280/horizontal flip) with class-aware IoU association, confidence-weighted box fusion, localization-stability and uncertainty metrics, safety gating, and a deterministic active-learning review queue.
- Shipped the model as a loopback-only FastAPI product with bilingual UI, MPS inference, optional local Ollama narratives, privacy headers, structured failure recovery, and a comprehensive automated test suite.

中文版本：

- 在 Apple Silicon 上构建完全本地的道路基础设施巡检系统，完成 RDD2022 确定性数据流水线、五类 YOLO 训练/留出评估、可解释维护优先级与 SHA-256 不可变来源审计。
- 设计 640/1280/水平镜像三视图可靠性层，实现分类感知 IoU 关联、置信度加权框融合、定位稳定性/不确定性量化、安全门控和确定性主动学习复核队列。
- 使用 FastAPI 交付仅监听本机回环地址的双语产品，支持 Apple MPS、本地 Ollama 可选说明、隐私响应头、结构化故障恢复与完整自动化测试。

## Interview deep-dive / 面试追问

Be prepared to explain these decisions:

1. Why maximum confidence is optimistic and mean confidence is used after view association.
2. Why horizontal flipping tests invariance but cannot prove semantic correctness.
3. Why class-aware IoU association must prevent two boxes from the same view entering one cluster.
4. How active learning converts production uncertainty into the next dataset version.
5. Why a zero detection and an unstable consensus must never be displayed as a safe road.
6. Why `reliability.json` and content digests matter for reproducibility and incident review.

准备回答：为什么不取最高置信度、镜像一致性有什么局限、为什么聚类必须限制每个视图只贡献一次、主动学习如何形成数据闭环、为什么零检测不能解释为安全，以及为什么可靠性文件和内容摘要对复现与事故审计重要。

## Five-minute demo / 五分钟演示

1. Start the app in default `consensus` mode and upload one clear image.
2. Explain the three views and show accepted support, stability, uncertainty, and fused boxes.
3. Upload a difficult image and show score withholding or the review recommendation.
4. Open `/api/review-queue?limit=20` to demonstrate the human-in-the-loop data loop.
5. Open the inspection directory and connect `prediction.json`, `reliability.json`, `risk.json`, and the manifest digests.
6. Finish with held-out metrics and the limitations instead of claiming certified safety.

## Claims to avoid / 不要夸大的内容

Do not claim autonomous road-safety decisions, calibrated physical crack dimensions, complete defect taxonomy, production city-scale validation, or causal engineering risk. The technically strong story is that the system detects, measures its own instability, preserves evidence, and knows when to defer to people.

不要声称自动道路安全决策、物理裂缝尺寸已标定、缺陷类别完整、已完成城市规模生产验证或得到了因果工程风险。真正高级的表达是：系统能检测，也能衡量自身不稳定性，保留证据，并知道何时交给人。
