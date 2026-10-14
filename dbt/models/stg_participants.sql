SELECT DISTINCT p.* FROM {{ source('raw', 'raw_participants') }} p
JOIN {{ ref('stg_matches') }} m USING(match_id)
