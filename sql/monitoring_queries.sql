-- ============================================================
-- Merchant-Level Risk Metrics
-- ============================================================

-- 1. Chargeback ratio, refund rate, decline rate, and average ticket per merchant
SELECT
    m.merchant_id,
    m.merchant_name,
    m.category,
    m.is_high_risk,
    COUNT(t.transaction_id)                                              AS total_transactions,
    SUM(CASE WHEN t.status = 'approved' THEN 1 ELSE 0 END)             AS approved_count,
    SUM(CASE WHEN t.status = 'declined' THEN 1 ELSE 0 END)             AS declined_count,
    SUM(CASE WHEN t.status = 'refunded' THEN 1 ELSE 0 END)             AS refunded_count,
    ROUND(SUM(CASE WHEN t.status = 'declined' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(t.transaction_id), 0) * 100, 2)               AS decline_rate_pct,
    ROUND(SUM(CASE WHEN t.status = 'refunded' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(t.transaction_id), 0) * 100, 2)               AS refund_rate_pct,
    ROUND(AVG(CASE WHEN t.status = 'approved' THEN t.amount END), 2)   AS avg_ticket_usd,
    ROUND(SUM(CASE WHEN t.status = 'approved' THEN t.amount ELSE 0 END), 2) AS total_volume_usd,
    cb_summary.unique_chargebacks,
    ROUND(cb_summary.unique_chargebacks
          / NULLIF(SUM(CASE WHEN t.status = 'approved' THEN 1 ELSE 0 END), 0) * 100, 3) AS chargeback_ratio_pct
FROM merchants m
LEFT JOIN transactions t ON t.merchant_id = m.merchant_id
LEFT JOIN (
    SELECT merchant_id, COUNT(DISTINCT transaction_id) AS unique_chargebacks
    FROM chargebacks
    WHERE is_final_stage = 1
    GROUP BY merchant_id
) cb_summary ON cb_summary.merchant_id = m.merchant_id
GROUP BY m.merchant_id, m.merchant_name, m.category, m.is_high_risk, cb_summary.unique_chargebacks
ORDER BY chargeback_ratio_pct DESC;


-- ============================================================
-- Transaction-Level Anomaly Checks
-- ============================================================

-- 2. Rapid repeat transactions: same customer at same merchant within 30 minutes
SELECT
    t1.transaction_id,
    t1.merchant_id,
    t1.customer_id,
    t1.amount,
    t1.txn_datetime,
    COUNT(*) OVER (
        PARTITION BY t1.merchant_id, t1.customer_id
        ORDER BY t1.txn_datetime
        RANGE BETWEEN INTERVAL 30 MINUTE PRECEDING AND CURRENT ROW
    ) - 1 AS txns_in_prior_30min,
    t1.is_fraud
FROM transactions t1
WHERE t1.status = 'approved'
HAVING txns_in_prior_30min >= 2
ORDER BY t1.merchant_id, t1.customer_id, t1.txn_datetime;


-- 3. High-value outliers: amount more than 3 standard deviations above merchant mean
SELECT
    t.transaction_id,
    t.merchant_id,
    m.merchant_name,
    t.customer_id,
    t.amount,
    stats.avg_amount,
    stats.std_amount,
    ROUND((t.amount - stats.avg_amount) / NULLIF(stats.std_amount, 0), 2) AS z_score,
    t.txn_datetime,
    t.is_fraud
FROM transactions t
JOIN merchants m ON m.merchant_id = t.merchant_id
JOIN (
    SELECT
        merchant_id,
        AVG(amount) AS avg_amount,
        STDDEV(amount) AS std_amount
    FROM transactions
    WHERE status = 'approved'
    GROUP BY merchant_id
) stats ON stats.merchant_id = t.merchant_id
WHERE t.status = 'approved'
  AND (t.amount - stats.avg_amount) / NULLIF(stats.std_amount, 0) > 3.0
ORDER BY z_score DESC;


-- 4. Unusual-hour transactions (2 AM to 5 AM)
SELECT
    t.transaction_id,
    t.merchant_id,
    m.merchant_name,
    t.customer_id,
    t.amount,
    t.txn_datetime,
    t.hour_of_day,
    t.location_mismatch,
    t.is_fraud
FROM transactions t
JOIN merchants m ON m.merchant_id = t.merchant_id
WHERE t.status = 'approved'
  AND t.hour_of_day BETWEEN 2 AND 5
