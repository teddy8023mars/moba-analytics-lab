SELECT DISTINCT CAST(occurred_at AS DATE) activity_date, user_id
FROM {{ ref('stg_logins') }}
