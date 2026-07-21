# Local Data / 本地数据

`downloads/` stores the official archive, `raw/` stores immutable extraction, and `processed/` stores YOLO-format train/val/test data. These generated directories are ignored by Git.

`downloads/` 保存官方压缩包，`raw/` 保存不可变解压数据，`processed/` 保存 YOLO 格式训练、验证和测试数据；这些生成目录不提交 Git。

RDD2022 source / 数据来源: <https://github.com/sekilab/RoadDamageDetector>

Never edit `raw/`. If a generated directory must be removed, inspect it first and use `/usr/bin/trash <absolute-path>`.

不要编辑 `raw/`。确需移除生成目录时，先检查内容，再使用 `/usr/bin/trash <absolute-path>`。
