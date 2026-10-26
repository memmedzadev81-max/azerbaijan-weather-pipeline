-- Example analytical queries on the gold layer.

-- 1. Average temperature and total rainfall per city and season
SELECT c.city_name,
       d.season,
       ROUND(AVG(f.avg_temperature_c), 1)   AS avg_temp_c,
       ROUND(SUM(f.total_precipitation_mm)) AS total_rain_mm
FROM fact_weather_daily f
JOIN dim_city c ON c.city_id = f.city_id
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY c.city_name, d.season
ORDER BY c.city_name, d.season;

-- 2. Hottest day per city (window function)
SELECT city_name, full_date, max_temperature_c
FROM (
    SELECT c.city_name, d.full_date, f.max_temperature_c,
           RANK() OVER (PARTITION BY f.city_id ORDER BY f.max_temperature_c DESC) AS rnk
    FROM fact_weather_daily f
    JOIN dim_city c ON c.city_id = f.city_id
    JOIN dim_date d ON d.date_key = f.date_key
)
WHERE rnk = 1;

-- 3. 7-day moving average temperature in Baku
SELECT d.full_date,
       f.avg_temperature_c,
       ROUND(AVG(f.avg_temperature_c) OVER (
           ORDER BY d.full_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS temp_7d_avg
FROM fact_weather_daily f
JOIN dim_date d ON d.date_key = f.date_key
WHERE f.city_id = 1
ORDER BY d.full_date;

-- 4. Pipeline run history
SELECT run_id, started_at, status, rows_bronze, rows_silver, rows_gold, message
FROM pipeline_runs
ORDER BY run_id DESC;
