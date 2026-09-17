# 本地数据目录

以下文件由本地流程生成，已被 `.gitignore` 排除，不进入 Git：

- `UserBehavior_raw.csv`：从天池下载的原始数据。
- `UserBehavior_sample.csv`：按 `user_id` 稳定哈希生成的约 2% 用户级抽样。
- `ecommerce.db`：SQLite 数仓。

原始数据下载地址和数据版本见项目根目录 `README.md` 与 `docs/01_数据说明.md`。
