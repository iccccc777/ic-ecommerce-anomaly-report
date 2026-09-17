WITH behavior_counts AS (
    SELECT
        date(timestamps, 'unixepoch', '+8 hours') AS day,
        behavior_type,
        COUNT(*) AS cnt
    FROM behavior_clean
    GROUP BY day, behavior_type
),
daily_users AS (
    SELECT
        date(timestamps, 'unixepoch', '+8 hours') AS day,
        COUNT(DISTINCT user_id) AS dau
    FROM behavior_clean
    GROUP BY day
)
SELECT
    d.day,
    d.dau,
    COALESCE(SUM(CASE WHEN b.behavior_type = 'pv' THEN b.cnt ELSE 0 END), 0) AS pv,
    COALESCE(SUM(CASE WHEN b.behavior_type = 'fav' THEN b.cnt ELSE 0 END), 0) AS fav,
    COALESCE(SUM(CASE WHEN b.behavior_type = 'cart' THEN b.cnt ELSE 0 END), 0) AS cart,
    COALESCE(SUM(CASE WHEN b.behavior_type = 'buy' THEN b.cnt ELSE 0 END), 0) AS buy,
    ROUND(
        COALESCE(SUM(CASE WHEN b.behavior_type = 'buy' THEN b.cnt ELSE 0 END), 0) * 1.0
        / NULLIF(SUM(CASE WHEN b.behavior_type = 'pv' THEN b.cnt ELSE 0 END), 0),
        6
    ) AS buy_to_pv,
    ROUND(
        COALESCE(SUM(CASE WHEN b.behavior_type = 'buy' THEN b.cnt ELSE 0 END), 0) * 1.0
        / NULLIF(d.dau, 0),
        6
    ) AS buy_per_dau
FROM daily_users d
LEFT JOIN behavior_counts b ON d.day = b.day
GROUP BY d.day, d.dau
ORDER BY d.day;
