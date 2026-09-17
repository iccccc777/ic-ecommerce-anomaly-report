SELECT
    strftime('%H', timestamps, 'unixepoch', '+8 hours') AS hour,
    date(timestamps, 'unixepoch', '+8 hours') AS day,
    COUNT(*) AS buy_events,
    COUNT(DISTINCT user_id) AS users
FROM behavior_clean
WHERE behavior_type = 'buy'
  AND date(timestamps, 'unixepoch', '+8 hours') IN ('2017-12-01', '2017-12-02')
GROUP BY hour, day;
