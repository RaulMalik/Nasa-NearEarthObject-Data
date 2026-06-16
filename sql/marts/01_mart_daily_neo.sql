-- Daily close-approach activity, size and hazard share (trend grain for BI).
CREATE OR REPLACE TABLE mart_daily_neo AS
SELECT
    d.date,
    d.date_key,
    count(*)                                        AS approaches,
    count(DISTINCT f.neo_id)                        AS distinct_neos,
    round(avg(f.est_diameter_mean_m), 1)            AS avg_diameter_m,
    round(median(f.est_diameter_mean_m), 1)         AS median_diameter_m,
    sum(f.is_potentially_hazardous::INT)            AS hazardous_count,
    round(avg(f.is_potentially_hazardous::INT) * 100, 2) AS hazardous_share_pct,
    round(min(f.miss_distance_km), 0)               AS closest_miss_km,
    round(max(f.relative_velocity_kmh), 0)          AS max_velocity_kmh
FROM fact_close_approach f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY ALL
ORDER BY d.date;