ORDER BY t.txn_datetime DESC;


-- 5. Location mismatch transactions
SELECT
    t.transaction_id,
    t.merchant_id,
    m.merchant_name,
    t.customer_id,
    t.amount,
    t.ip_country,
    t.billing_country,
    t.txn_datetime,
    t.is_fraud
FROM transactions t
JOIN merchants m ON m.merchant_id = t.merchant_id
WHERE t.status = 'approved'
  AND t.location_mismatch = 1
ORDER BY t.amount DESC;


-- ============================================================
-- Merchants to Review: Composite Risk Ranking
-- ============================================================

-- 6. Risk ranking query combining all metrics
WITH merchant_stats AS (
    SELECT
        m.merchant_id,
        m.merchant_name,
        m.category,
        m.is_high_risk,
        COUNT(t.transaction_id)                                                AS total_txns,
        SUM(CASE WHEN t.status = 'approved' THEN 1 ELSE 0 END)                AS approved_txns,
        ROUND(SUM(CASE WHEN t.status = 'declined' THEN 1 ELSE 0 END)
              / NULLIF(COUNT(t.transaction_id), 0) * 100, 2)                   AS decline_rate_pct,
        ROUND(SUM(CASE WHEN t.status = 'refunded' THEN 1 ELSE 0 END)
              / NULLIF(COUNT(t.transaction_id), 0) * 100, 2)                   AS refund_rate_pct,
        ROUND(SUM(CASE WHEN t.location_mismatch = 1 AND t.status = 'approved' THEN 1 ELSE 0 END)
              / NULLIF(SUM(CASE WHEN t.status = 'approved' THEN 1 ELSE 0 END), 0) * 100, 2) AS location_mismatch_pct,
        ROUND(AVG(CASE WHEN t.status = 'approved' THEN t.amount END), 2)       AS avg_ticket_usd
    FROM merchants m
    LEFT JOIN transactions t ON t.merchant_id = m.merchant_id
    GROUP BY m.merchant_id, m.merchant_name, m.category, m.is_high_risk
),
cb_stats AS (
    SELECT
        merchant_id,
        COUNT(DISTINCT transaction_id)                                     AS unique_chargebacks,
        ROUND(SUM(loss_amount), 2)                                         AS total_loss_usd,
        ROUND(SUM(CASE WHEN outcome = 'won' AND is_final_stage = 1 THEN 1 ELSE 0 END)
              / NULLIF(SUM(is_final_stage), 0) * 100, 2)                   AS win_rate_pct
    FROM chargebacks
    GROUP BY merchant_id
)
SELECT
    ms.merchant_id,
    ms.merchant_name,
    ms.category,
    ms.is_high_risk,
    ms.total_txns,
    ms.decline_rate_pct,
    ms.refund_rate_pct,
    ms.location_mismatch_pct,
    ms.avg_ticket_usd,
    COALESCE(cs.unique_chargebacks, 0)  AS unique_chargebacks,
    COALESCE(cs.total_loss_usd, 0)      AS total_loss_usd,
    COALESCE(cs.win_rate_pct, 0)        AS win_rate_pct,
    ROUND(
        COALESCE(cs.unique_chargebacks, 0)
        / NULLIF(ms.approved_txns, 0) * 100, 3
    )                                   AS chargeback_ratio_pct,
    ROUND(
        (ms.decline_rate_pct * 0.25)
        + (ms.refund_rate_pct * 0.20)
        + (ms.location_mismatch_pct * 0.25)
        + (COALESCE(cs.unique_chargebacks, 0) / NULLIF(ms.approved_txns, 0) * 100 * 3.0)
        + (ms.is_high_risk * 10)
    , 2)                                AS composite_risk_score
FROM merchant_stats ms
LEFT JOIN cb_stats cs ON cs.merchant_id = ms.merchant_id
ORDER BY composite_risk_score DESC
LIMIT 20;


-- ============================================================
-- Chargeback Lifecycle Analytics
-- ============================================================

