-- =====================================================================
-- 04 Content and popularity bias (QK)
-- Business question: how concentrated are exposures, and do the most-shown videos actually
-- earn their exposure (higher click-through)?
-- =====================================================================

-- @name popularity_deciles
-- Items ranked by exposures into 10 equal-count groups (10 = most exposed)
WITH r AS (
    SELECT *, NTILE(10) OVER (ORDER BY exposures) AS decile FROM item_qk
)
SELECT decile,
       COUNT(*)                                              AS items,
       MIN(exposures)                                        AS min_exposures,
       MAX(exposures)                                        AS max_exposures,
       SUM(exposures)                                        AS exposures,
       SUM(clicks)                                           AS clicks,
       SUM(likes)                                            AS likes
FROM r
GROUP BY decile
ORDER BY decile;

-- @name concentration
WITH r AS (
    SELECT exposures, clicks,
           ROW_NUMBER() OVER (ORDER BY exposures DESC) AS rk,
           COUNT(*) OVER ()                            AS n
    FROM item_qk
)
SELECT MAX(n)                                                                         AS items,
       ROUND(SUM(CASE WHEN rk <= n * 0.01 THEN exposures ELSE 0 END) * 1.0 / SUM(exposures), 4) AS top1pct_exposure_share,
       ROUND(SUM(CASE WHEN rk <= n * 0.10 THEN exposures ELSE 0 END) * 1.0 / SUM(exposures), 4) AS top10pct_exposure_share,
       ROUND(SUM(CASE WHEN rk <= n * 0.01 THEN clicks ELSE 0 END) * 1.0 / SUM(clicks), 4)       AS top1pct_click_share,
       SUM(CASE WHEN exposures = 1 THEN 1 ELSE 0 END)                                         AS items_shown_once
FROM r;

-- @name item_ctr_by_size
-- Item-level CTR spread among items with enough exposures to be measured (100+)
SELECT CASE WHEN exposures < 1000 THEN '1_100-999'
            WHEN exposures < 10000 THEN '2_1k-10k'
            WHEN exposures < 100000 THEN '3_10k-100k'
            ELSE '4_100k+' END                                  AS exposure_band,
       COUNT(*)                                                 AS items,
       ROUND(AVG(clicks * 1.0 / exposures), 4)                  AS mean_item_ctr,
       SUM(clicks) * 1.0 / SUM(exposures)                       AS pooled_ctr
FROM item_qk
WHERE exposures >= 100
GROUP BY 1
ORDER BY 1;
