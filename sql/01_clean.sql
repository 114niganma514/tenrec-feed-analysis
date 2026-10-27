-- =====================================================================
-- 01 Data quality and modelling
-- Input tables (loaded by src/run_analysis.py):
--   qk = QK-video.csv (QQ Kandian video feed, ~490M exposures)
--   qb = QB-video.csv (QQ Browser video feed)
-- One row = one video exposure. click/like/share/follow are 0/1 flags; watching_times = times
-- watched after clicking; gender and age are anonymised codes (0 = missing).
-- =====================================================================

-- @name quality
SELECT 'QK' AS platform,
       COUNT(*)                                                         AS exposures,
       COUNT(DISTINCT user_id)                                          AS users,
       COUNT(DISTINCT item_id)                                          AS items,
       SUM(CASE WHEN click NOT IN (0, 1) THEN 1 ELSE 0 END)             AS bad_click_values,
       SUM(CASE WHEN click = 0 AND (alike = 1 OR share = 1 OR follow = 1) THEN 1 ELSE 0 END) AS action_without_click,
       SUM(CASE WHEN click = 0 AND watching_times > 0 THEN 1 ELSE 0 END) AS watch_without_click,
       SUM(CASE WHEN gender = 0 THEN 1 ELSE 0 END)                      AS gender_missing_rows,
       SUM(CASE WHEN age = 0 THEN 1 ELSE 0 END)                         AS age_missing_rows
FROM qk
UNION ALL
SELECT 'QB', COUNT(*), COUNT(DISTINCT user_id), COUNT(DISTINCT item_id),
       SUM(CASE WHEN click NOT IN (0, 1) THEN 1 ELSE 0 END),
       SUM(CASE WHEN click = 0 AND (alike = 1 OR share = 1 OR follow = 1) THEN 1 ELSE 0 END),
       SUM(CASE WHEN click = 0 AND watching_times > 0 THEN 1 ELSE 0 END),
       SUM(CASE WHEN gender = 0 THEN 1 ELSE 0 END),
       SUM(CASE WHEN age = 0 THEN 1 ELSE 0 END)
FROM qb;

-- @name null_counts
-- Missing values (\N in the source) per column, counted at load time before defaulting
SELECT * FROM qk_nulls
UNION ALL
SELECT * FROM qb_nulls;

-- @name build_user_qk
-- One row per QK user (all exposures)
DROP TABLE IF EXISTS user_qk;
CREATE TABLE user_qk AS
SELECT user_id,
       MAX(gender)                           AS gender,
       MAX(age)                              AS age,
       COUNT(*)                              AS exposures,
       SUM(click)                            AS clicks,
       SUM(alike)                            AS likes,
       SUM(share)                            AS shares,
       SUM(follow)                           AS follows,
       SUM(watching_times)                   AS watches,
       SUM(CASE WHEN click = 1 AND watching_times >= 2 THEN 1 ELSE 0 END) AS rewatched
FROM qk
GROUP BY user_id;

-- @name build_item_qk
DROP TABLE IF EXISTS item_qk;
CREATE TABLE item_qk AS
SELECT item_id,
       MAX(video_category)                   AS video_category,
       COUNT(*)                              AS exposures,
       SUM(click)                            AS clicks,
       SUM(alike)                            AS likes,
       SUM(share)                            AS shares
FROM qk
GROUP BY item_id;
