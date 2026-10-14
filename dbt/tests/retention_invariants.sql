SELECT * FROM {{ ref('retention') }}
WHERE cohort_users <= 0 OR retained_users < 0 OR retained_users > cohort_users
   OR day_offset NOT IN (1,7) OR retention_rate IS NULL
   OR ABS(retention_rate - retained_users::DOUBLE / cohort_users) > 1e-12
   OR cohort_date + day_offset > (SELECT as_of FROM {{ ref('observation') }})
