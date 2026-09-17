SELECT
    behavior_type,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_id) AS user_count
FROM behavior_clean
GROUP BY behavior_type
ORDER BY event_count DESC;
