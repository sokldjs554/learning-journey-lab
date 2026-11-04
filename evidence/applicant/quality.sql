-- OULAD: first three source-quality checks.
-- Read-only; run after load_sources.py has populated the DuckDB tables.
-- Output: rule_id, issue_count (exactly three rows).

WITH exact_repeat_groups AS (
    SELECT COUNT(*) AS row_count
    FROM studentVle
    GROUP BY
        code_module,
        code_presentation,
        id_student,
        id_site,
        date,
        sum_click
    HAVING COUNT(*) > 1
),
quality_counts AS (
    -- One issue per registration row whose registration date is NULL.
    SELECT
        'registration_missing_date' AS rule_id,
        COUNT(*) AS issue_count
    FROM studentRegistration
    WHERE date_registration IS NULL

    UNION ALL

    -- Count only extra copies: three identical rows contribute two issues.
    SELECT
        'event_exact_repeat' AS rule_id,
        COALESCE(SUM(row_count - 1), 0) AS issue_count
    FROM exact_repeat_groups

    UNION ALL

    -- Count event rows, not joined registration rows; ignore NULL student IDs.
    SELECT
        'event_unknown_student' AS rule_id,
        COUNT(*) AS issue_count
    FROM studentVle AS e
    WHERE e.id_student IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM studentRegistration AS r
          WHERE r.code_module = e.code_module
            AND r.code_presentation = e.code_presentation
            AND r.id_student = e.id_student
      )
)
SELECT rule_id, issue_count
FROM quality_counts
ORDER BY CASE rule_id
    WHEN 'registration_missing_date' THEN 1
    WHEN 'event_exact_repeat' THEN 2
    WHEN 'event_unknown_student' THEN 3
END;