-- 7. Stage distribution and average days per stage
SELECT
    stage,
    COUNT(*)                                           AS records_at_stage,
    ROUND(AVG(DATEDIFF(deadline_date, stage_date)), 1) AS avg_days_in_stage,
    SUM(CASE WHEN outcome = 'won'       THEN 1 ELSE 0 END) AS won,
    SUM(CASE WHEN outcome = 'lost'      THEN 1 ELSE 0 END) AS lost,
    SUM(CASE WHEN outcome = 'escalated' THEN 1 ELSE 0 END) AS escalated,
    SUM(CASE WHEN outcome = 'pending'   THEN 1 ELSE 0 END) AS pending,
    ROUND(SUM(loss_amount), 2)                         AS total_loss_usd,
    ROUND(SUM(arbitration_fee), 2)                     AS total_arbitration_fees
FROM chargebacks
GROUP BY stage
ORDER BY FIELD(stage, 'retrieval_request','first_chargeback','representment','pre_arbitration','arbitration');


-- 8. Win rate and recovery rate by reason code
SELECT
    reason_code,
    reason_description,
    chargeback_type,
    COUNT(CASE WHEN is_final_stage = 1 THEN 1 END)                     AS total_cases,
    SUM(CASE WHEN is_final_stage = 1 AND outcome = 'won'  THEN 1 END)  AS won,
    SUM(CASE WHEN is_final_stage = 1 AND outcome = 'lost' THEN 1 END)  AS lost,
    ROUND(SUM(CASE WHEN is_final_stage = 1 AND outcome = 'won'  THEN 1 ELSE 0 END)
          / NULLIF(COUNT(CASE WHEN is_final_stage = 1 THEN 1 END), 0) * 100, 1) AS win_rate_pct,
    ROUND(SUM(CASE WHEN is_final_stage = 1 THEN loss_amount ELSE 0 END), 2) AS total_loss_usd
FROM chargebacks
GROUP BY reason_code, reason_description, chargeback_type
ORDER BY total_loss_usd DESC;


-- 9. Merchants with highest chargeback losses
SELECT
    c.merchant_id,
    m.merchant_name,
    m.category,
    m.is_high_risk,
    COUNT(CASE WHEN c.is_final_stage = 1 THEN 1 END)                    AS total_cases,
    ROUND(SUM(CASE WHEN c.is_final_stage = 1 THEN c.loss_amount ELSE 0 END), 2) AS total_loss_usd,
    ROUND(SUM(CASE WHEN c.is_final_stage = 1 THEN c.arbitration_fee ELSE 0 END), 2) AS total_arb_fees,
    ROUND(SUM(CASE WHEN c.is_final_stage = 1 AND c.outcome = 'won' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(CASE WHEN c.is_final_stage = 1 THEN 1 END), 0) * 100, 1) AS win_rate_pct
FROM chargebacks c
JOIN merchants m ON m.merchant_id = c.merchant_id
GROUP BY c.merchant_id, m.merchant_name, m.category, m.is_high_risk
HAVING total_loss_usd > 0
ORDER BY total_loss_usd DESC
LIMIT 15;


-- ============================================================
-- Data Quality Checks
-- ============================================================

-- 10. Orphan check: refunds with no matching transaction
SELECT COUNT(*) AS orphan_refunds
FROM refunds r
LEFT JOIN transactions t ON t.transaction_id = r.transaction_id
WHERE t.transaction_id IS NULL;

-- 11. Orphan check: chargebacks with no matching transaction
SELECT COUNT(*) AS orphan_chargebacks
FROM chargebacks c
LEFT JOIN transactions t ON t.transaction_id = c.transaction_id
WHERE t.transaction_id IS NULL;

-- 12. Null check on critical transaction fields
SELECT
    SUM(CASE WHEN transaction_id IS NULL THEN 1 ELSE 0 END)  AS null_transaction_id,
    SUM(CASE WHEN merchant_id IS NULL    THEN 1 ELSE 0 END)  AS null_merchant_id,
    SUM(CASE WHEN customer_id IS NULL    THEN 1 ELSE 0 END)  AS null_customer_id,
    SUM(CASE WHEN amount IS NULL         THEN 1 ELSE 0 END)  AS null_amount,
    SUM(CASE WHEN status IS NULL         THEN 1 ELSE 0 END)  AS null_status,
    SUM(CASE WHEN txn_datetime IS NULL   THEN 1 ELSE 0 END)  AS null_txn_datetime
FROM transactions;

-- 13. Negative amount check
SELECT COUNT(*) AS negative_amounts
FROM transactions
WHERE amount <= 0;
