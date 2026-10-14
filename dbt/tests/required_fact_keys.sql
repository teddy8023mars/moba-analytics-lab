SELECT 'user_day' AS model FROM {{ ref('user_day') }} WHERE user_id IS NULL OR activity_date IS NULL
UNION ALL SELECT 'player_match' FROM {{ ref('fact_player_match') }} WHERE user_id IS NULL OR match_id IS NULL
UNION ALL SELECT 'retention' FROM {{ ref('retention') }} WHERE cohort_date IS NULL OR day_offset IS NULL OR cohort_users IS NULL OR retained_users IS NULL
