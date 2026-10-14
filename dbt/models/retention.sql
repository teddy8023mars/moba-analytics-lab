WITH cohort AS (SELECT user_id, CAST(signup_at AS DATE) cohort_date FROM {{ ref('stg_users') }}),
eligible AS (SELECT c.*, d.day_offset FROM cohort c CROSS JOIN (VALUES (1), (7)) d(day_offset)
 WHERE c.cohort_date + d.day_offset <= (SELECT as_of FROM {{ ref('observation') }}))
SELECT e.cohort_date, e.day_offset, COUNT(*) cohort_users,
 COUNT(a.user_id) retained_users, COUNT(a.user_id)::DOUBLE / COUNT(*) retention_rate
FROM eligible e LEFT JOIN {{ ref('user_day') }} a ON e.user_id = a.user_id
 AND a.activity_date = e.cohort_date + e.day_offset
GROUP BY e.cohort_date, e.day_offset
