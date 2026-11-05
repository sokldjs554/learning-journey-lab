-- OULAD enrollment mart (read-only). Bind DuckDB named parameter $strict (boolean).
-- One output row per (code_module, code_presentation, id_student).
-- W1=D0..D6, W2=D7..D13, later=D14..D27; D0 is the presentation start.

WITH eligible AS (
    SELECT
        r.code_module,
        r.code_presentation,
        r.id_student,
        r.date_registration,
        r.date_unregistration
    FROM studentRegistration AS r
    JOIN courses AS c
      ON c.code_module = r.code_module
     AND c.code_presentation = r.code_presentation
    WHERE r.date_registration <= 0
      AND (r.date_unregistration IS NULL OR r.date_unregistration >= 0)
      AND c.module_presentation_length >= 28
),
per_site AS (
    SELECT
        e.code_module,
        e.code_presentation,
        e.id_student,
        e.date,
        e.id_site,
        SUM(e.sum_click) AS clicks_raw,
        SUM(DISTINCT e.sum_click) AS clicks_exact,
        MAX(e.sum_click) AS clicks_max,
        MAX(CASE WHEN v.activity_type IN (
            'oucontent', 'resource', 'subpage', 'page'
        ) THEN 1 ELSE 0 END) AS has_content
    FROM studentVle AS e
    JOIN eligible AS r
      ON r.code_module = e.code_module
     AND r.code_presentation = e.code_presentation
     AND r.id_student = e.id_student
    JOIN vle AS v
      ON v.code_module = e.code_module
     AND v.code_presentation = e.code_presentation
     AND v.id_site = e.id_site
    WHERE e.sum_click > 0
      AND e.date BETWEEN 0 AND 27
      AND (
          NOT $strict
          OR (
              e.date >= r.date_registration
              AND (
                  r.date_unregistration IS NULL
                  OR e.date <= r.date_unregistration
              )
          )
      )
    GROUP BY
        e.code_module, e.code_presentation, e.id_student, e.date, e.id_site
),
per_day AS (
    SELECT
        code_module,
        code_presentation,
        id_student,
        date,
        SUM(clicks_raw) AS clicks_raw,
        SUM(clicks_exact) AS clicks_exact,
        SUM(clicks_max) AS clicks_max,
        MAX(has_content) AS has_content
    FROM per_site
    GROUP BY code_module, code_presentation, id_student, date
),
activity_by_enrollment AS (
    SELECT
        r.code_module,
        r.code_presentation,
        r.id_student,
        CAST(COUNT(CASE WHEN d.date BETWEEN 0 AND 6 THEN 1 END) AS INTEGER)
            AS w1_days,
        CAST(MAX(CASE WHEN d.date BETWEEN 7 AND 13 THEN 1 ELSE 0 END) AS INTEGER)
            AS w2_active,
        CAST(MAX(CASE WHEN d.date BETWEEN 14 AND 27 THEN 1 ELSE 0 END) AS INTEGER)
            AS later_active,
        MIN(CASE WHEN d.date BETWEEN 0 AND 6 THEN d.date END) AS first_day,
        r.date_unregistration
    FROM eligible AS r
    LEFT JOIN per_day AS d
      ON d.code_module = r.code_module
     AND d.code_presentation = r.code_presentation
     AND d.id_student = r.id_student
    GROUP BY r.code_module, r.code_presentation, r.id_student,
             r.date_unregistration
)
SELECT
    a.code_module,
    a.code_presentation,
    a.id_student,
    a.w1_days,
    a.w2_active,
    a.later_active,
    a.first_day,
    a.date_unregistration,
    CAST(COALESCE(d.has_content, 0) AS INTEGER) AS first_content,
    CAST(COALESCE(d.clicks_raw, 0) AS BIGINT) AS first_clicks_raw,
    CAST(COALESCE(d.clicks_exact, 0) AS BIGINT) AS first_clicks_exact,
    CAST(COALESCE(d.clicks_max, 0) AS BIGINT) AS first_clicks_max
FROM activity_by_enrollment AS a
LEFT JOIN per_day AS d
  ON d.code_module = a.code_module
 AND d.code_presentation = a.code_presentation
 AND d.id_student = a.id_student
 AND d.date = a.first_day
ORDER BY a.code_module, a.code_presentation, a.id_student;
