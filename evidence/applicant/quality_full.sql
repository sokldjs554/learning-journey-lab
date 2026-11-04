-- OULAD source-quality checks: all 20 rules in applicant-full-quality-spec.md.
-- Read-only SELECT; one issue per source row except *_repeat (excess copies).
-- Output: rule_id, severity, issue_count (exactly 20 rows).
-- GROUP BY treats NULL values in the same key position as one repeat group.

WITH exact_repeat_groups AS (
    SELECT COUNT(*) AS row_count
    FROM studentVle
    GROUP BY code_module, code_presentation, id_student, id_site, date, sum_click
    HAVING COUNT(*) > 1
),
daily_repeat_groups AS (
    SELECT COUNT(*) AS row_count
    FROM studentVle
    GROUP BY code_module, code_presentation, id_student, id_site, date
    HAVING COUNT(*) > 1
),
registration_repeat_groups AS (
    SELECT COUNT(*) AS row_count
    FROM studentRegistration
    GROUP BY code_module, code_presentation, id_student
    HAVING COUNT(*) > 1
),
site_repeat_groups AS (
    SELECT COUNT(*) AS row_count
    FROM vle
    GROUP BY code_module, code_presentation, id_site
    HAVING COUNT(*) > 1
),
course_repeat_groups AS (
    SELECT COUNT(*) AS row_count
    FROM courses
    GROUP BY code_module, code_presentation
    HAVING COUNT(*) > 1
),
checks AS (
    SELECT 1 AS ordinal, 'registration_missing_date' AS rule_id,
           'review' AS severity, COUNT(*) AS issue_count
    FROM studentRegistration
    WHERE date_registration IS NULL

    UNION ALL
    SELECT 2, 'event_exact_repeat', 'review', COALESCE(SUM(row_count - 1), 0)
    FROM exact_repeat_groups

    UNION ALL
    SELECT 3, 'event_unknown_student', 'block', COUNT(*)
    FROM studentVle AS e
    WHERE e.id_student IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM studentRegistration AS r
          WHERE r.code_module = e.code_module
            AND r.code_presentation = e.code_presentation
            AND r.id_student = e.id_student
      )

    UNION ALL
    SELECT 4, 'event_required_null', 'block', COUNT(*)
    FROM studentVle
    WHERE code_module IS NULL OR code_presentation IS NULL
       OR id_student IS NULL OR id_site IS NULL
       OR date IS NULL OR sum_click IS NULL

    UNION ALL
    SELECT 5, 'event_nonpositive_click', 'block', COUNT(*)
    FROM studentVle
    WHERE sum_click <= 0

    UNION ALL
    SELECT 6, 'event_daily_key_repeat', 'review', COALESCE(SUM(row_count - 1), 0)
    FROM daily_repeat_groups

    UNION ALL
    SELECT 7, 'event_unknown_site', 'block', COUNT(*)
    FROM studentVle AS e
    WHERE e.id_site IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM vle AS v
          WHERE v.code_module = e.code_module
            AND v.code_presentation = e.code_presentation
            AND v.id_site = e.id_site
      )

    UNION ALL
    SELECT 8, 'registration_inverted_dates', 'block', COUNT(*)
    FROM studentRegistration
    WHERE date_registration > date_unregistration

    UNION ALL
    SELECT 9, 'registration_key_repeat', 'block',
           COALESCE(SUM(row_count - 1), 0)
    FROM registration_repeat_groups

    UNION ALL
    SELECT 10, 'site_key_repeat', 'block', COALESCE(SUM(row_count - 1), 0)
    FROM site_repeat_groups

    UNION ALL
    SELECT 11, 'course_key_repeat', 'block', COALESCE(SUM(row_count - 1), 0)
    FROM course_repeat_groups

    UNION ALL
    SELECT 12, 'event_before_registration', 'review', COUNT(*)
    FROM studentVle AS e
    WHERE EXISTS (
        SELECT 1 FROM studentRegistration AS r
        WHERE r.code_module = e.code_module
          AND r.code_presentation = e.code_presentation
          AND r.id_student = e.id_student
          AND e.date < r.date_registration
    )

    UNION ALL
    SELECT 13, 'event_after_withdrawal', 'review', COUNT(*)
    FROM studentVle AS e
    WHERE EXISTS (
        SELECT 1 FROM studentRegistration AS r
        WHERE r.code_module = e.code_module
          AND r.code_presentation = e.code_presentation
          AND r.id_student = e.id_student
          AND e.date > r.date_unregistration
    )

    UNION ALL
    SELECT 14, 'event_after_course', 'review', COUNT(*)
    FROM studentVle AS e
    WHERE EXISTS (
        SELECT 1 FROM courses AS c
        WHERE c.code_module = e.code_module
          AND c.code_presentation = e.code_presentation
          AND e.date >= c.module_presentation_length
    )

    UNION ALL
    SELECT 15, 'registration_required_null', 'block', COUNT(*)
    FROM studentRegistration
    WHERE code_module IS NULL OR code_presentation IS NULL
       OR id_student IS NULL

    UNION ALL
    SELECT 16, 'site_required_null', 'block', COUNT(*)
    FROM vle
    WHERE code_module IS NULL OR code_presentation IS NULL
       OR id_site IS NULL OR activity_type IS NULL

    UNION ALL
    SELECT 17, 'course_required_null', 'block', COUNT(*)
    FROM courses
    WHERE code_module IS NULL OR code_presentation IS NULL

    UNION ALL
    SELECT 18, 'course_invalid_length', 'block', COUNT(*)
    FROM courses
    WHERE module_presentation_length IS NULL OR module_presentation_length <= 0

    UNION ALL
    SELECT 19, 'registration_unknown_course', 'block', COUNT(*)
    FROM studentRegistration AS r
    WHERE r.code_module IS NOT NULL
      AND r.code_presentation IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM courses AS c
          WHERE c.code_module = r.code_module
            AND c.code_presentation = r.code_presentation
      )

    UNION ALL
    SELECT 20, 'site_unknown_course', 'block', COUNT(*)
    FROM vle AS v
    WHERE v.code_module IS NOT NULL
      AND v.code_presentation IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM courses AS c
          WHERE c.code_module = v.code_module
            AND c.code_presentation = v.code_presentation
      )
)
SELECT rule_id, severity, issue_count
FROM checks
ORDER BY ordinal;
