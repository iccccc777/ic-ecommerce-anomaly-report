# SQL 文件

- `01_schema.sql`：行为事实表、清洗视图和维度表结构。
- `02_daily_metrics.sql`：DAU、PV、收藏、加购、购买和购买/浏览比。
- `03_funnel.sql`：窗口期行为用户重叠率。
- `04_retention.sql`：按窗口内首次活跃日计算留存。
- `05_attribution_category.sql`：类目购买增量明细。
- `06_attribution_hour.sql`：小时购买增量明细。
- `07_attribution_user_segment.sql`：DAU 净增量拆解。

方言迁移版本：

- `mysql/`：MySQL 8.0 建表、复合索引和分析查询。
- `postgresql/`：PostgreSQL 建表和等价查询。
