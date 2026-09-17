# Python 脚本

按顺序运行：

1. `01_quick_inspect.py`：检查原始文件前几行和字段分布。
2. `02_build_sqlite.py`：用户级抽样并重建 SQLite 数仓。
3. `03_daily_metrics.py`：生成日指标。
4. `04_funnel_retention.py`：生成窗口期用户重叠率和留存。
5. `05_anomaly_detection.py`：前 3 日移动平均、同星期基线和留一法 Z-Score。
6. `06_attribution.py`：类目、时段和 DAU 增量归因。
7. `07_ai_daily_report.py`：调用 DeepSeek/通义千问或生成本地模板日报。
8. `08_streamlit_dashboard.py`：启动 Streamlit 看板。
9. `09_migrate_to_mysql.py`：将 SQLite 行为抽样迁移到 MySQL 8 并生成方言结果。
10. `10_validate_mysql_migration.py`：比较 MySQL 迁移结果与 SQLite 基线。
11. `anomaly_utils.py`：SQLite 与 MySQL 共用的异常检测和 trailing baseline 逻辑。
