-- Presence metrics do not assume repeated daily rows are ingestion duplicates.
CREATE OR REPLACE TEMP TABLE eligible AS
SELECT r.*,c.module_presentation_length
FROM studentRegistration r JOIN courses c USING(code_module,code_presentation)
WHERE r.date_registration<=0
  AND (r.date_unregistration IS NULL OR r.date_unregistration>=0)
  AND c.module_presentation_length>=28;

CREATE OR REPLACE TEMP TABLE day_activity AS
WITH per_site AS (
 SELECT e.code_module,e.code_presentation,e.id_student,e.date,e.id_site,
        sum(e.sum_click) clicks_raw,
        sum(DISTINCT e.sum_click) clicks_exact,
        max(e.sum_click) clicks_max,
        max(CASE WHEN v.activity_type IN ('oucontent','resource','subpage','page') THEN 1 ELSE 0 END) AS has_content
 FROM studentVle e JOIN eligible r USING(code_module,code_presentation,id_student)
 JOIN vle v USING(code_module,code_presentation,id_site)
 WHERE e.sum_click>0 AND e.date BETWEEN 0 AND 27
   AND (NOT $strict OR (e.date>=r.date_registration AND (r.date_unregistration IS NULL OR e.date<=r.date_unregistration)))
 GROUP BY e.code_module,e.code_presentation,e.id_student,e.date,e.id_site
)
SELECT code_module,code_presentation,id_student,date,
       sum(clicks_raw) clicks_raw,sum(clicks_exact) clicks_exact,sum(clicks_max) clicks_max,max(has_content) AS has_content
FROM per_site GROUP BY code_module,code_presentation,id_student,date;

CREATE OR REPLACE TABLE mart AS
WITH a AS (
 SELECT r.code_module,r.code_presentation,r.id_student,
 count(d.date) FILTER(WHERE d.date BETWEEN 0 AND 6)::INT w1_days,
 max(CASE WHEN d.date BETWEEN 7 AND 13 THEN 1 ELSE 0 END)::INT w2_active,
 max(CASE WHEN d.date BETWEEN 14 AND 27 THEN 1 ELSE 0 END)::INT later_active,
 min(d.date) FILTER(WHERE d.date BETWEEN 0 AND 6) first_day,
 r.date_unregistration
 FROM eligible r LEFT JOIN day_activity d USING(code_module,code_presentation,id_student)
 GROUP BY r.code_module,r.code_presentation,r.id_student,r.date_unregistration
)
SELECT a.*,coalesce(d.has_content,0)::INT first_content,
 coalesce(d.clicks_raw,0)::BIGINT first_clicks_raw,
 coalesce(d.clicks_exact,0)::BIGINT first_clicks_exact,
 coalesce(d.clicks_max,0)::BIGINT first_clicks_max
FROM a LEFT JOIN day_activity d ON a.code_module=d.code_module AND a.code_presentation=d.code_presentation
 AND a.id_student=d.id_student AND a.first_day=d.date;
