# UrbanVision-Risk v3.0 Field Metrology / 现场裂缝量测

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

For a real image, upload it once. Detection and the independent mask proposal start automatically in parallel. Review the green proposal with the brush and eraser, choose a calibration mode, and run local metrology. The mask is exported at the source image's original resolution rather than the displayed CSS size.

对真实图片只需上传一次，检测与独立掩膜建议会并行自动启动。用画笔和橡皮复核绿色候选，选择标定模式，再运行本地量测。网页导出的掩膜保持原图分辨率，不会使用屏幕显示尺寸代替。

The circular cursor shows the exact brush diameter. Every brush move appears immediately as a green overlay; erasing removes both the mask alpha and the green overlay. The browser exports a transparent PNG, and the local service composites transparency onto black before thresholding, so unpainted pixels cannot accidentally become foreground.

圆形光标就是实际笔宽；拖动时绿色轨迹会立即显示，橡皮会同时清除掩膜透明度和绿色覆盖层。浏览器导出透明 PNG，本地服务先把透明区域合成到黑色背景再二值化，因此未绘制区域不会误变成前景。

## Human-in-the-loop mask proposal / 人机协同候选掩膜

After choosing a source image, the page automatically runs three complementary, deterministic proposal views on the Mac—there is no separate proposal button:

选择原图后，页面会自动在 Mac 上运行三个互补、确定性的建议视图，不再需要单独点击建议按钮：

1. multi-scale morphological blackhat for locally dark structures / 多尺度形态学黑帽提取局部暗结构；
2. multi-scale Hessian eigenvalue response for thin dark ridges / 多尺度 Hessian 特征值响应提取细暗脊；
3. strong-seed/weak-neighbour hysteresis with connected-component geometry filtering / 强种子—弱邻域迟滞与连通区域几何过滤。

Images larger than two million pixels are processed on a downsampled work raster and the binary proposal is restored to the exact source resolution. This bounds memory and runtime without sending pixels to a cloud service. The sensitivity slider changes proposal recall; it is not a calibrated probability or YOLO confidence.

超过 200 万像素的图片会在缩小的工作栅格上处理，再把二值候选恢复到原图精确分辨率，从而限制内存和耗时，且不发送到云端。灵敏度滑块改变候选召回范围，不是经过标定的概率或 YOLO 置信度。

An empty proposal is returned as unusable, and a proposal covering more than 35% of the image is rejected as too broad instead of being painted automatically.

空候选会标为不可用；候选覆盖超过整图 35% 时会以“范围过宽”拒绝自动载入，而不是把大面积噪声涂到画布上。

The proposal becomes the editable green base layer. Every later brush or eraser stroke is replayed above that immutable base. When metrology is submitted, `measurement.json` records the proposal ID and schema, proposal/final mask hashes, human-added pixels, human-removed pixels, changed-image ratio, and proposal-to-final IoU.

候选会成为可编辑的绿色底稿，后续画笔或橡皮笔迹都在不可变底稿之上重放。提交量测时，`measurement.json` 会记录候选编号与版本、候选/最终掩膜摘要、人工增加像素、人工删除像素、整图改动比例和候选—最终 IoU。

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
