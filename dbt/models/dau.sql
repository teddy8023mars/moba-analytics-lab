SELECT activity_date, COUNT(*) dau FROM {{ ref('user_day') }} GROUP BY activity_date
