WITH grouped AS (
    SELECT
        CASE
            WHEN w1_days = 1 THEN '1일'
            WHEN w1_days = 2 THEN '2일'
            ELSE '3일 이상'
        END AS activity_group,
        CASE
            WHEN w1_days = 1 THEN 1
            WHEN w1_days = 2 THEN 2
            ELSE 3
        END AS sort_order,
        w2_active
    FROM mart
    WHERE w1_days >= 1
)
SELECT
    activity_group,
    COUNT(*) AS enrollment_count,
    SUM(CASE WHEN w2_active = 1 THEN 1 ELSE 0 END)
        AS next_week_active_count,
    ROUND(
        100.0 * SUM(CASE WHEN w2_active = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    ) AS revisit_rate_pct
FROM grouped
GROUP BY activity_group, sort_order
ORDER BY sort_order;
