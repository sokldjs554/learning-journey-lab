-- 100% SYNTHETIC. One row per renewal cycle; join aggregated learning/billing.
-- Scenario window: [due, due + 7 days). This is NOT CLASS101's billing policy.
WITH member_counts AS (
 SELECT cycle_id, count(DISTINCT learner_id) learner_count FROM members GROUP BY cycle_id
), first_week AS (
 SELECT c.cycle_id, count(DISTINCT CAST(e.occurred_at AS DATE))::INT learning_days
 FROM cycles c LEFT JOIN learning e ON e.cycle_id=c.cycle_id
 AND e.occurred_at>=c.started_at AND e.occurred_at<c.started_at+INTERVAL 7 DAY
 AND e.ingested_at<=$as_of
 GROUP BY c.cycle_id
), settlements AS (
 SELECT DISTINCT b.cycle_id,b.transaction_id
 FROM billing b JOIN cycles c USING(cycle_id)
 WHERE b.kind='settled' AND b.occurred_at>=c.renewal_due_at
 AND b.occurred_at<c.renewal_due_at+INTERVAL 7 DAY AND b.ingested_at<=$as_of
), remaining AS (
 SELECT s.cycle_id,count(*)::INT retained_transactions FROM settlements s
 WHERE NOT EXISTS (SELECT 1 FROM billing r WHERE r.transaction_id=s.transaction_id
 AND r.kind='refunded' AND r.occurred_at<=$as_of AND r.ingested_at<=$as_of)
 GROUP BY s.cycle_id
), paid AS (
 SELECT cycle_id,count(*)::INT paid_transactions FROM settlements GROUP BY cycle_id
), failed AS (
 SELECT DISTINCT b.cycle_id FROM billing b JOIN cycles c USING(cycle_id)
 WHERE b.kind='failed' AND b.occurred_at>=c.renewal_due_at
 AND b.occurred_at<c.renewal_due_at+INTERVAL 7 DAY AND b.ingested_at<=$as_of
), evaluated AS (
 SELECT c.cycle_id,c.subscription_id,c.payer_id,c.plan_type,
 coalesce(m.learner_count,0)::INT learner_count,
 CASE WHEN least($as_of,$watermark)>=c.started_at+INTERVAL 7 DAY THEN f.learning_days END learning_days,
 c.cancel_requested_at IS NOT NULL AND c.cancel_requested_at<=$as_of cancel_requested,
 CASE WHEN least($as_of,$watermark)<c.renewal_due_at+INTERVAL 7 DAY THEN 'pending'
 WHEN coalesce(r.retained_transactions,0)>0 THEN 'renewed'
 WHEN coalesce(p.paid_transactions,0)>0 THEN 'fully_refunded'
 WHEN x.cycle_id IS NOT NULL THEN 'payment_failed'
 ELSE 'no_settlement_in_window' END outcome
 FROM cycles c LEFT JOIN member_counts m USING(cycle_id)
 LEFT JOIN first_week f USING(cycle_id) LEFT JOIN remaining r USING(cycle_id)
 LEFT JOIN paid p USING(cycle_id) LEFT JOIN failed x USING(cycle_id)
)
SELECT *, CASE WHEN outcome='pending' THEN NULL ELSE (outcome='renewed')::INT END renewed
FROM evaluated ORDER BY cycle_id;
