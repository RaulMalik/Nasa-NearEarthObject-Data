-- Size histogram (50 m bins, capped) for the distribution chart.
CREATE OR REPLACE TABLE mart_size_distribution AS
SELECT
    CASE WHEN est_diameter_mean_m >= 1000 THEN 1000
         ELSE CAST(floor(est_diameter_mean_m / 50) * 50 AS INTEGER) END AS size_bin_m,
    count(*)                            AS approaches,
    sum(is_potentially_hazardous::INT)  AS hazardous_count
FROM fact_close_approach
GROUP BY ALL
ORDER BY size_bin_m;
