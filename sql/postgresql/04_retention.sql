WITH first_active AS (
    SELECT
        user_id,
        MIN(event_day) AS first_day
    FROM behavior_clean
    GROUP BY user_id
),
daily_active AS (
    SELECT DISTINCT
        user_id,
        event_day AS day
    FROM behavior_clean
),
cohort_size AS (
    SELECT
        first_day,
        COUNT(*) AS users
    FROM first_active
    GROUP BY first_day
),
retained AS (
    SELECT
        f.first_day,
        a.day,
        a.day::DATE - f.first_day::DATE AS day_diff,
        COUNT(DISTINCT f.user_id) AS retained_users
    FROM first_active f
    JOIN daily_active a USING (user_id)
    WHERE a.day >= f.first_day
    GROUP BY f.first_day, a.day
)
SELECT
    c.first_day,
    d.day_diff,
    c.users AS cohort_size,
    d.retained_users,
    ROUND(d.retained_users::NUMERIC / NULLIF(c.users, 0), 4) AS retention_rate
FROM cohort_size c
JOIN retained d USING (first_day)
ORDER BY c.first_day, d.day_diff;
