SELECT p.*, CAST(m.started_at AS DATE) match_date,
 m.duration_seconds FROM {{ ref('stg_participants') }} p JOIN {{ ref('stg_matches') }} m USING(match_id)
