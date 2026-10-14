SELECT hero, COUNT(*) player_matches,
 COUNT(DISTINCT match_id) distinct_matches, SUM(won::INT) wins,
 AVG(won::INT) win_rate, SUM(kills) kills, SUM(deaths) deaths, SUM(assists) assists
FROM {{ ref('fact_player_match') }} GROUP BY hero
