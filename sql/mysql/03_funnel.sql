WITH user_behavior AS (
    SELECT
        behavior_type,
        user_id,
        COUNT(*) AS event_count
    FROM behavior_clean
    GROUP BY behavior_type, user_id
),
behavior_counts AS (
    SELECT
        behavior_type,
        SUM(event_count) AS event_count,
        COUNT(*) AS user_count
    FROM user_behavior
    GROUP BY behavior_type
),
pv_users AS (
    SELECT user_count
    FROM behavior_counts
    WHERE behavior_type = 'pv'
)
SELECT
    behavior_counts.behavior_type,
    behavior_counts.event_count,
    behavior_counts.user_count,
    ROUND(
        CAST(behavior_counts.user_count AS DECIMAL(20, 10))
        / NULLIF(pv_users.user_count, 0),
        6
    ) AS user_to_pv
FROM behavior_counts
CROSS JOIN pv_users
ORDER BY FIELD(behavior_counts.behavior_type, 'pv', 'cart', 'fav', 'buy');
