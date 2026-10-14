SELECT DISTINCT * FROM {{ source('raw', 'raw_logins') }}
WHERE CAST(occurred_at AS DATE) <= (SELECT as_of FROM {{ ref('observation') }})
