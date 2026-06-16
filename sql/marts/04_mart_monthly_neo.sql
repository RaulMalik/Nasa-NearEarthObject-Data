-- Monthly rollup of approaches, hazard share and mean size.
CREATE OR REPLACE TABLE mart_monthly_neo AS
SELECT
    d.year,
    d.month,
    d.month_name,
    count(*)                                        AS approaches,
    sum(f.is_potentially_hazardous::INT)            AS hazardous_count,
    round(avg(f.is_potentially_hazardous::INT) * 100, 2) AS hazardous_share_pct,
    round(avg(f.est_diameter_mean_m), 1)            AS avg_diameter_m
FROM fact_close_approach f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY ALL
ORDER BY d.year, d.month;
