-- Incremental rebuild of the daily fact table.
-- Python first deletes the affected dates (stored in temp table _affected_dates),
-- then this statement re-aggregates exactly those dates from silver.
INSERT INTO fact_weather_daily
    (date_key, city_id, avg_temperature_c, min_temperature_c, max_temperature_c,
     total_precipitation_mm, avg_humidity_pct, max_wind_speed_kmh,
     rainy_hours, hours_recorded)
SELECT
    CAST(strftime('%Y%m%d', s.observed_date) AS INTEGER) AS date_key,
    s.city_id,
    ROUND(AVG(s.temperature_c), 2)                       AS avg_temperature_c,
    MIN(s.temperature_c)                                 AS min_temperature_c,
    MAX(s.temperature_c)                                 AS max_temperature_c,
    ROUND(SUM(s.precipitation_mm), 2)                    AS total_precipitation_mm,
    ROUND(AVG(s.relative_humidity_pct), 2)               AS avg_humidity_pct,
    MAX(s.wind_speed_kmh)                                AS max_wind_speed_kmh,
    SUM(CASE WHEN s.precipitation_mm > 0 THEN 1 ELSE 0 END) AS rainy_hours,
    COUNT(*)                                             AS hours_recorded
FROM silver_weather_hourly AS s
JOIN _affected_dates AS a ON a.observed_date = s.observed_date
GROUP BY s.observed_date, s.city_id;
