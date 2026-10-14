SELECT 'user_day' AS model FROM {{ ref('user_day') }} GROUP BY activity_date,user_id HAVING COUNT(*) > 1
UNION ALL SELECT 'retention' FROM {{ ref('retention') }} GROUP BY cohort_date,day_offset HAVING COUNT(*) > 1
UNION ALL SELECT 'player_match' FROM {{ ref('fact_player_match') }} GROUP BY match_id,user_id HAVING COUNT(*) > 1
