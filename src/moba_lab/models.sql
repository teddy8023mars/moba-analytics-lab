-- UTC timezone is explicitly set by the connection. Watermark is a complete day.
CREATE TABLE stg_users AS SELECT DISTINCT * FROM raw_users
WHERE CAST(signup_at AS DATE) <= (SELECT as_of FROM observation);
CREATE TABLE stg_logins AS SELECT DISTINCT * FROM raw_logins
WHERE CAST(occurred_at AS DATE) <= (SELECT as_of FROM observation);
CREATE TABLE stg_matches AS SELECT DISTINCT * FROM raw_matches
WHERE CAST(started_at AS DATE) <= (SELECT as_of FROM observation);
CREATE TABLE stg_participants AS SELECT DISTINCT p.* FROM raw_participants p
JOIN stg_matches m USING(match_id);
CREATE TABLE stg_payments AS SELECT DISTINCT * FROM raw_payments
WHERE CAST(occurred_at AS DATE) <= (SELECT as_of FROM observation);

-- Fact grain: one distinct login user per UTC day, regardless of event count.
CREATE TABLE user_day AS SELECT DISTINCT CAST(occurred_at AS DATE) activity_date, user_id
FROM stg_logins;
CREATE TABLE dau AS SELECT activity_date, COUNT(*) dau FROM user_day GROUP BY activity_date;

-- Exact-day retention, not rolling retention. Only observable offsets included.
CREATE TABLE retention AS
WITH cohort AS (SELECT user_id, CAST(signup_at AS DATE) cohort_date FROM stg_users),
eligible AS (SELECT c.*, d.day_offset FROM cohort c CROSS JOIN (VALUES (1), (7)) d(day_offset)
 WHERE c.cohort_date + d.day_offset <= (SELECT as_of FROM observation))
SELECT e.cohort_date, e.day_offset, COUNT(*) cohort_users,
 COUNT(a.user_id) retained_users, COUNT(a.user_id)::DOUBLE / COUNT(*) retention_rate
FROM eligible e LEFT JOIN user_day a ON e.user_id = a.user_id
 AND a.activity_date = e.cohort_date + e.day_offset
GROUP BY e.cohort_date, e.day_offset;

-- Participant fact grain: one player per match. No payment join here.
CREATE TABLE fact_player_match AS SELECT p.*, CAST(m.started_at AS DATE) match_date,
 m.duration_seconds FROM stg_participants p JOIN stg_matches m USING(match_id);
CREATE TABLE hero_stats AS SELECT hero, COUNT(*) player_matches,
 COUNT(DISTINCT match_id) distinct_matches, SUM(won::INT) wins,
 AVG(won::INT) win_rate, SUM(kills) kills, SUM(deaths) deaths, SUM(assists) assists
FROM fact_player_match GROUP BY hero;
CREATE TABLE player_stats AS SELECT user_id, COUNT(*) player_matches,
 SUM(won::INT) wins, SUM(kills) kills, SUM(deaths) deaths, SUM(assists) assists
FROM fact_player_match GROUP BY user_id;

-- Payment grain: transaction; cents remain integers until ARPPU division.
CREATE TABLE monetization AS SELECT CAST(occurred_at AS DATE) payment_date,
 COUNT(*) transactions, COUNT(DISTINCT user_id) paying_users, SUM(amount_cents) revenue_cents,
 SUM(amount_cents)::DOUBLE / COUNT(DISTINCT user_id) arppu_cents
FROM stg_payments GROUP BY payment_date;
