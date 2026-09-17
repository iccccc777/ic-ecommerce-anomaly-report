WITH daily_users AS (
    SELECT DISTINCT
        user_id,
        date(timestamps, 'unixepoch', '+8 hours') AS day
    FROM behavior_clean
    WHERE date(timestamps, 'unixepoch', '+8 hours') IN ('2017-12-01', '2017-12-02')
),
dau_1201 AS (
    SELECT user_id FROM daily_users WHERE day = '2017-12-01'
),
dau_1202 AS (
    SELECT user_id FROM daily_users WHERE day = '2017-12-02'
),
both AS (
    SELECT user_id FROM dau_1201
    INTERSECT
    SELECT user_id FROM dau_1202
)
SELECT 'both_days' AS segment, COUNT(*) AS users FROM both
UNION ALL
SELECT 'gained_1202_only' AS segment, COUNT(*) AS users
FROM dau_1202
WHERE user_id NOT IN (SELECT user_id FROM both)
UNION ALL
SELECT 'lost_1201_only' AS segment, COUNT(*) AS users
FROM dau_1201
WHERE user_id NOT IN (SELECT user_id FROM both);
