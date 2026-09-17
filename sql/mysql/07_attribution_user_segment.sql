WITH daily_users AS (
    SELECT DISTINCT
        user_id,
        event_day AS day
    FROM behavior_clean
    WHERE event_day IN ('2017-12-01', '2017-12-02')
),
user_presence AS (
    SELECT
        user_id,
        MAX(CASE WHEN day = '2017-12-01' THEN 1 ELSE 0 END) AS active_1201,
        MAX(CASE WHEN day = '2017-12-02' THEN 1 ELSE 0 END) AS active_1202
    FROM daily_users
    GROUP BY user_id
),
segment_counts AS (
    SELECT
        SUM(active_1201 = 1 AND active_1202 = 1) AS both_users,
        SUM(active_1201 = 1 AND active_1202 = 0) AS lost_users,
        SUM(active_1201 = 0 AND active_1202 = 1) AS gained_users
    FROM user_presence
)
SELECT segment, users_1201, users_1202, delta_contribution, share_1202
FROM (
    SELECT
        1 AS sort_order,
        'both_days' AS segment,
        segment_counts.both_users AS users_1201,
        segment_counts.both_users AS users_1202,
        0 AS delta_contribution,
        ROUND(
            CAST(segment_counts.both_users AS DECIMAL(20, 10))
            / NULLIF(segment_counts.both_users + segment_counts.gained_users, 0),
            6
        ) AS share_1202
    FROM segment_counts
    UNION ALL
    SELECT
        2 AS sort_order,
        'gained_1202_only' AS segment,
        0 AS users_1201,
        segment_counts.gained_users AS users_1202,
        segment_counts.gained_users AS delta_contribution,
        ROUND(
            CAST(segment_counts.gained_users AS DECIMAL(20, 10))
            / NULLIF(segment_counts.both_users + segment_counts.gained_users, 0),
            6
        ) AS share_1202
    FROM segment_counts
    UNION ALL
    SELECT
        3 AS sort_order,
        'lost_1201_only' AS segment,
        segment_counts.lost_users AS users_1201,
        0 AS users_1202,
        -segment_counts.lost_users AS delta_contribution,
        0 AS share_1202
    FROM segment_counts
) AS segments
ORDER BY sort_order;
