-- Small dimension contract: must run before any INNER JOIN can hide missing keys.
SELECT 'registration_required_null' rule_id,'block' severity,count(*) count FROM studentRegistration
WHERE code_module IS NULL OR code_presentation IS NULL OR id_student IS NULL
UNION ALL SELECT 'site_required_null','block',count(*) FROM vle
WHERE code_module IS NULL OR code_presentation IS NULL OR id_site IS NULL OR activity_type IS NULL
UNION ALL SELECT 'course_required_null','block',count(*) FROM courses
WHERE code_module IS NULL OR code_presentation IS NULL
UNION ALL SELECT 'course_invalid_length','block',count(*) FROM courses
WHERE module_presentation_length IS NULL OR module_presentation_length<=0
UNION ALL SELECT 'registration_unknown_course','block',count(*) FROM studentRegistration r
WHERE r.code_module IS NOT NULL AND r.code_presentation IS NOT NULL
AND NOT EXISTS(SELECT 1 FROM courses c WHERE r.code_module=c.code_module AND r.code_presentation=c.code_presentation)
UNION ALL SELECT 'site_unknown_course','block',count(*) FROM vle v
WHERE v.code_module IS NOT NULL AND v.code_presentation IS NOT NULL
AND NOT EXISTS(SELECT 1 FROM courses c WHERE v.code_module=c.code_module AND v.code_presentation=c.code_presentation);
