-- =====================================================================
-- 02 Engagement funnel: exposure -> click -> like / share / follow
-- Business question: how much of the feed gets clicked, and how deep does engagement go?
-- How do the two Tencent products (QQ Kandian vs QQ Browser) compare?
-- =====================================================================

-- @name funnel_by_platform
SELECT 'QK' AS platform,
       COUNT(*)                                                  AS exposures,
       SUM(click)                                                AS clicks,
       SUM(alike)                                                AS likes,
       SUM(share)                                                AS shares,
       SUM(follow)                                               AS follows,
       SUM(CASE WHEN click = 1 AND watching_times >= 2 THEN 1 ELSE 0 END) AS rewatched_clicks,
       SUM(CASE WHEN click = 1 THEN watching_times ELSE 0 END)  AS watches
FROM qk
UNION ALL
SELECT 'QB', COUNT(*), SUM(click), SUM(alike), SUM(share), SUM(follow),
       SUM(CASE WHEN click = 1 AND watching_times >= 2 THEN 1 ELSE 0 END),
       SUM(CASE WHEN click = 1 THEN watching_times ELSE 0 END)
FROM qb;

-- @name funnel_by_category
-- video_category is a binary content flag in the source data (meaning not documented)
SELECT 'QK' AS platform, video_category,
       COUNT(*) AS exposures, SUM(click) AS clicks, SUM(alike) AS likes, SUM(share) AS shares, SUM(follow) AS follows
FROM qk GROUP BY video_category
UNION ALL
SELECT 'QB', video_category, COUNT(*), SUM(click), SUM(alike), SUM(share), SUM(follow)
FROM qb GROUP BY video_category
ORDER BY platform, video_category;
