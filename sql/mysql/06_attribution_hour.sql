WITH hour_daily AS (
    SELECT
        event_hour AS hour,
        SUM(CASE WHEN event_day = '2017-12-01' THEN 1 ELSE 0 END) AS buy_1201,
        SUM(CASE WHEN event_day = '2017-12-02' THEN 1 ELSE 0 END) AS buy_1202
    FROM behavior_clean
    WHERE behavior_type = 'buy'
      AND event_day IN ('2017-12-01', '2017-12-02')
    GROUP BY event_hour
),
hour_delta AS (
    SELECT
        hour,
        buy_1201,
        buy_1202,
        buy_1202 - buy_1201 AS buy_delta
    FROM hour_daily
),
totals AS (
    SELECT SUM(buy_delta) AS total_delta
    FROM hour_delta
)
SELECT
    d.hour,
    d.buy_1201,
    d.buy_1202,
    d.buy_delta,
    ROUND(
        CAST(d.buy_delta AS DECIMAL(20, 10)) / NULLIF(t.total_delta, 0),
        6
    ) AS contribution
FROM hour_delta d
CROSS JOIN totals t
ORDER BY contribution DESC, hour;
