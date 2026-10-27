-- =====================================================================
-- 06 Feed fatigue: does click-through fall as a user scrolls further?
-- Assumption: rows are stored in each user's exposure order (the Tenrec authors build session
-- sequences from this order). Position = n-th exposure of that user in the file.
-- QB: all users. QK: fixed 2% user sample (user_id divisible by 50) to keep the sort affordable.
-- =====================================================================

-- @name build_seq
DROP TABLE IF EXISTS seq;
CREATE TABLE seq AS
SELECT 'QK' AS platform, user_id, click,
       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY rowid) AS pos
FROM qk
WHERE user_id % 50 = 0;
INSERT INTO seq
SELECT 'QB', user_id, click, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY rowid)
FROM qb;

-- @name fatigue
SELECT platform,
       CASE WHEN pos <= 10  THEN '01_1-10'
            WHEN pos <= 20  THEN '02_11-20'
            WHEN pos <= 50  THEN '03_21-50'
            WHEN pos <= 100 THEN '04_51-100'
            WHEN pos <= 200 THEN '05_101-200'
            WHEN pos <= 500 THEN '06_201-500'
            ELSE '07_501+' END                 AS position_bucket,
       COUNT(*)                                AS exposures,
       SUM(click)                              AS clicks,
       COUNT(DISTINCT user_id)                 AS users
FROM seq
GROUP BY 1, 2
ORDER BY 1, 2;

-- @name fatigue_within_user
-- Same users only: CTR in their first 20 exposures vs their exposures 101-200
-- (removes the effect of heavy users being different people from light users)
WITH u AS (
    SELECT platform, user_id,
           SUM(CASE WHEN pos <= 20 THEN click ELSE 0 END) * 1.0 / 20                    AS ctr_early,
           SUM(CASE WHEN pos BETWEEN 101 AND 200 THEN click ELSE 0 END) * 1.0 / 100     AS ctr_late
    FROM seq
    GROUP BY platform, user_id
    HAVING MAX(pos) >= 200
)
SELECT platform, user_id, ROUND(ctr_early, 4) AS ctr_early, ROUND(ctr_late, 4) AS ctr_late FROM u;
