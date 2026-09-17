WITH category_daily AS (
    SELECT
        category_id,
        SUM(CASE WHEN event_day = '2017-12-01' THEN 1 ELSE 0 END) AS buy_1201,
        SUM(CASE WHEN event_day = '2017-12-02' THEN 1 ELSE 0 END) AS buy_1202
    FROM behavior_clean
    WHERE behavior_type = 'buy'
      AND event_day IN ('2017-12-01', '2017-12-02')
    GROUP BY category_id
),
category_delta AS (
    SELECT
        category_id,
        buy_1201,
        buy_1202,
        buy_1202 - buy_1201 AS buy_delta
    FROM category_daily
),
totals AS (
    SELECT SUM(buy_delta) AS total_delta
    FROM category_delta
)
SELECT
    d.category_id,
    d.buy_1201,
    d.buy_1202,
    d.buy_delta,
    ROUND(
        d.buy_delta::NUMERIC / NULLIF(t.total_delta, 0),
        6
    ) AS contribution
FROM category_delta d
CROSS JOIN totals t
ORDER BY contribution DESC, category_id;
