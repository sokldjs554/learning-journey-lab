CREATE OR REPLACE TEMP VIEW received AS SELECT * FROM delivery WHERE ingested_at<14*86400;
CREATE OR REPLACE TEMP VIEW unique_received AS
SELECT * FROM received QUALIFY row_number() OVER(PARTITION BY event_id ORDER BY ingested_at)=1;
CREATE OR REPLACE TEMP VIEW bad_sessions AS
SELECT f.session_id FROM unique_received f LEFT JOIN unique_received s ON f.session_id=s.session_id AND s.event_type='start'
WHERE f.event_type='complete' AND (s.event_id IS NULL OR f.occurred_at<s.occurred_at);
CREATE OR REPLACE TEMP VIEW cleaned AS
SELECT * FROM unique_received e WHERE user_id IN (SELECT user_id FROM learners)
AND session_id NOT IN(SELECT session_id FROM bad_sessions);
