-- Hazard rate by size band (the headline "do bigger objects skew hazardous?" view).
CREATE OR REPLACE TABLE mart_hazard_summary AS
WITH banded AS (
    SELECT *,
        CASE WHEN est_diameter_mean_m < 50   THEN '1. <50 m'
             WHEN est_diameter_mean_m < 140  THEN '2. 50-140 m'
             WHEN est_diameter_mean_m < 300  THEN '3. 140-300 m'
             WHEN est_diameter_mean_m < 1000 THEN '4. 300-1000 m'
             ELSE '5. >1000 m' END AS size_band
    FROM fact_close_approach
)
SELECT
    size_band,
    count(*)                                        AS approaches,
    sum(is_potentially_hazardous::INT)              AS hazardous_count,
    round(avg(is_potentially_hazardous::INT) * 100, 2) AS hazardous_share_pct,
    round(avg(miss_distance_lunar), 2)              AS avg_miss_lunar,
    round(avg(relative_velocity_kmh), 0)            AS avg_velocity_kmh
FROM banded
GROUP BY ALL
ORDER BY size_band;
