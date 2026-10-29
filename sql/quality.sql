-- Counts are affected rows, except *_repeat / *_key_repeat: excess rows beyond first.
SELECT 'event_required_null' rule_id, 'block' severity, count(*) count FROM studentVle
WHERE code_module IS NULL OR code_presentation IS NULL OR id_student IS NULL OR id_site IS NULL OR date IS NULL OR sum_click IS NULL
UNION ALL SELECT 'event_nonpositive_click','block',count(*) FROM studentVle WHERE sum_click<=0
UNION ALL SELECT 'event_exact_repeat','review',count(*)-count(DISTINCT (code_module,code_presentation,id_student,id_site,date,sum_click)) FROM studentVle
UNION ALL SELECT 'event_daily_key_repeat','review',count(*)-count(DISTINCT (code_module,code_presentation,id_student,id_site,date)) FROM studentVle
UNION ALL SELECT 'event_unknown_student','block',count(*) FROM studentVle e
WHERE e.id_student IS NOT NULL AND NOT EXISTS(SELECT 1 FROM studentRegistration r WHERE (e.code_module,e.code_presentation,e.id_student)=(r.code_module,r.code_presentation,r.id_student))
UNION ALL SELECT 'event_unknown_site','block',count(*) FROM studentVle e
WHERE e.id_site IS NOT NULL AND NOT EXISTS(SELECT 1 FROM vle v WHERE (e.code_module,e.code_presentation,e.id_site)=(v.code_module,v.code_presentation,v.id_site))
UNION ALL SELECT 'registration_missing_date','review',count(*) FROM studentRegistration WHERE date_registration IS NULL
UNION ALL SELECT 'registration_inverted_dates','block',count(*) FROM studentRegistration WHERE date_registration>date_unregistration
UNION ALL SELECT 'registration_key_repeat','block',count(*)-count(DISTINCT(code_module,code_presentation,id_student)) FROM studentRegistration
UNION ALL SELECT 'site_key_repeat','block',count(*)-count(DISTINCT(code_module,code_presentation,id_site)) FROM vle
UNION ALL SELECT 'course_key_repeat','block',count(*)-count(DISTINCT(code_module,code_presentation)) FROM courses
UNION ALL SELECT 'event_before_registration','review',count(*) FROM studentVle e JOIN studentRegistration r USING(code_module,code_presentation,id_student) WHERE e.date<r.date_registration
UNION ALL SELECT 'event_after_withdrawal','review',count(*) FROM studentVle e JOIN studentRegistration r USING(code_module,code_presentation,id_student) WHERE e.date>r.date_unregistration
UNION ALL SELECT 'event_after_course','review',count(*) FROM studentVle e JOIN courses c USING(code_module,code_presentation) WHERE e.date>=c.module_presentation_length
ORDER BY rule_id;
