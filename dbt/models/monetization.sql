SELECT CAST(occurred_at AS DATE) payment_date,
 COUNT(*) transactions, COUNT(DISTINCT user_id) paying_users, SUM(amount_cents) revenue_cents,
 SUM(amount_cents)::DOUBLE / COUNT(DISTINCT user_id) arppu_cents
FROM {{ ref('stg_payments') }} GROUP BY payment_date
