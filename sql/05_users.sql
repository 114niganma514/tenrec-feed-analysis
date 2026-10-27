-- =====================================================================
-- 05 User activity (QK)
-- Business question: how concentrated is engagement among users, and how many users never act?
-- =====================================================================

-- @name activity_buckets
SELECT CASE WHEN exposures < 10  THEN '1_1-9'
            WHEN exposures < 50  THEN '2_10-49'
            WHEN exposures < 100 THEN '3_50-99'
            WHEN exposures < 200 THEN '4_100-199'
            WHEN exposures < 500 THEN '5_200-499'
            ELSE '6_500+' END                                         AS exposure_bucket,
       COUNT(*)                                                       AS users,
       SUM(exposures)                                                 AS exposures,
       SUM(clicks)                                                    AS clicks,
       SUM(CASE WHEN clicks = 0 THEN 1 ELSE 0 END)                    AS never_clicked,
       SUM(CASE WHEN likes + shares + follows > 0 THEN 1 ELSE 0 END)  AS engaged_users
FROM user_qk
GROUP BY 1
ORDER BY 1;

-- @name user_percentiles
-- Users split into 100 equal groups by clicks (1 = most clicks), for the concentration curve
WITH r AS (
    SELECT clicks, likes, NTILE(100) OVER (ORDER BY clicks DESC) AS pctile FROM user_qk
)
SELECT pctile, COUNT(*) AS users, SUM(clicks) AS clicks, SUM(likes) AS likes
FROM r
GROUP BY pctile
ORDER BY pctile;

-- @name user_summary
SELECT COUNT(*)                                                           AS users,
       SUM(CASE WHEN clicks = 0 THEN 1 ELSE 0 END)                        AS never_clicked,
       SUM(CASE WHEN likes > 0 THEN 1 ELSE 0 END)                         AS ever_liked,
       SUM(CASE WHEN shares > 0 THEN 1 ELSE 0 END)                        AS ever_shared,
       SUM(CASE WHEN follows > 0 THEN 1 ELSE 0 END)                       AS ever_followed,
       ROUND(AVG(exposures * 1.0), 1)                                     AS mean_exposures,
       SUM(rewatched)                                                     AS rewatched_clicks
FROM user_qk;
