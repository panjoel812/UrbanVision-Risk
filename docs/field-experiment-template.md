# v3.0 Field Experiment Record / 现场实验记录模板

Copy this section once per calibrated road plane. Keep personal locations and faces out of the committed version.

每个标定路面复制一份。提交到 GitHub 的版本不能包含私人地点、车牌、人脸或绝对本机路径。

## Identity / 标识

- Anonymous plane ID / 匿名路面编号：
- Capture date (local) / 拍摄日期：
- Operator / 操作者：
- Camera and lens / 相机与镜头：
- Image resolution / 图片分辨率：
- Weather and lighting / 天气与光照：

## Calibration / 标定

- TL/TR/BR/BL marker IDs / 标记 ID：17 / 23 / 42 / 56
- Measured center width / 中心真实宽度：
- Measured center height / 中心真实高度：
- Unit / 单位：
- Tape or reference instrument / 参考量具：
- ArUco minimum perimeter in pixels / 最小标记周长像素：
- Calibration quadrilateral image ratio / 标定四边形画面占比：
- Point sigma used / 标定点扰动 sigma：

## Ground truth / 人工参考值

| Segment ID | Reference length | Width station | Reference width | Instrument | Second operator? |
|---|---:|---:|---:|---|---|
| | | | | | |

## Software output / 软件结果

- Git commit:
- Command:
- Output name:
- Mask author and review status / 掩膜作者与复核状态：
- Centerline length:
- Length sensitivity p05 / median / p95:
- Mean width:
- Width p95:
- Components / endpoints / junctions:
- Runtime:
- Peak memory:

## Error analysis / 误差分析

- Absolute length error:
- Percentage length error:
- Width errors at declared stations:
- Camera-pose repeatability:
- Did the reference fall inside the sensitivity interval?
- Known failure factors / 已知失败因素：
- Human decision: accept, relabel mask, recalibrate, or reject / 人工决定：
