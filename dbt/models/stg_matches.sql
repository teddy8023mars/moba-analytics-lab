SELECT DISTINCT * FROM {{ source('raw', 'raw_matches') }}
WHERE CAST(started_at AS DATE) <= (SELECT as_of FROM {{ ref('observation') }})
