-- One row per sampled user. Anchor is the first RECORDED event, not signup.
-- Integer elapsed 24-hour bins are invariant to an additive timestamp shift.
-- No eligibility condition based on a future event or maximum activity date.
WITH anchored AS (
  SELECT *, min(timestamp) OVER (PARTITION BY user_id) AS anchor
  FROM events
), timed AS (
  SELECT *, CAST(floor((timestamp - anchor) / 86400000.0) AS BIGINT) AS elapsed_day,
    action_type = 'submit' AND regexp_full_match(item_id, 'b[0-9]+') AS is_submit,
    action_type = 'enter' AND regexp_full_match(item_id, '[bel][0-9]+') AS is_entry
  FROM anchored
)
SELECT user_id,
  count(DISTINCT elapsed_day) FILTER (WHERE elapsed_day >= 0 AND elapsed_day < 7 AND is_submit) AS w1_submit_days,
  CAST(count(*) FILTER (WHERE elapsed_day >= 7 AND elapsed_day < 14 AND is_submit) > 0 AS INTEGER) AS w2_submit,
  count(DISTINCT elapsed_day) FILTER (WHERE elapsed_day >= 0 AND elapsed_day < 7 AND is_entry) AS w1_entry_days,
  CAST(count(*) FILTER (WHERE elapsed_day >= 7 AND elapsed_day < 14 AND is_entry) > 0 AS INTEGER) AS w2_entry,
  count(DISTINCT elapsed_day) FILTER (WHERE elapsed_day >= 0 AND elapsed_day < 7) AS w1_ui_days,
  CAST(count(*) FILTER (WHERE elapsed_day >= 7 AND elapsed_day < 14) > 0 AS INTEGER) AS w2_ui,
  max(elapsed_day) AS last_event_elapsed_day,
  count(*) AS rows
FROM timed GROUP BY user_id ORDER BY user_id;
