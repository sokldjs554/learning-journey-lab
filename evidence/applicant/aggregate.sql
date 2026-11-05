-- Descriptive activity groups for the validated 12-column enrollment mart.
-- 0-day enrollments contribute to neither an activity-group denominator nor numerator.
-- Keep the overall and per-(module,presentation) scopes separate: summing both
-- scopes together would count every active enrollment twice.
WITH
activity_groups(sort_order, activity_group) AS (
    VALUES (1, '1일'), (2, '2일'), (3, '3일 이상')
),
cohorts AS (
    SELECT DISTINCT code_module, code_presentation
    FROM mart
),
scopes AS (
    SELECT 'overall' AS scope,
           CAST(NULL AS VARCHAR) AS code_module,
           CAST(NULL AS VARCHAR) AS code_presentation
    UNION ALL
    SELECT 'cohort', code_module, code_presentation
    FROM cohorts
),
classified AS (
    SELECT code_module, code_presentation, w2_active,
           CASE WHEN w1_days = 1 THEN 1
                WHEN w1_days = 2 THEN 2
                ELSE 3 END AS sort_order
    FROM mart
    WHERE w1_days >= 1
),
scoped_activity AS (
    SELECT 'overall' AS scope,
           CAST(NULL AS VARCHAR) AS code_module,
           CAST(NULL AS VARCHAR) AS code_presentation,
           sort_order, w2_active
    FROM classified
    UNION ALL
    SELECT 'cohort', code_module, code_presentation, sort_order, w2_active
    FROM classified
),
counts AS (
    SELECT scope, code_module, code_presentation, sort_order,
           COUNT(*) AS denominator,
           SUM(CASE WHEN w2_active = 1 THEN 1 ELSE 0 END) AS numerator
    FROM scoped_activity
    GROUP BY scope, code_module, code_presentation, sort_order
)
SELECT s.scope,
       s.code_module,
       s.code_presentation,
       g.activity_group,
       COALESCE(c.denominator, 0) AS denominator,
       COALESCE(c.numerator, 0) AS numerator,
       CASE WHEN COALESCE(c.denominator, 0) = 0 THEN NULL
            ELSE ROUND(100.0 * c.numerator / c.denominator, 1)
       END AS return_rate_pct
FROM scopes AS s
CROSS JOIN activity_groups AS g
LEFT JOIN counts AS c
    ON c.scope = s.scope
   AND c.sort_order = g.sort_order
   AND (
       s.scope = 'overall'
       OR (
           s.code_module = c.code_module
           AND s.code_presentation = c.code_presentation
       )
   )
ORDER BY CASE WHEN s.scope = 'overall' THEN 0 ELSE 1 END,
         s.code_module, s.code_presentation, g.sort_order;
