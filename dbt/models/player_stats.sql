SELECT user_id, COUNT(*) player_matches,
 SUM(won::INT) wins, SUM(kills) kills, SUM(deaths) deaths, SUM(assists) assists
FROM {{ ref('fact_player_match') }} GROUP BY user_id
