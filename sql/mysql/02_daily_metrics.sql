WITH behavior_counts AS (
    SELECT
        event_day,
        behavior_type,
        COUNT(*) AS cnt
    FROM behavior_clean
    GROUP BY event_day, behavior_type
),
daily_users AS (
    SELECT
        event_day,
        COUNT(DISTINCT user_id) AS dau
    FROM behavior_clean
    GROUP BY event_day
)
SELECT
    d.event_day AS day,
    d.dau,
    COALESCE(SUM(CASE WHEN b.behavior_type = 'pv' THEN b.cnt ELSE 0 END), 0) AS pv,
    COALESCE(SUM(CASE WHEN b.behavior_type = 'fav' THEN b.cnt ELSE 0 END), 0) AS fav,
    COALESCE(SUM(CASE WHEN b.behavior_type = 'cart' THEN b.cnt ELSE 0 END), 0) AS cart,
    COALESCE(SUM(CASE WHEN b.behavior_type = 'buy' THEN b.cnt ELSE 0 END), 0) AS buy,
    ROUND(
        CAST(
            COALESCE(SUM(CASE WHEN b.behavior_type = 'buy' THEN b.cnt ELSE 0 END), 0)
            AS DECIMAL(20, 10)
        )
        / NULLIF(SUM(CASE WHEN b.behavior_type = 'pv' THEN b.cnt ELSE 0 END), 0),
        6
    ) AS buy_to_pv,
    ROUND(
        CAST(
            COALESCE(SUM(CASE WHEN b.behavior_type = 'buy' THEN b.cnt ELSE 0 END), 0)
            AS DECIMAL(20, 10)
        )
        / NULLIF(d.dau, 0),
        6
    ) AS buy_per_dau
FROM daily_users d
LEFT JOIN behavior_counts b ON d.event_day = b.event_day
GROUP BY d.event_day, d.dau
ORDER BY d.event_day;
