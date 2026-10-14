SELECT DISTINCT * FROM {{ source('raw', 'raw_users') }}
WHERE CAST(signup_at AS DATE) <= (SELECT as_of FROM {{ ref('observation') }})
