-- =====================================================================
-- 03 Demographics (QK)
-- Business question: which audience groups click and engage most?
-- Rates are exposure-weighted: clicks / exposures, likes / clicks, etc.
-- =====================================================================

-- @name by_gender
SELECT gender,
       COUNT(*)                                          AS users,
       ROUND(AVG(exposures * 1.0), 1)                    AS exposures_per_user,
       SUM(exposures)                                    AS exposures,
       SUM(clicks)                                       AS clicks,
       SUM(likes)                                        AS likes,
       SUM(shares)                                       AS shares,
       SUM(follows)                                      AS follows
FROM user_qk
GROUP BY gender
ORDER BY gender;

-- @name by_age
SELECT age,
       COUNT(*)                                          AS users,
       ROUND(AVG(exposures * 1.0), 1)                    AS exposures_per_user,
       SUM(exposures)                                    AS exposures,
       SUM(clicks)                                       AS clicks,
       SUM(likes)                                        AS likes,
       SUM(shares)                                       AS shares,
       SUM(follows)                                      AS follows
FROM user_qk
GROUP BY age
ORDER BY age;

-- @name gender_age_grid
SELECT gender, age, COUNT(*) AS users, SUM(exposures) AS exposures, SUM(clicks) AS clicks, SUM(likes) AS likes
FROM user_qk
GROUP BY gender, age
ORDER BY gender, age;
