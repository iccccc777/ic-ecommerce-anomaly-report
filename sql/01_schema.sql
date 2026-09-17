-- 说明：本文件描述 SQLite 数仓表结构；实际建库由 python/02_build_sqlite.py 完成。

DROP VIEW IF EXISTS behavior_clean;
DROP TABLE IF EXISTS dim_user;
DROP TABLE IF EXISTS dim_item;
DROP TABLE IF EXISTS dim_category;
DROP TABLE IF EXISTS behavior;

CREATE TABLE behavior (
    user_id INTEGER,
    item_id INTEGER,
    category_id INTEGER,
    behavior_type TEXT,
    timestamps INTEGER
);

CREATE INDEX idx_behavior_user ON behavior(user_id, timestamps);
CREATE INDEX idx_behavior_cat ON behavior(category_id, timestamps);
CREATE INDEX idx_behavior_time ON behavior(timestamps);

-- 只保留原始数据声明的业务时间窗口，并统一按北京时间计算日期。
CREATE VIEW behavior_clean AS
SELECT *
FROM behavior
WHERE date(timestamps, 'unixepoch', '+8 hours')
      BETWEEN '2017-11-25' AND '2017-12-03';

CREATE TABLE dim_user AS
SELECT
    user_id,
    COUNT(*) AS behavior_count,
    COUNT(DISTINCT date(timestamps, 'unixepoch', '+8 hours')) AS active_days,
    MIN(timestamps) AS first_ts,
    MAX(timestamps) AS last_ts
FROM behavior_clean
GROUP BY user_id;

CREATE TABLE dim_item AS
SELECT
    item_id,
    COUNT(*) AS behavior_count,
    COUNT(DISTINCT user_id) AS user_count
FROM behavior_clean
GROUP BY item_id;

CREATE TABLE dim_category AS
SELECT
    category_id,
    COUNT(*) AS behavior_count,
    COUNT(DISTINCT user_id) AS user_count
FROM behavior_clean
GROUP BY category_id;
